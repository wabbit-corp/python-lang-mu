from dataclasses import dataclass

@dataclass
class Pos:
    line: int
    col: int
    index: int

    def forward_via(self, char: str):
        assert len(char) == 1

        if char == '\n':
            return Pos(self.line + 1, 1, self.index + 1)
        else:
            return Pos(self.line, self.col + 1, self.index + 1)
    
    def backward_via(self, char: str):
        assert len(char) == 1

        if char == '\n':
            raise ValueError("Cannot move backwards over a newline")
        else:
            return Pos(self.line, self.col - 1, self.index - 1)

@dataclass
class Span:
    start: Pos
    end: Pos
    raw: str

    def __post_init__(self):
        assert len(self.raw) == self.end.index - self.start.index

    def __getitem__(self, key):
        assert isinstance(key, slice)

        # 1. Extract raw string length
        length = len(self.raw)

        # 2. Convert slice.start and slice.stop to valid integer offsets
        #    handling None and negative values (Python-style).
        start_offset = key.start if key.start is not None else 0
        stop_offset = key.stop if key.stop is not None else length

        if start_offset < 0:
            start_offset = length + start_offset
        if stop_offset < 0:
            stop_offset = length + stop_offset

        # 3. Clamp to avoid out-of-range issues
        if start_offset < 0:
            start_offset = 0
        if start_offset > length:
            start_offset = length
        if stop_offset < 0:
            stop_offset = 0
        if stop_offset > length:
            stop_offset = length

        # 4. Prepare new start/end
        new_start = self.start
        new_end = self.end

        # Move new_start forward by start_offset
        for i in range(start_offset):
            new_start = new_start.forward_via(self.raw[i])

        # Move new_end backward for the part after stop_offset
        chars_to_trim_from_end = length - stop_offset
        for i in range(chars_to_trim_from_end):
            new_end = new_end.backward_via(self.raw[-i - 1])

        new_raw = self.raw[start_offset:stop_offset]
        return Span(new_start, new_end, new_raw)
    
    def __add__(self, other: 'Span') -> 'Span':
        """
        Merge two spans if they are contiguous, meaning:
        self.end.index == other.start.index.

        If not contiguous, raises ValueError.
        """
        if self.end.index != other.start.index:
            raise ValueError(
                f"Cannot add spans that are not contiguous: "
                f"self.end.index={self.end.index}, other.start.index={other.start.index}"
            )

        # Construct the new raw text.
        new_start = self.start
        new_raw = self.raw + other.raw
        new_end = other.end
        return Span(new_start, new_end, new_raw)

class _Input:
    EOS = '\0'

    def __init__(self, str: str):
        self.str = str

        self.index = 0
        self.line = 1
        self.column = 1

        self.mark_index = 0
        self.mark_line = 1
        self.mark_column = 1
        
        self.current = _Input.EOS if len(str) == 0 else str[0]

    @property
    def position(self) -> Pos:
        return Pos(self.line, self.column, self.index)

    def next(self):
        if self.index < len(self.str):
            if self.current == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1

            self.index += 1
            self.current = _Input.EOS if self.index >= len(self.str) else self.str[self.index]
        else:
            self.current = _Input.EOS

    def capture(self) -> Span:
        start_pos = Pos(self.mark_line, self.mark_column, self.mark_index)
        result = Span(start_pos, self.position, self.str[self.mark_index:self.index])
        self.mark_index = self.index
        self.mark_line = self.line
        self.mark_column = self.column
        return result

    def __repr__(self) -> str:
        start_index = max(0, self.index - 8)
        end_index = min(len(self.str), self.index + 8)

        chars = []
        for i in range(start_index, end_index):
            char = self.str[i]
            if char == ' ':
                char = '·'
            if char == '\n':
                char = '\\n'
            elif char == '\t':
                char = '\\t'
            elif not char.isprintable():
                char = f"\\x{ord(char):02x}"

            if i == self.index:
                chars.append(f"[{char}]")
            else:
                chars.append(char)

        snippet = ' '.join(chars)

        return f"Input(line={self.line}, column={self.column}, {snippet})"

DEBUG_ENABLED = False
DEBUG_DEPTH = 0

# debug decorator
def debug(func):
    if not DEBUG_ENABLED:
        return func

    def wrapper(*args, **kwargs):
        global DEBUG_DEPTH
        saved_depth = DEBUG_DEPTH
        prefix = '  ' * DEBUG_DEPTH
        print(f"{prefix}{func.__name__}({', '.join(repr(x) for x in args)}, {kwargs}) {{")
        try:
            DEBUG_DEPTH += 1
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            exception = e
            raise e
        finally:
            if 'exception' in locals():
                print(f"{prefix}}}raise {exception}")
            else:
                print(f"{'  ' * DEBUG_DEPTH}return {repr(result)}")
            DEBUG_DEPTH -= 1
            assert saved_depth == DEBUG_DEPTH
            print(f"{prefix}}}")
    return wrapper