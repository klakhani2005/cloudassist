"""Document validation shared by the upload API and the S3-triggered Lambda."""
from pathlib import PurePath

ALLOWED_SUFFIXES = {".txt", ".md"}


class InvalidDocument(ValueError):
    """Raised when a document fails validation. `status` maps to an HTTP code."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def validate_document(filename: str, raw: bytes, max_bytes: int) -> tuple[str, str]:
    """Return (clean_name, text) or raise InvalidDocument."""
    name = PurePath(filename or "").name
    if not name:
        raise InvalidDocument("Missing file name")
    if PurePath(name).suffix.lower() not in ALLOWED_SUFFIXES:
        raise InvalidDocument("Only .txt and .md files are supported", status=415)
    if len(raw) > max_bytes:
        raise InvalidDocument(f"File exceeds {max_bytes // 1_000_000} MB limit", status=413)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise InvalidDocument("File must be UTF-8 encoded")
    if not text.strip():
        raise InvalidDocument("Document is empty")
    return name, text
