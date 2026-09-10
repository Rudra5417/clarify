from dataclasses import dataclass
from io import BytesIO
from typing import Literal

from pypdf import PdfReader

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_FALLBACK_CHARS = 4000
MAX_PDF_PAGES = 2

Kind = Literal["pdf", "image", "text"]
Source = Literal["file", "selection", "visible_fallback"]


@dataclass(frozen=True)
class Extracted:
    kind: Kind
    text_layer: str | None
    image_bytes: bytes | None
    page_limit_hit: bool
    source: Source
    error: str | None


def extract_pdf(data: bytes) -> Extracted:
    if not data:
        return Extracted(
            kind="pdf",
            text_layer=None,
            image_bytes=None,
            page_limit_hit=False,
            source="file",
            error="empty",
        )
    try:
        reader = PdfReader(BytesIO(data))
        page_limit_hit = len(reader.pages) > MAX_PDF_PAGES
        parts: list[str] = []
        for page in reader.pages[:MAX_PDF_PAGES]:
            parts.append(page.extract_text() or "")
        text_layer = "\n".join(parts)
        if not text_layer.strip():
            return Extracted(
                kind="pdf",
                text_layer=text_layer,
                image_bytes=None,
                page_limit_hit=page_limit_hit,
                source="file",
                error="unreadable",
            )
        return Extracted(
            kind="pdf",
            text_layer=text_layer,
            image_bytes=None,
            page_limit_hit=page_limit_hit,
            source="file",
            error=None,
        )
    except Exception:
        return Extracted(
            kind="pdf",
            text_layer=None,
            image_bytes=None,
            page_limit_hit=False,
            source="file",
            error="unreadable",
        )


def extract_image(data: bytes) -> Extracted:
    if len(data) == 0:
        return Extracted(
            kind="image",
            text_layer=None,
            image_bytes=None,
            page_limit_hit=False,
            source="file",
            error="empty",
        )
    if len(data) > MAX_IMAGE_BYTES:
        return Extracted(
            kind="image",
            text_layer=None,
            image_bytes=None,
            page_limit_hit=False,
            source="file",
            error="oversize",
        )
    return Extracted(
        kind="image",
        text_layer=None,
        image_bytes=data,
        page_limit_hit=False,
        source="file",
        error=None,
    )


def extract_text(text: str, *, fallback: bool) -> Extracted:
    if fallback:
        layer = text[:MAX_FALLBACK_CHARS]
        source: Source = "visible_fallback"
    else:
        layer = text
        source = "selection"
    return Extracted(
        kind="text",
        text_layer=layer,
        image_bytes=None,
        page_limit_hit=False,
        source=source,
        error=None,
    )
