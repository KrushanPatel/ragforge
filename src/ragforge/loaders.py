from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


@dataclass
class Document:
    text: str
    metadata: dict = field(default_factory=dict)


def load_file(path: Path) -> list[Document]:
    path = Path(path)
    ext = path.suffix.lower()
    base = {"source": path.name, "path": str(path.resolve())}

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return [
            Document(page.extract_text() or "", {**base, "page": i + 1})
            for i, page in enumerate(reader.pages)
        ]
    if ext == ".docx":
        import docx

        d = docx.Document(str(path))
        return [Document("\n\n".join(p.text for p in d.paragraphs), base)]
    if ext in {".txt", ".md"}:
        return [Document(path.read_text(encoding="utf-8", errors="ignore"), base)]
    raise ValueError(f"Unsupported file type: {ext} ({path.name})")


def load_directory(directory: Path) -> list[Document]:
    docs: list[Document] = []
    for path in sorted(Path(directory).rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            docs.extend(load_file(path))
    return docs
