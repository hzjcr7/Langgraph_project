from __future__ import annotations

from pathlib import Path


def parse_document(path: str | Path) -> str:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    suffix = source.suffix.lower()
    if suffix in {".txt", ".md", ".csv", ".json"}:
        return source.read_text(encoding="utf-8")
    if suffix == ".pdf":
        return _parse_pdf(source)
    raise ValueError(f"Unsupported document type: {source.suffix}")


def _parse_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required to parse PDF files") from exc
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()

