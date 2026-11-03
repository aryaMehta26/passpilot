import numpy as np

from passpilot.config import PASS_NAMES
from passpilot.features import encode_pipeline, feature_names, IR_KEYS


def test_encoding_counts_and_first_position():
    v = encode_pipeline(["sroa", "gvn", "sroa", "licm"])
    n = len(PASS_NAMES)
    counts, first, length = v[:n], v[n:2 * n], v[-1]
    assert counts[PASS_NAMES.index("sroa")] == 2
    assert first[PASS_NAMES.index("sroa")] == 0
    assert first[PASS_NAMES.index("licm")] == 0.75
    assert first[PASS_NAMES.index("dce")] == 1.0     # absent passes sit at the end
    assert length == 4


def test_feature_names_match_vector_width():
    assert len(feature_names()) == len(encode_pipeline(["dce"])) + len(IR_KEYS)


def test_order_changes_the_encoding():
    assert not np.array_equal(encode_pipeline(["sroa", "gvn"]), encode_pipeline(["gvn", "sroa"]))
