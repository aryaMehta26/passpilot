from passpilot.remarks import _LINE


def test_remark_lines_are_parsed():
    line = "remark: <unknown>:0:0: loop not vectorized: call instruction cannot be vectorized"
    assert _LINE.search(line).group(1) == "loop not vectorized: call instruction cannot be vectorized"


def test_other_stderr_is_ignored():
    assert _LINE.search("warning: something else") is None
