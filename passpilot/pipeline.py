"""Turn a list of pass names into an opt pipeline string, rejecting anything unknown."""
from .config import MAX_PIPELINE_LEN, PASSES


class InvalidPipeline(ValueError):
    pass


def validate(passes):
    if not isinstance(passes, (list, tuple)) or not passes:
        raise InvalidPipeline("pipeline must be a non-empty list of pass names")
    if len(passes) > MAX_PIPELINE_LEN:
        raise InvalidPipeline(f"pipeline has {len(passes)} passes; the limit is {MAX_PIPELINE_LEN}")
    unknown = [p for p in passes if p not in PASSES]
    if unknown:
        raise InvalidPipeline(f"unknown passes: {', '.join(map(str, unknown))}")
    return list(passes)


def to_opt(passes):
    return ",".join(PASSES[p] for p in validate(passes))
