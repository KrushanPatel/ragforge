from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Hit:
    path: str
    start_line: int
    end_line: int
    score: float
    text: str


class Retriever(Protocol):
    """Finds the chunks nearest a query vector. Shared by embedded mode and production."""

    def search(self, query_vector: list[float], k: int, root: str | None = None) -> list[Hit]: ...
