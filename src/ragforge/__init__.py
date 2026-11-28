"""ragforge CLI. Embedded mode: index and ask over local docs, with no server or API key."""

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from ragforge.config import Settings
from ragforge.embeddings import Embedder, SentenceTransformerEmbedder
from ragforge.retrieval import LocalQdrantIndex, SyncReport

app = typer.Typer(
    help="Ask questions over your own docs, with cited passages.", no_args_is_help=True
)
console = Console()

PathArg = Annotated[
    Path, typer.Argument(exists=True, help="Folder (or file) of Markdown/text docs.")
]


def make_embedder(settings: Settings) -> Embedder:
    return SentenceTransformerEmbedder(settings.embed_model, settings.embed_query_prefix)


def _display(path: str) -> str:
    rel = os.path.relpath(path)
    return path if rel.startswith("..") else rel


def _sync(index: LocalQdrantIndex, path: Path, settings: Settings) -> SyncReport:
    report = index.sync(path, settings.chunk_chars, settings.chunk_overlap_lines)
    for skipped in report.skipped:
        console.print(f"[yellow]skipped (not UTF-8):[/] {_display(skipped)}")
    if not (report.indexed or report.unchanged):
        console.print(f"[red]No .md, .markdown or .txt files found under {path}[/]")
        raise typer.Exit(1)
    return report


@app.command()
def index(path: PathArg) -> None:
    """Index Markdown and text files under PATH into the local store."""
    settings = Settings()
    with LocalQdrantIndex(settings.index_dir, make_embedder(settings)) as idx:
        r = _sync(idx, path, settings)
        console.print(
            f"Indexed {len(r.indexed)} file(s), {r.unchanged} unchanged, {len(r.removed)} "
            f"removed. {idx.count(str(path.resolve()))} chunks in {settings.index_dir}/"
        )


@app.command()
def ask(path: PathArg, question: str) -> None:
    """Index PATH if needed, then print the passages that best answer QUESTION."""
    settings = Settings()
    embedder = make_embedder(settings)
    with LocalQdrantIndex(settings.index_dir, embedder) as idx:
        _sync(idx, path, settings)
        hits = idx.search(embedder.embed_query(question), settings.top_k, str(path.resolve()))
    for rank, hit in enumerate(hits, 1):
        console.print(
            f"[bold]{rank}. {_display(hit.path)}:{hit.start_line}-{hit.end_line}[/]"
            f"  [dim]({hit.score:.2f})[/]",
            highlight=False,
        )
        console.print(hit.text.strip(), markup=False, highlight=False)
        console.print()


def main() -> None:
    app()
