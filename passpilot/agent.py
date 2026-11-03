"""An LLM agent that tunes a pass pipeline from compiler and performance feedback.

Each step the agent sees the program, its IR features, what it has tried so far (runtime, speedup vs -O3,
failures) and LLVM's missed-optimization remarks for the latest pipeline, then proposes one new pipeline.
The interface is strict: proposals must be JSON naming known passes. Bad output is repaired or retried,
and if the model keeps failing, the step falls back to mutating the best pipeline so budget isn't wasted.
"""
import json
import math
import random
import time
from collections import Counter

import requests

from .config import BENCH_DIR, PASS_NAMES
from .evaluator import BudgetExhausted
from .features import ir_features
from .pipeline import InvalidPipeline, validate
from .remarks import missed_remarks
from .search import mutate

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1"
MAX_RETRIES = 2

SYSTEM = f"""You are a compiler optimization agent tuning LLVM IR pass pipelines for runtime speed.
The program starts as unoptimized IR (allocas, no SSA). Machine code generation is fixed (llc -O2);
only the IR pass pipeline you choose changes. Correctness is checked: if output changes, the pipeline scores zero.

Available passes (use these exact names, in the order they should run, 3 to 40 passes, repeats allowed):
{", ".join(PASS_NAMES)}

Reply with JSON only: {{"passes": ["pass", ...], "reason": "one sentence on why this should be faster"}}"""


def _source(bench, limit=1800):
    src = (BENCH_DIR / f"{bench}.c").read_text()
    return src if len(src) <= limit else src[:limit] + "\n/* ... truncated ... */"


def _history_table(ev, k_best=6, k_recent=3):
    rows = [(ev.cache[p], list(p)) for p in ev.cache]
    good = sorted([r for r in rows if r[0].correct], key=lambda r: r[0].runtime_s)[:k_best]
    recent = rows[-k_recent:]
    lines = []
    for m, p in good + [r for r in recent if r not in good]:
        status = (f"{m.runtime_s:.3f}s ({ev.o3 / m.runtime_s:.2f}x vs -O3)" if m.correct
                  else ("WRONG OUTPUT" if m.ok else f"FAILED: {m.error[:80]}"))
        lines.append(f"- {status}: {' '.join(p)}")
    return "\n".join(lines) or "(nothing tried yet)"


def _prompt(ev, o0_runtime, remarks):
    best = "none yet" if ev.best[1] is None else f"{ev.best[0]:.3f}s"
    return f"""Benchmark: {ev.bench}
```c
{_source(ev.bench)}
```
IR features (unoptimized): {json.dumps(ir_features(ev.bench))}
Runtime at -O0: {o0_runtime:.3f}s. Runtime at -O3 (target to beat): {ev.o3:.3f}s. Your best so far: {best}.
Evaluations left: {ev.remaining}.

Pipelines tried (best first, then most recent):
{_history_table(ev)}

LLVM missed-optimization remarks for the latest pipeline:
{chr(10).join("- " + r for r in remarks) or "- (none)"}

Propose ONE new pipeline you have not tried that should run faster. Use the remarks: if loops were not
vectorized, think about which canonicalization (mem2reg/sroa, loop-rotate, licm, indvars, instcombine) must come first."""


def _ask(messages):
    r = requests.post(OLLAMA_URL, json={"model": MODEL, "messages": messages, "stream": False, "format": "json",
                                        "options": {"temperature": 0.7, "num_ctx": 8192, "num_predict": 200}}, timeout=180)
    r.raise_for_status()
    return r.json()["message"]["content"]


def _parse(text, stats):
    """JSON -> a valid pass list. Unknown pass names are dropped (repaired) if anything valid remains."""
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        stats["invalid_json"] += 1
        raise InvalidPipeline("reply was not valid JSON")
    passes = obj.get("passes") if isinstance(obj, dict) else None
    if not isinstance(passes, list):
        stats["invalid_json"] += 1
        raise InvalidPipeline('reply must have a "passes" list')
    passes = [str(p).strip() for p in passes]
    known = [p for p in passes if p in PASS_NAMES]
    if len(known) < len(passes):
        stats["unknown_pass_repairs"] += 1
        if not known:
            raise InvalidPipeline("none of the proposed passes exist: " + ", ".join(passes[:5]))
    return validate(known[:40]), str(obj.get("reason", ""))[:200]


def agent_search(ev, o0_runtime, seed=0, trace=None):
    rng = random.Random(seed)
    stats = Counter()
    remarks = []
    try:
        while ev.remaining > 0:
            messages = [{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": _prompt(ev, o0_runtime, remarks)}]
            passes, reason = None, ""
            for attempt in range(MAX_RETRIES + 1):
                t0 = time.perf_counter()
                stats["llm_calls"] += 1
                try:
                    reply = _ask(messages)
                except requests.RequestException as e:
                    stats["llm_errors"] += 1
                    reply = ""
                    err = f"model call failed: {e}"
                else:
                    try:
                        passes, reason = _parse(reply, stats)
                        if tuple(passes) in ev.cache:
                            stats["duplicates"] += 1
                            raise InvalidPipeline("that exact pipeline was already evaluated; propose a different one")
                    except InvalidPipeline as e:
                        passes, err = None, str(e)
                stats["llm_seconds"] += time.perf_counter() - t0
                if passes:
                    break
                messages += [{"role": "assistant", "content": reply or "{}"},
                             {"role": "user", "content": f"Error: {err}. Reply again with valid JSON."}]
            if not passes:
                stats["fallbacks"] += 1
                base = ev.best[1] or [rng.choice(PASS_NAMES) for _ in range(10)]
                passes, reason = mutate(base, rng), "fallback: mutation of best"
                while tuple(passes) in ev.cache:
                    passes = mutate(passes, rng)
            s = ev.score(passes)
            m = ev.result(passes)
            if not m.ok:
                stats["build_failures"] += 1
            elif not m.correct:
                stats["wrong_outputs"] += 1
            if trace is not None:
                trace.append({"bench": ev.bench, "step": ev.used, "passes": " ".join(passes), "reason": reason,
                              "runtime_s": None if math.isinf(s) else round(s, 4)})
            try:
                remarks = missed_remarks(ev.bench, passes)
            except Exception:
                remarks = []
    except BudgetExhausted:
        pass
    return ev.best, dict(stats)
