import hashlib
import math
import re
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

import ragforge
from ragforge.chunking import split_lines
from ragforge.retrieval import LocalQdrantIndex

CORPUS = Path(__file__).parent.parent / "fixtures" / "corpus"
runner = CliRunner()


class FakeEmbedder:
    """Hashed bag of words: no torch, no download, and predictable nearest neighbours."""

    model_name = "fake/bag-of-words"
    dim = 1024

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for word in re.findall(r"[a-z]+", text.lower()):
            v[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


@pytest.fixture
def docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A writable copy of the corpus, with the index in tmp_path and the fake embedder."""
    docs = tmp_path / "docs"
    shutil.copytree(CORPUS, docs)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAGFORGE_INDEX_DIR", str(tmp_path / ".ragforge"))
    monkeypatch.setattr(ragforge, "make_embedder", lambda settings: FakeEmbedder())
    return docs


def _point_count(tmp_path: Path) -> int:
    with LocalQdrantIndex(tmp_path / ".ragforge", FakeEmbedder()) as idx:
        return idx.count()


# --- chunking ---


def test_split_lines_tracks_line_ranges_with_overlap() -> None:
    text = "\n".join(f"line {i:02d}" for i in range(1, 11))  # 10 lines of 7 chars
    chunks = split_lines("f.md", text, max_chars=32, overlap_lines=1)

    assert [(c.start_line, c.end_line) for c in chunks] == [(1, 4), (4, 7), (7, 10)]
    assert chunks[1].text.splitlines()[0] == "line 04"


def test_split_lines_keeps_an_overlong_line_whole_and_skips_blank_chunks() -> None:
    text = "short\n" + "x" * 500 + "\n\n\n"
    chunks = split_lines("f.md", text, max_chars=100, overlap_lines=0)

    assert [(c.start_line, c.end_line) for c in chunks] == [(1, 1), (2, 2)]
    assert len(chunks[1].text) == 500


def test_split_lines_caps_overlap_at_half_a_chunk() -> None:
    # A huge overlap used to advance one line per chunk: 17 chunks here instead of ~5.
    text = "\n".join(f"line {i:02d}" for i in range(1, 21))  # 20 lines, 4 per chunk
    chunks = split_lines("f.md", text, max_chars=32, overlap_lines=50)

    assert [c.start_line for c in chunks] == [1, 3, 5, 7, 9, 11, 13, 15, 17]
    assert chunks[-1].end_line == 20


def test_split_lines_counts_only_newlines_as_line_breaks() -> None:
    # Editors and grep -n don't break lines on \f or U+2028, so citations mustn't either.
    text = "one\r\ntwo \f page\r\nthree   sep\nfour\n"
    chunks = split_lines("f.md", text, max_chars=1000, overlap_lines=0)

    assert [(c.start_line, c.end_line) for c in chunks] == [(1, 4)]
    assert chunks[0].text.split("\n")[3] == "four"


# --- CLI ---


def test_ask_cites_the_matching_file_and_line(docs: Path) -> None:
    result = runner.invoke(ragforge.app, ["ask", "docs", "which environment variables prefix"])

    assert result.exit_code == 0, result.output
    first = result.output.splitlines()[0]
    assert first.startswith("1. docs/config.md:1-")
    assert "docs/notes.txt" not in first


def test_index_skips_non_doc_files_and_is_idempotent(docs: Path, tmp_path: Path) -> None:
    first = runner.invoke(ragforge.app, ["index", "docs"])
    count = _point_count(tmp_path)
    second = runner.invoke(ragforge.app, ["index", "docs"])

    assert first.exit_code == 0, first.output
    assert "Indexed 3 file(s)" in first.output  # ignored.py is not a doc
    assert "Indexed 0 file(s), 3 unchanged" in second.output
    assert _point_count(tmp_path) == count > 0


def test_edited_file_is_reindexed_and_deleted_file_is_removed(docs: Path) -> None:
    runner.invoke(ragforge.app, ["index", "docs"])
    (docs / "notes.txt").write_text("Penguins waddle across the ice.\n")
    (docs / "guides" / "retrieval.md").unlink()

    result = runner.invoke(ragforge.app, ["ask", "docs", "penguins ice"])

    assert result.exit_code == 0, result.output
    assert result.output.splitlines()[0].startswith("1. docs/notes.txt:1-1")
    assert "Kittens" not in result.output
    assert "retrieval.md" not in result.output


def test_ask_only_searches_the_given_folder(docs: Path) -> None:
    runner.invoke(ragforge.app, ["index", "docs"])

    result = runner.invoke(ragforge.app, ["ask", "docs/guides", "environment variables prefix"])

    assert result.exit_code == 0, result.output
    assert "config.md" not in result.output
    assert "retrieval.md" in result.output


def test_changed_chunk_settings_reindex_unchanged_files(
    docs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner.invoke(ragforge.app, ["index", "docs"])
    monkeypatch.setenv("RAGFORGE_CHUNK_OVERLAP_LINES", "0")

    result = runner.invoke(ragforge.app, ["index", "docs"])

    assert "Indexed 3 file(s), 0 unchanged" in result.output, result.output


def test_file_that_stops_being_utf8_loses_its_old_chunks(docs: Path) -> None:
    runner.invoke(ragforge.app, ["index", "docs"])
    (docs / "notes.txt").write_bytes("Pingüinos en el hielo.\n".encode("latin-1"))

    result = runner.invoke(ragforge.app, ["ask", "docs", "kittens afternoon"])

    assert result.exit_code == 0, result.output
    assert "skipped (not UTF-8): docs/notes.txt" in result.output
    assert "Kittens" not in result.output


def test_indexing_a_subfolder_keeps_the_parent_index_intact(docs: Path) -> None:
    runner.invoke(ragforge.app, ["index", "docs"])
    runner.invoke(ragforge.app, ["ask", "docs/guides", "retrieval"])

    result = runner.invoke(ragforge.app, ["index", "docs"])

    assert "Indexed 0 file(s), 3 unchanged" in result.output, result.output


def test_paths_with_brackets_are_printed_verbatim(docs: Path) -> None:
    (docs / "notes[draft].md").write_text("Penguins waddle across the ice.\n")
    (docs / "odd[").mkdir()
    (docs / "odd[" / "x].md").write_text("Walruses bask on the ice floes.\n")  # "[/x]" in path

    result = runner.invoke(ragforge.app, ["ask", "docs", "penguins waddle ice walruses"])

    assert result.exit_code == 0, result.output
    assert "docs/notes[draft].md:1-1" in result.output
    assert "docs/odd[/x].md:1-1" in result.output


def test_blank_file_counts_as_unchanged_on_rerun(docs: Path) -> None:
    (docs / "TODO.md").write_text("  \n\n")
    runner.invoke(ragforge.app, ["index", "docs"])

    result = runner.invoke(ragforge.app, ["index", "docs"])

    assert "Indexed 0 file(s), 4 unchanged" in result.output, result.output


def test_folder_of_only_non_utf8_docs_says_so(tmp_path: Path, docs: Path) -> None:
    latin = tmp_path / "latin"
    latin.mkdir()
    (latin / "a.txt").write_bytes("Pingüinos.\n".encode("latin-1"))

    result = runner.invoke(ragforge.app, ["ask", "latin", "anything"])

    assert result.exit_code == 1
    assert "No UTF-8 .md, .markdown or .txt files under latin" in result.output
    assert "1 skipped" in result.output


def test_display_keeps_dot_dot_names_and_survives_other_drives(
    docs: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert ragforge._display(str(tmp_path / "..notes.md")) == "..notes.md"
    outside = str(tmp_path.parent / "x.md")
    assert ragforge._display(outside) == outside

    def other_drive(path: str, start: str = ".") -> str:
        raise ValueError("path is on mount 'D:', start on mount 'C:'")

    monkeypatch.setattr(ragforge.os.path, "relpath", other_drive)
    assert ragforge._display("D:/docs/a.md") == "D:/docs/a.md"


def test_folder_without_docs_fails_clearly(tmp_path: Path, docs: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "script.py").write_text("x = 1\n")

    result = runner.invoke(ragforge.app, ["ask", "empty", "anything"])

    assert result.exit_code == 1
    assert "No .md, .markdown or .txt files found" in result.output


def test_help_lists_both_commands() -> None:
    result = runner.invoke(ragforge.app, ["--help"])

    assert result.exit_code == 0
    assert "index" in result.output and "ask" in result.output
