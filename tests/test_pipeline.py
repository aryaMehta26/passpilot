import pytest

from passpilot.config import MAX_PIPELINE_LEN, PASSES
from passpilot.pipeline import InvalidPipeline, to_opt, validate


def test_known_passes_build_a_pipeline():
    assert to_opt(["sroa", "licm", "inline"]) == "function(sroa),function(loop-mssa(licm)),cgscc(inline)"


def test_loop_passes_are_nested_in_loop_adaptors():
    assert PASSES["loop-rotate"] == "function(loop(loop-rotate))"
    assert PASSES["licm"].startswith("function(loop-mssa(")


@pytest.mark.parametrize("bad", [[], None, "sroa", ["sroa", "not-a-pass"], ["sroa"] * (MAX_PIPELINE_LEN + 1)])
def test_invalid_pipelines_are_rejected(bad):
    with pytest.raises(InvalidPipeline):
        validate(bad)


def test_error_names_the_unknown_pass():
    with pytest.raises(InvalidPipeline, match="loop-magic"):
        validate(["sroa", "loop-magic"])
