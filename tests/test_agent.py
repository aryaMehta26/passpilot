import json
from collections import Counter

import pytest

from passpilot.agent import _parse
from passpilot.pipeline import InvalidPipeline


def test_valid_reply_is_parsed():
    passes, reason = _parse(json.dumps({"passes": ["sroa", "licm"], "reason": "hoist loads"}), Counter())
    assert passes == ["sroa", "licm"] and reason == "hoist loads"


def test_unknown_passes_are_repaired_and_counted():
    stats = Counter()
    passes, _ = _parse(json.dumps({"passes": ["sroa", "loop-magic", "gvn"]}), stats)
    assert passes == ["sroa", "gvn"] and stats["unknown_pass_repairs"] == 1


@pytest.mark.parametrize("reply", ["not json", "[]", json.dumps({"pipeline": ["sroa"]}),
                                   json.dumps({"passes": ["nope", "nada"]})])
def test_unusable_replies_are_rejected(reply):
    with pytest.raises(InvalidPipeline):
        _parse(reply, Counter())


def test_whitespace_in_pass_names_is_tolerated():
    passes, _ = _parse(json.dumps({"passes": [" sroa ", "instcombine\n"]}), Counter())
    assert passes == ["sroa", "instcombine"]
