from dataclasses import FrozenInstanceError

import pytest
from game.InputBuffer import InputBuffer


@pytest.mark.parametrize("has_trailing_newline", [False, True])
def test_file_input_is_an_immutable_snapshot(shell_basic, has_trailing_newline):
    source = shell_basic.fs.resolve("f1.txt")
    source.inode.has_trailing_newline = has_trailing_newline
    original = tuple(source.inode.data)
    buffer = InputBuffer.from_file(source)

    assert buffer.lines == original
    assert buffer.has_trailing_newline is has_trailing_newline
    with pytest.raises(FrozenInstanceError):
        buffer.lines = ("changed",)
    with pytest.raises(FrozenInstanceError):
        buffer.has_trailing_newline = not has_trailing_newline
    with pytest.raises(TypeError):
        buffer.lines[0] = "changed"
    assert tuple(source.inode.data) == original

    source.inode.data[0] = "changed after reading"
    source.inode.has_trailing_newline = not has_trailing_newline
    assert buffer.lines == original
    assert buffer.has_trailing_newline is has_trailing_newline


@pytest.mark.parametrize("lines", [[], [""], ["a", "", "b"]])
def test_line_input_preserves_content_and_detaches_upstream_output(lines):
    original = tuple(lines)
    buffer = InputBuffer.from_lines(lines)
    assert buffer.lines == original
    assert buffer.has_trailing_newline is bool(original)

    lines.append("changed after reading")
    assert buffer.lines == original


def test_constructor_snapshots_mutable_lines():
    lines = ["original"]
    buffer = InputBuffer(lines, has_trailing_newline=False)
    lines.clear()
    assert buffer.lines == ("original",)
    assert not buffer.has_trailing_newline
