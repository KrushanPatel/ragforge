from pathlib import Path

import pytest

from ragforge.loaders import load_directory, load_file


def test_load_txt(tmp_path: Path):
    f = tmp_path / "note.txt"
    f.write_text("hello world", encoding="utf-8")
    docs = load_file(f)
    assert len(docs) == 1
    assert docs[0].text == "hello world"
    assert docs[0].metadata["source"] == "note.txt"


def test_load_md(tmp_path: Path):
    f = tmp_path / "readme.md"
    f.write_text("# Title\n\nBody", encoding="utf-8")
    assert load_file(f)[0].text.startswith("# Title")


def test_unsupported_extension_raises(tmp_path: Path):
    f = tmp_path / "data.csv"
    f.write_text("a,b", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported"):
        load_file(f)


def test_load_directory_skips_unsupported(tmp_path: Path):
    (tmp_path / "a.txt").write_text("A", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.md").write_text("B", encoding="utf-8")
    (tmp_path / "ignore.csv").write_text("x", encoding="utf-8")
    docs = load_directory(tmp_path)
    assert sorted(d.text for d in docs) == ["A", "B"]
