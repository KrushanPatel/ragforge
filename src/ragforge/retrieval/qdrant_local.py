"""Embedded mode: a Qdrant local-mode index on disk, so no server or Docker is needed."""

import hashlib
import re
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from qdrant_client import QdrantClient, models

from ragforge.chunking import Chunk, split_lines
from ragforge.embeddings import Embedder
from ragforge.retrieval.base import Hit

SUFFIXES = {".md", ".markdown", ".txt"}
HIT_FIELDS = ("path", "start_line", "end_line", "text")
# A stored file is up to date only if all of these match; changing any one re-chunks it.
VERSION_FIELDS = ("file_sha256", "chunk_chars", "chunk_overlap_lines")


@dataclass
class SyncReport:
    indexed: list[str] = field(default_factory=list)
    unchanged: int = 0
    removed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # not UTF-8


def find_files(root: Path) -> list[Path]:
    """Markdown and text files under ``root``, skipping hidden folders like .git and .venv."""
    if root.is_file():
        return [root] if root.suffix.lower() in SUFFIXES else []
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix.lower() in SUFFIXES
        and not any(part.startswith(".") for part in p.relative_to(root).parts)
    )


def _match(**values: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(key=k, match=models.MatchValue(value=v))
            for k, v in values.items()
        ]
    )


def _root_filter(root: str | None) -> models.Filter | None:
    """Limit a query to one indexed folder, or search everything when ``root`` is None."""
    return _match(root=root) if root else None


class LocalQdrantIndex:
    def __init__(self, index_dir: Path, embedder: Embedder) -> None:
        self._client = QdrantClient(path=str(index_dir))
        self._embedder = embedder
        self._collection = "ragforge_" + re.sub(r"\W", "_", embedder.model_name)

    def __enter__(self) -> "LocalQdrantIndex":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._client.close()

    def _ensure_collection(self) -> None:
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                self._collection,
                vectors_config=models.VectorParams(
                    size=self._embedder.dim, distance=models.Distance.COSINE
                ),
            )

    def _stored_versions(self, root: str) -> dict[str, dict[str, object]]:
        """For each file indexed under ``root``, the payload fields in ``VERSION_FIELDS``."""
        versions: dict[str, dict[str, object]] = {}
        offset = None
        while True:
            points, offset = self._client.scroll(
                self._collection,
                _match(root=root),
                limit=1000,
                offset=offset,
                with_payload=["path", *VERSION_FIELDS],
                with_vectors=False,
            )
            for p in points:
                assert p.payload is not None
                versions[p.payload["path"]] = {f: p.payload.get(f) for f in VERSION_FIELDS}
            if offset is None:
                return versions

    def sync(self, root: Path, chunk_chars: int, overlap_lines: int) -> SyncReport:
        """Bring the index in line with ``root``: add new or changed files, drop deleted ones.

        A file is re-chunked when its content or the chunk settings changed since it was
        indexed.
        """
        self._ensure_collection()
        root_key = str(root.resolve())
        stored = self._stored_versions(root_key)
        report = SyncReport()
        seen: set[str] = set()
        for file in find_files(root):
            path, data = str(file.resolve()), file.read_bytes()
            seen.add(path)
            version = {
                "file_sha256": hashlib.sha256(data).hexdigest(),
                "chunk_chars": chunk_chars,
                "chunk_overlap_lines": overlap_lines,
            }
            if stored.get(path) == version:
                report.unchanged += 1
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                # Drop chunks from an earlier UTF-8 version, so ask can't cite stale text.
                self._client.delete(self._collection, _match(root=root_key, path=path))
                report.skipped.append(path)
                continue
            chunks = split_lines(path, text, chunk_chars, overlap_lines)
            if not chunks and path not in stored:
                # A blank file stores no points, so it never matches a stored version.
                # With nothing old to drop either, there is nothing to do.
                report.unchanged += 1
                continue
            self._replace_file(root_key, path, version, chunks)
            report.indexed.append(path)
        for path in stored.keys() - seen:
            self._client.delete(self._collection, _match(root=root_key, path=path))
            report.removed.append(path)
        return report

    def _replace_file(
        self, root_key: str, path: str, version: dict[str, object], chunks: list[Chunk]
    ) -> None:
        """Drop a file's old points, then store its new chunks (none if the file is blank)."""
        self._client.delete(self._collection, _match(root=root_key, path=path))
        if not chunks:
            return
        vectors = self._embedder.embed_documents([c.text for c in chunks])
        extra = {"root": root_key, "embed_model": self._embedder.model_name} | version
        sha = version["file_sha256"]
        points = [
            models.PointStruct(
                # The root is part of the ID, so overlapping folders keep separate points.
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{root_key}:{path}:{c.start_line}:{sha}")),
                vector=vector,
                payload=asdict(c) | extra,
            )
            for c, vector in zip(chunks, vectors, strict=True)
        ]
        self._client.upsert(self._collection, points)

    def search(self, query_vector: list[float], k: int, root: str | None = None) -> list[Hit]:
        if not self._client.collection_exists(self._collection):
            return []
        result = self._client.query_points(
            self._collection,
            query=query_vector,
            limit=k,
            with_payload=True,
            query_filter=_root_filter(root),
        )
        return [
            Hit(score=p.score, **{f: (p.payload or {})[f] for f in HIT_FIELDS})
            for p in result.points
        ]

    def count(self, root: str | None = None) -> int:
        if not self._client.collection_exists(self._collection):
            return 0
        return self._client.count(self._collection, count_filter=_root_filter(root)).count
