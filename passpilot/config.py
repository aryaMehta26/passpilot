"""Paths, the pass catalog, and experiment budgets: the whole policy lives here."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LLVM = Path(os.environ.get("LLVM_PREFIX", "/opt/homebrew/opt/llvm")) / "bin"
CLANG, OPT, LLC = LLVM / "clang", LLVM / "opt", LLVM / "llc"
# Homebrew clang leaves macOS arm64 binaries unsigned (the kernel kills them); the system linker driver signs them.
LINKER = os.environ.get("PASSPILOT_LINKER", "/usr/bin/clang")
PLUGIN = ROOT / "build" / "IRFeatures.dylib"
BENCH_DIR = ROOT / "benchmarks"
BUILD_DIR = ROOT / "build"
DATA_DIR = ROOT / "data"

BENCHMARKS = sorted(p.stem for p in BENCH_DIR.glob("*.c"))

# Each pass the search may use, mapped to how it must be nested in an opt pipeline.
# Loop passes go through the loop adaptor; licm and unswitching need MemorySSA.
PASSES = {
    # module
    "globalopt": "globalopt", "ipsccp": "ipsccp", "deadargelim": "deadargelim",
    "globaldce": "globaldce", "constmerge": "constmerge",
    # call graph
    "inline": "cgscc(inline)", "function-attrs": "cgscc(function-attrs)", "argpromotion": "cgscc(argpromotion)",
    # function
    "mem2reg": "function(mem2reg)", "sroa": "function(sroa)", "early-cse": "function(early-cse<memssa>)",
    "instcombine": "function(instcombine)", "aggressive-instcombine": "function(aggressive-instcombine)",
    "instsimplify": "function(instsimplify)", "simplifycfg": "function(simplifycfg)",
    "reassociate": "function(reassociate)", "gvn": "function(gvn)", "newgvn": "function(newgvn)",
    "sccp": "function(sccp)", "dce": "function(dce)", "adce": "function(adce)", "bdce": "function(bdce)",
    "dse": "function(dse)", "memcpyopt": "function(memcpyopt)", "jump-threading": "function(jump-threading)",
    "correlated-propagation": "function(correlated-propagation)", "tailcallelim": "function(tailcallelim)",
    "mldst-motion": "function(mldst-motion)", "div-rem-pairs": "function(div-rem-pairs)",
    "float2int": "function(float2int)", "sink": "function(sink)", "loop-unroll": "function(loop-unroll)",
    "loop-vectorize": "function(loop-vectorize)", "slp-vectorizer": "function(slp-vectorizer)",
    "loop-distribute": "function(loop-distribute)", "loop-load-elim": "function(loop-load-elim)",
    "vector-combine": "function(vector-combine)",
    # loop
    "loop-rotate": "function(loop(loop-rotate))", "indvars": "function(loop(indvars))",
    "loop-idiom": "function(loop(loop-idiom))", "loop-deletion": "function(loop(loop-deletion))",
    "loop-instsimplify": "function(loop(loop-instsimplify))", "loop-simplifycfg": "function(loop(loop-simplifycfg))",
    "licm": "function(loop-mssa(licm))", "simple-loop-unswitch": "function(loop-mssa(simple-loop-unswitch))",
}
PASS_NAMES = sorted(PASSES)

BASELINES = {"O0": None, "O1": "default<O1>", "O2": "default<O2>", "O3": "default<O3>"}

MAX_PIPELINE_LEN = 40
SEARCH_RUNS = 3      # timed runs per candidate during search (min is kept)
CONFIRM_RUNS = 10    # timed runs when re-measuring the final best and the baselines
BUDGET = 40          # candidate pipelines each method may evaluate per benchmark
RUN_TIMEOUT_S = 30
