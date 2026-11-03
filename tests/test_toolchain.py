"""Integration: really compiles and runs one small benchmark. Skipped when LLVM isn't installed."""
import pytest

from passpilot.config import OPT, PLUGIN

pytestmark = pytest.mark.skipif(not OPT.exists(), reason="LLVM not installed")


def test_o1_build_is_correct_and_faster_than_o0():
    from passpilot.toolchain import measure
    o0 = measure("histogram", None, 1, tag="t_o0")
    o1 = measure("histogram", "default<O1>", 1, tag="t_o1")
    assert o0.ok and o0.correct and o1.ok and o1.correct
    assert o1.runtime_s < o0.runtime_s


def test_unknown_pass_fails_cleanly():
    from passpilot.toolchain import measure
    m = measure("histogram", "function(no-such-pass)", 1, tag="t_bad")
    assert not m.ok and "opt" in m.error


@pytest.mark.skipif(not PLUGIN.exists(), reason="run `make plugin` first")
def test_plugin_reports_loops():
    from passpilot.features import ir_features
    f = ir_features("matmul")
    assert f["loops"] >= 3 and f["max_loop_depth"] == 3
