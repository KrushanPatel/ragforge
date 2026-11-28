from typing import Protocol


class Embedder(Protocol):
    """Turns text into vectors. Shared by embedded mode and the production pipeline."""

    @property
    def model_name(self) -> str: ...

    @property
    def dim(self) -> int: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...
