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
    ``overlap_lines`` lines before the previous one ended, but always moves forward.
    """
    lines = text.splitlines()
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
        start = max(end - overlap_lines, start + 1)
    return chunks
