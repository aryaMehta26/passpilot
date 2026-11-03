"""IR features from the C++ IRFeatures plugin, plus a fixed-width encoding of a pass pipeline."""
import json
import subprocess

import numpy as np

from .config import OPT, PASS_NAMES, PLUGIN
from .toolchain import base_bitcode

IR_KEYS = ["functions", "loops", "innermost_loops", "max_loop_depth", "blocks", "insts", "insts_in_loops",
           "loads", "stores", "allocas", "phis", "geps", "terminators", "compares", "calls", "intrinsics",
           "binops", "fp_insts", "vector_insts"]

_cache = {}


def ir_features(bench):
    if bench not in _cache:
        if not PLUGIN.exists():
            raise FileNotFoundError(f"{PLUGIN} missing: run `make plugin` first")
        r = subprocess.run([str(OPT), f"-load-pass-plugin={PLUGIN}", "-passes=ir-features", "-disable-output",
                            str(base_bitcode(bench))], capture_output=True, text=True, check=True)
        raw = json.loads(r.stdout.strip().splitlines()[-1])
        _cache[bench] = {k: raw.get(k, 0) for k in IR_KEYS}
    return _cache[bench]


def encode_pipeline(passes):
    """Per pass: how often it appears and where it first appears (as a fraction of the pipeline), plus length."""
    n = len(passes)
    counts = np.zeros(len(PASS_NAMES))
    first = np.ones(len(PASS_NAMES))
    for i, p in enumerate(passes):
        j = PASS_NAMES.index(p)
        counts[j] += 1
        first[j] = min(first[j], i / n)
    return np.concatenate([counts, first, [n]])


def feature_names():
    return [f"count:{p}" for p in PASS_NAMES] + [f"first:{p}" for p in PASS_NAMES] + ["length"] + \
           [f"ir:{k}" for k in IR_KEYS]


def encode(bench, passes):
    ir = ir_features(bench)
    return np.concatenate([encode_pipeline(passes), [ir[k] for k in IR_KEYS]])
