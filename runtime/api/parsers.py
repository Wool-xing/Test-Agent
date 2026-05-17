"""Input parsers: PDF / Word / Markdown / Docker tar / APK / IPA / exe / etc.

Returns normalized TargetArtifact for the router.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from runtime.router.schema import TargetArtifact

TEXT_EXTS = {".md", ".txt", ".log", ".yaml", ".yml", ".json", ".xml", ".csv"}
PDF_EXTS = {".pdf"}
DOCX_EXTS = {".docx"}
MOBILE_EXTS = {".apk", ".ipa"}
DESKTOP_EXTS = {".exe", ".msi", ".dmg", ".app"}
DOCKER_EXTS = {".tar"}  # docker save .tar; refined by magic-bytes later


def parse_path(path: Path) -> TargetArtifact:
    ext = path.suffix.lower()
    size = path.stat().st_size if path.exists() else None
    if ext in TEXT_EXTS:
        text = _safe_read_text(path)
        return TargetArtifact(kind="file", path=str(path), text=text, mime="text/plain", size_bytes=size)
    if ext in PDF_EXTS:
        return TargetArtifact(
            kind="file",
            path=str(path),
            text=_extract_pdf(path),
            mime="application/pdf",
            size_bytes=size,
            extra={"ext": ext},
        )
    if ext in DOCX_EXTS:
        return TargetArtifact(
            kind="file",
            path=str(path),
            text=_extract_docx(path),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size_bytes=size,
            extra={"ext": ext},
        )
    if ext in MOBILE_EXTS:
        return TargetArtifact(
            kind="file",
            path=str(path),
            mime="application/octet-stream",
            size_bytes=size,
            extra={"category": "mobile-app", "ext": ext},
        )
    if ext in DESKTOP_EXTS:
        return TargetArtifact(
            kind="file",
            path=str(path),
            mime="application/octet-stream",
            size_bytes=size,
            extra={"category": "desktop-app", "ext": ext},
        )
    if ext in DOCKER_EXTS:
        return TargetArtifact(
            kind="file",
            path=str(path),
            mime="application/x-tar",
            size_bytes=size,
            extra={"category": "docker-image", "ext": ext},
        )
    if path.is_dir():
        return TargetArtifact(kind="directory", path=str(path), extra={"category": "source-repo"})
    return TargetArtifact(kind="file", path=str(path), size_bytes=size, extra={"ext": ext, "category": "unknown"})


def parse_text(text: str) -> TargetArtifact:
    return TargetArtifact(kind="text", text=text)


def parse_url(url: str) -> TargetArtifact:
    return TargetArtifact(kind="url", text=url, extra={"category": "web-system"})


def _safe_read_text(path: Path, limit: int = 200_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError as e:
        logger.warning("read text failed {}: {}", path, e)
        return ""


def _extract_pdf(path: Path, max_pages: int = 30) -> str:
    try:
        from pypdf import PdfReader  # lightweight; pdfplumber fallback omitted in v1
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages):
            if i >= max_pages:
                break
            pages.append(page.extract_text() or "")
        return "\n\n".join(pages)
    except Exception as e:  # noqa: BLE001
        logger.warning("pdf extract failed {}: {}", path, e)
        return f"[PDF_PARSE_ERROR: {path.name}]"


def _extract_docx(path: Path) -> str:
    try:
        import docx  # python-docx
    except ImportError:
        return "[DOCX_PARSE_ERROR: python-docx not installed]"
    try:
        d = docx.Document(str(path))
        return "\n".join(p.text for p in d.paragraphs)
    except Exception as e:  # noqa: BLE001
        logger.warning("docx extract failed {}: {}", path, e)
        return f"[DOCX_PARSE_ERROR: {path.name}]"
