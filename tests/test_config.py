from ragforge.config import Settings


def test_env_override(monkeypatch):
    monkeypatch.setenv("RAG_TOP_K", "8")
    assert Settings(_env_file=None).top_k == 8


def test_defaults():
    s = Settings(_env_file=None)
    assert s.chunk_overlap < s.chunk_size
