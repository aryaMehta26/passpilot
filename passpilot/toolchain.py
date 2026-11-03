"""Compile a benchmark with a given pass pipeline, then measure compile time, size, runtime and correctness.

Every candidate goes through the same path, so only the IR pipeline differs:
    clang -O0 (no optnone) -> .bc -> opt -passes=<pipeline> -> llc -O2 -> link -> run
"""
import hashlib
import subprocess
import time
from dataclasses import asdict, dataclass

from .config import BENCH_DIR, BUILD_DIR, CLANG, LINKER, LLC, OPT, RUN_TIMEOUT_S
from .pipeline import to_opt


@dataclass
class Measurement:
    ok: bool
    correct: bool = False
    runtime_s: float = float("nan")
    compile_s: float = float("nan")
    text_bytes: int = 0
    error: str = ""

    def as_dict(self):
        return asdict(self)


def _run(cmd, timeout=120):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout)


def base_bitcode(bench):
    """Unoptimized bitcode for a benchmark, built once and cached."""
    BUILD_DIR.mkdir(exist_ok=True)
    bc = BUILD_DIR / f"{bench}.base.bc"
    src = BENCH_DIR / f"{bench}.c"
    if not bc.exists() or bc.stat().st_mtime < src.stat().st_mtime:
        r = _run([CLANG, "-O0", "-Xclang", "-disable-O0-optnone", "-emit-llvm", "-c", src, "-o", bc])
        if r.returncode:
            raise RuntimeError(f"clang failed on {bench}: {r.stderr[:500]}")
    return bc


def _text_size(obj):
    r = _run(["size", obj])
    try:
        return int(r.stdout.splitlines()[1].split()[0])
    except (IndexError, ValueError):
        return obj.stat().st_size


def _time_runs(exe, runs):
    best, out = float("inf"), None
    for _ in range(runs):
        t0 = time.perf_counter()
        r = _run([exe], timeout=RUN_TIMEOUT_S)
        dt = time.perf_counter() - t0
        if r.returncode:
            raise RuntimeError(f"exit code {r.returncode}")
        out = r.stdout.strip()
        best = min(best, dt)
    return best, out


def build(bench, opt_pipeline, tag):
    """Build an executable; returns (exe, object, compile seconds). opt_pipeline=None means no IR passes."""
    bc = base_bitcode(bench)
    work = BUILD_DIR / "cand" / bench
    work.mkdir(parents=True, exist_ok=True)
    opt_bc, obj, exe = work / f"{tag}.bc", work / f"{tag}.o", work / tag
    t0 = time.perf_counter()
    if opt_pipeline:
        r = _run([OPT, f"-passes={opt_pipeline}", bc, "-o", opt_bc])
        if r.returncode:
            raise RuntimeError("opt: " + r.stderr.strip()[:300])
    else:
        opt_bc = bc
    r = _run([LLC, "-O2", "-filetype=obj", opt_bc, "-o", obj])
    if r.returncode:
        raise RuntimeError("llc: " + r.stderr.strip()[:300])
    compile_s = time.perf_counter() - t0
    # Apple Silicon kills a binary overwritten in place (stale code signature), so always link a fresh file.
    exe.unlink(missing_ok=True)
    r = _run([LINKER, obj, "-o", exe, "-lm"])
    if r.returncode:
        raise RuntimeError("link: " + r.stderr.strip()[:300])
    return exe, obj, compile_s


_reference = {}


def reference_output(bench):
    """Program output at -O0: the ground truth every optimized build must reproduce."""
    if bench not in _reference:
        exe, _, _ = build(bench, None, "ref")
        _reference[bench] = _time_runs(exe, 1)[1]
    return _reference[bench]


def measure(bench, opt_pipeline, runs, tag=None):
    tag = tag or hashlib.sha1((opt_pipeline or "O0").encode()).hexdigest()[:12]
    try:
        exe, obj, compile_s = build(bench, opt_pipeline, tag)
        runtime_s, out = _time_runs(exe, runs)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        return Measurement(ok=False, error=str(e)[:300])
    correct = out == reference_output(bench)
    return Measurement(ok=True, correct=correct, runtime_s=runtime_s, compile_s=compile_s,
                       text_bytes=_text_size(obj), error="" if correct else "output differs from -O0")


def measure_passes(bench, passes, runs):
    return measure(bench, to_opt(passes), runs)
