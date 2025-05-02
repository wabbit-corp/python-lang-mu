import pytest
from mu.input import Pos, Span

# ------------------------------
# Test the Pos class
# ------------------------------

def test_pos_forward_normal_char():
    p = Pos(line=1, col=1, index=0)
    p2 = p.forward_via('a')
    assert p2.line == 1
    assert p2.col == 2
    assert p2.index == 1

def test_pos_forward_newline():
    p = Pos(line=1, col=10, index=9)
    p2 = p.forward_via('\n')
    assert p2.line == 2
    assert p2.col == 1
    assert p2.index == 10

def test_pos_backward_normal_char():
    p = Pos(line=2, col=5, index=10)
    p2 = p.backward_via('a')
    assert p2.line == 2
    assert p2.col == 4
    assert p2.index == 9

def test_pos_backward_newline_raises():
    p = Pos(line=2, col=5, index=10)
    with pytest.raises(ValueError, match="Cannot move backwards over a newline"):
        p.backward_via('\n')

# ------------------------------
# Test the Span class
# ------------------------------

def test_span_init_happy_path():
    # The raw is 5 chars long, so end.index - start.index must be 5
    start = Pos(line=1, col=1, index=0)
    # We'll set end's index to start.index + 5 = 5
    end = Pos(line=1, col=6, index=5)
    s = Span(start, end, raw="hello")
    assert s.start == start
    assert s.end == end
    assert s.raw == "hello"

def test_span_init_mismatch_length():
    start = Pos(line=1, col=1, index=0)
    # The 'raw' is length 5, but end.index - start.index = 6 => mismatch
    end = Pos(line=1, col=7, index=6)
    with pytest.raises(AssertionError):
        Span(start, end, raw="hello")

def test_span_slice_simple():
    # Suppose the raw is "hello" => length 5
    # We'll pretend the text is all on one line for simplicity.
    start = Pos(line=1, col=1, index=0)   # start index = 0
    end   = Pos(line=1, col=6, index=5)   # end   index = 5
    s = Span(start, end, "hello")

    # s[1:4] => "ell"
    # We should see that the new Span covers 3 characters and the positions shift.
    sliced = s[1:4]

    assert sliced.raw == "ell"
    assert sliced.start.index == 1
    assert sliced.end.index == 4
    # The line should still be 1, columns should reflect the shift
    assert sliced.start.line == 1
    assert sliced.start.col == 2  # original was col=1 => moved forward by 1 char => col=2
    assert sliced.end.col == 5    # original was col=6 => moved backward by 1 char => col=5

def test_span_slice_with_negative_stop():
    # raw = "hello", same as above
    start = Pos(line=1, col=1, index=0)
    end   = Pos(line=1, col=6, index=5)
    s = Span(start, end, "hello")

    # s[1:-1] => "ell" (s[1:4])
    sliced = s[1:-1]
    assert sliced.raw == "ell"
    assert sliced.start.index == 1
    assert sliced.end.index == 4
    assert sliced.start.col == 2
    assert sliced.end.col == 5

def test_span_slice_entire_span():
    # raw = "hello"
    start = Pos(line=1, col=1, index=0)
    end   = Pos(line=1, col=6, index=5)
    s = Span(start, end, "hello")

    # s[:] => entire "hello"
    sliced = s[:]
    assert sliced.raw == "hello"
    assert sliced.start == s.start
    assert sliced.end == s.end

def test_span_slice_noop():
    # raw = "hello"
    start = Pos(line=1, col=1, index=0)
    end   = Pos(line=1, col=6, index=5)
    s = Span(start, end, "hello")

    # s[0:len(raw)] => entire "hello"
    sliced = s[0:5]
    assert sliced.raw == "hello"
    assert sliced.start == s.start
    assert sliced.end == s.end

def test_span_slice_empty():
    # Suppose the raw is "hello" => length 5
    # We'll pretend the text is all on one line for simplicity.
    start = Pos(line=1, col=1, index=0)   # start index = 0
    end   = Pos(line=1, col=6, index=5)   # end   index = 5
    s = Span(start, end, "hello")

    # s[1:1] => empty slice
    sliced = s[1:1]

    # The resulting substring is "", length 0
    assert sliced.raw == ""
    # The new slice spans zero characters, so start == end in both index and line/col
    assert sliced.start.index == 1
    assert sliced.end.index == 1
    assert sliced.start.line == 1
    assert sliced.end.line == 1
    # Since we moved forward by 1 from col=1 => col=2
    assert sliced.start.col == 2
    assert sliced.end.col == 2

def test_span_slice_empty_negative_indices():
    start = Pos(line=1, col=1, index=0)
    end   = Pos(line=1, col=6, index=5)
    s = Span(start, end, "hello")

    # s[-1:-1] => This is an empty slice in Python 
    # because both start and stop resolve to 4 (length(hello)=5 => 5 + (-1)=4).
    sliced = s[-1:-1]

    # The resulting substring should be ""
    assert sliced.raw == ""

    # Because it's an empty slice, the new Span has no characters.
    # We expect sliced.start.index == sliced.end.index == 4
    assert sliced.start.index == 4
    assert sliced.end.index == 4

    # We also expect the line to remain at 1, because we never cross a newline,
    # and to have the column offset advanced from index=0 to index=4 
    # (since "hello" from index=0..3 is 4 moves).
    # Start col was 1. Four forward steps for 'h','e','l','l' => col=5
    assert sliced.start.line == 1
    assert sliced.start.col == 5
    assert sliced.end.line == 1
    assert sliced.end.col == 5