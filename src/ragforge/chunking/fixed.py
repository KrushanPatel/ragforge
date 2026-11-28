"""Fixed-size chunking on whole lines, so every chunk knows its exact line range."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    path: str
    start_line: int  # 1-based, inclusive
    end_line: int  # 1-based, inclusive
    text: str


def split_lines(path: str, text: str, max_chars: int, overlap_lines: int) -> list[Chunk]:
    """Group whole lines into chunks of at most ``max_chars``.

    A single line longer than ``max_chars`` becomes its own chunk. Each new chunk starts
    ``overlap_lines`` lines before the previous one ended (capped at half the previous
    chunk's lines), but always moves forward.
    Only ``\\n`` (or ``\\r\\n``) ends a line, as in editors and ``grep -n``, so cited
    line numbers match: ``str.splitlines`` would also split on ``\\f`` and U+2028.
    """
    lines = [line.removesuffix("\r") for line in text.split("\n")]
    if lines[-1] == "":  # a trailing newline ends the last line; it doesn't start a new one
        lines.pop()
    chunks: list[Chunk] = []
    start = 0
    while start < len(lines):
        end, size = start, 0
        while end < len(lines) and (end == start or size + len(lines[end]) + 1 <= max_chars):
            size += len(lines[end]) + 1
            end += 1
        body = "\n".join(lines[start:end])
        if body.strip():
            chunks.append(Chunk(path, start + 1, end, body))
        if end >= len(lines):
            break
        # Overlap at most half the chunk, so a large setting can't make chunks advance
        # one line at a time (each line then lands in at most two chunks).
        start = max(end - min(overlap_lines, (end - start) // 2), start + 1)
    return chunks
