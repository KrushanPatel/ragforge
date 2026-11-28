from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class SentenceTransformerEmbedder:
    """Local CPU embeddings. torch is imported on first use, so the CLI starts fast."""

    def __init__(self, model_name: str, query_prefix: str = "") -> None:
        self._model_name = model_name
        self._query_prefix = query_prefix

    @cached_property
    def _model(self) -> "SentenceTransformer":
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self._model_name, device="cpu")

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dim(self) -> int:
        dim = self._model.get_embedding_dimension()
        if dim is None:
            raise ValueError(f"{self._model_name} does not report an embedding dimension")
        return dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True, batch_size=32)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(self._query_prefix + text, normalize_embeddings=True).tolist()
