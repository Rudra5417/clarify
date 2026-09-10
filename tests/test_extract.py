from clarify.extract import (
    MAX_FALLBACK_CHARS,
    MAX_IMAGE_BYTES,
    extract_image,
    extract_pdf,
    extract_text,
)
from tests.fixtures.make_pdf import pdf_with_n_pages, pdf_with_text


def test_pdf_over_two_pages_sets_page_limit_hit():
    data = pdf_with_n_pages(3)
    out = extract_pdf(data)
    assert out.page_limit_hit is True
    assert out.error is None
    assert "page 1" in (out.text_layer or "")
    assert "page 3" not in (out.text_layer or "")


def test_image_over_10mb_errors():
    out = extract_image(b"x" * (MAX_IMAGE_BYTES + 1))
    assert out.error == "oversize"


def test_empty_image_errors():
    out = extract_image(b"")
    assert out.error == "empty"


def test_visible_fallback_truncates_and_flags():
    out = extract_text("a" * 5000, fallback=True)
    assert out.source == "visible_fallback"
    assert len(out.text_layer or "") == MAX_FALLBACK_CHARS


def test_selection_is_not_fallback():
    out = extract_text("selected cells\t100", fallback=False)
    assert out.source == "selection"
    assert out.text_layer == "selected cells\t100"
