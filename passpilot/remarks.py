"""Compiler feedback for the agent: LLVM's own 'missed optimization' remarks for a pipeline."""
import re
import subprocess
from collections import Counter

from .config import OPT
from .pipeline import to_opt
from .toolchain import base_bitcode

REMARK_PASSES = "loop-vectorize|slp-vectorizer|licm|loop-unroll|gvn|inline"
_LINE = re.compile(r"remark: [^ ]*: (.*)$")


def missed_remarks(bench, passes, limit=5):
    """Most frequent distinct missed-optimization messages, e.g. why a loop was not vectorized."""
    r = subprocess.run([str(OPT), f"-passes={to_opt(passes)}", "-disable-output",
                        f"-pass-remarks-missed={REMARK_PASSES}", f"-pass-remarks-analysis={REMARK_PASSES}",
                        str(base_bitcode(bench))], capture_output=True, text=True, timeout=60)
    msgs = Counter(m.group(1).strip() for line in r.stderr.splitlines() if (m := _LINE.search(line)))
    return [f"{msg} (x{n})" for msg, n in msgs.most_common(limit)]
