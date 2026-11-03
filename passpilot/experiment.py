"""The full experiment: baselines, then four search methods per benchmark at the same budget, then re-measure.

Phase 1  random search, genetic algorithm, LLM agent (each benchmark, same budget)
Phase 2  cost model trained leave-one-benchmark-out on phase-1 data, then model-guided search
Phase 3  re-measure every method's best pipeline and -O3 with more runs; write results + summary
Resumable: finished (benchmark, method) pairs in data/evaluations.csv are skipped.
"""
import json
import math
import time

import numpy as np
import pandas as pd

from . import costmodel
from .agent import agent_search
from .config import BASELINES, BENCHMARKS, BUDGET, CONFIRM_RUNS, DATA_DIR, PASSES
from .evaluator import Evaluator
from .pipeline import to_opt
from .search import genetic_search, random_search
from .toolchain import measure

EVALS = DATA_DIR / "evaluations.csv"
BASES = DATA_DIR / "baselines.csv"


def _load(path):
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _append(path, rows):
    if rows:
        pd.DataFrame(rows).to_csv(path, mode="a", header=not path.exists(), index=False)


def baselines(benches):
    have = _load(BASES)
    rows = []
    for b in benches:
        if not have.empty and b in set(have.bench):
            continue
        for name, pipe in BASELINES.items():
            m = measure(b, pipe, 3 if name == "O0" else CONFIRM_RUNS, tag=f"base_{name}")
            rows.append({"bench": b, "baseline": name, **m.as_dict()})
            print(f"  {b:10s} {name}: {m.runtime_s:.3f}s correct={m.correct}", flush=True)
    _append(BASES, rows)
    return _load(BASES)


def _base(bases, bench, name):
    return float(bases[(bases.bench == bench) & (bases.baseline == name)].runtime_s.iloc[0])


def _done(bench, method):
    df = _load(EVALS)
    return not df.empty and ((df.bench == bench) & (df.method == method)).any()


def phase1(benches, methods, budget, bases):
    stats_path = DATA_DIR / "agent_stats.json"
    agent_stats = json.loads(stats_path.read_text()) if stats_path.exists() else {}
    for b in benches:
        o3, o0 = _base(bases, b, "O3"), _base(bases, b, "O0")
        for method in methods:
            if method == "model" or _done(b, method):
                continue
            t0, log = time.time(), []
            ev = Evaluator(b, method, budget, o3, log)
            if method == "random":
                random_search(ev)
            elif method == "ga":
                genetic_search(ev)
            elif method == "agent":
                trace = []
                _, stats = agent_search(ev, o0, trace=trace)
                agent_stats[b] = stats
                stats_path.write_text(json.dumps(agent_stats, indent=2))
                with open(DATA_DIR / "agent_trace.jsonl", "a") as f:
                    f.writelines(json.dumps(t) + "\n" for t in trace)
            _append(EVALS, log)
            best = ev.best[0]
            print(f"  {b:10s} {method:6s} best {best:.3f}s = {o3 / best if best < math.inf else 0:.2f}x vs O3 "
                  f"({time.time() - t0:.0f}s)", flush=True)


def phase2(benches, budget, bases):
    df = _load(EVALS)
    train_df = df[df.method != "model"]
    held = []
    for b in benches:
        model = costmodel.train(train_df, exclude=b)
        held.append(costmodel.held_out_scores(train_df, b, model))
        if _done(b, "model"):
            continue
        log = []
        o3 = _base(bases, b, "O3")
        ev = Evaluator(b, "model", budget, o3, log)
        costmodel.model_guided_search(ev, model, train_df)
        _append(EVALS, log)
        print(f"  {b:10s} model  best {ev.best[0]:.3f}s = {o3 / ev.best[0]:.2f}x vs O3", flush=True)
    pd.DataFrame(held).to_csv(DATA_DIR / "costmodel_heldout.csv", index=False)


def phase3(benches, bases):
    df = _load(EVALS)
    rows = []
    for b in benches:
        o3 = measure(b, BASELINES["O3"], CONFIRM_RUNS, tag="confirm_O3")
        for method, g in df[(df.bench == b) & df.correct.astype(bool)].groupby("method"):
            best = g.loc[g.runtime_s.idxmin()]
            m = measure(b, to_opt(best.passes.split()), CONFIRM_RUNS, tag=f"confirm_{method}")
            rows.append({"bench": b, "method": method, "passes": best.passes, "found_at_step": int(best.step),
                         "runtime_s": m.runtime_s, "correct": m.correct, "o3_runtime_s": o3.runtime_s,
                         "speedup_vs_o3": o3.runtime_s / m.runtime_s, "compile_s": m.compile_s,
                         "o3_compile_s": o3.compile_s, "text_bytes": m.text_bytes, "o3_text_bytes": o3.text_bytes,
                         "speedup_vs_o0": _base(bases, b, "O0") / m.runtime_s})
            print(f"  {b:10s} {method:6s} confirmed {o3.runtime_s / m.runtime_s:.3f}x vs O3", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(DATA_DIR / "results.csv", index=False)
    return res


def summarize(res, budget, wall_s):
    df = _load(EVALS)
    held = _load(DATA_DIR / "costmodel_heldout.csv")
    stats_path = DATA_DIR / "agent_stats.json"
    stats = json.loads(stats_path.read_text()) if stats_path.exists() else {}
    agg = {k: round(sum(s.get(k, 0) for s in stats.values()), 1) for k in
           ["llm_calls", "invalid_json", "unknown_pass_repairs", "duplicates", "fallbacks", "llm_errors",
            "build_failures", "wrong_outputs", "llm_seconds"]}
    per_method = {}
    for method, g in res.groupby("method"):
        sp = g.speedup_vs_o3.to_numpy()
        per_method[method] = {
            "geomean_speedup_vs_o3": float(np.exp(np.log(sp).mean())),
            "best_speedup_vs_o3": float(sp.max()), "best_bench": g.loc[g.speedup_vs_o3.idxmax(), "bench"],
            "wins_over_2pct": int((sp > 1.02).sum()), "within_2pct": int(((sp >= 0.98) & (sp <= 1.02)).sum()),
            "losses_over_2pct": int((sp < 0.98).sum()),
            "mean_compile_ratio_vs_o3": float((g.compile_s / g.o3_compile_s).mean())}
    summary = {
        "benchmarks": int(res.bench.nunique()), "budget_per_method": budget, "passes_in_catalog": len(PASSES),
        "total_evaluations": int(len(df)), "invalid_candidates": int((~df.correct.astype(bool)).sum()),
        "per_method": per_method,
        "agent_interface": agg,
        "costmodel": {"mean_spearman": float(held.spearman.mean()) if not held.empty else None,
                      "top1_within_5pct": int(held.top1_within_5pct.sum()) if not held.empty else None,
                      "benchmarks": int(len(held))},
        # Summed from the logs, so it stays right when a run is resumed.
        "measurement_minutes": round(df.eval_s.sum() / 60, 1),
        "llm_minutes": round(agg["llm_seconds"] / 60, 1),
    }
    (DATA_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def run(benches=None, methods=("random", "ga", "agent", "model"), budget=BUDGET):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    benches = benches or BENCHMARKS
    t0 = time.time()
    print("baselines", flush=True)
    bases = baselines(benches)
    print("phase 1: search", flush=True)
    phase1(benches, methods, budget, bases)
    if "model" in methods:
        print("phase 2: cost model", flush=True)
        phase2(benches, budget, bases)
    print("phase 3: confirm", flush=True)
    res = phase3(benches, bases)
    return summarize(res, budget, time.time() - t0)
