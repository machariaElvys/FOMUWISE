import fitz
import pytest

from app.errors import ApiError
from app.services.pdf_service import extract_pdf_pages


def make_pdf(text):
    document = fitz.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    result = document.tobytes()
    document.close()
    return result


def test_extracts_text_page_by_page():
    document = fitz.open()
    first = document.new_page()
    first.insert_text((72, 72), "First page of notice")
    second = document.new_page()
    second.insert_text((72, 72), "Second page of notice")
    result = document.tobytes()
    document.close()
    pages = extract_pdf_pages(result, 30)
    assert len(pages) == 2
    assert pages[0].strip() == "First page of notice"
    assert pages[1].strip() == "Second page of notice"


def test_rejects_wrong_signature():
    with pytest.raises(ApiError) as error:
        extract_pdf_pages(b"not a pdf", 30)
    assert error.value.code == "INVALID_PDF"


def test_rejects_image_only_or_empty_text_pdf():
    with pytest.raises(ApiError) as error:
        extract_pdf_pages(make_pdf(""), 30)
    assert error.value.code == "UNSUPPORTED_SCANNED_PDF"


def test_rejects_page_limit():
    document = fitz.open()
    for _ in range(2):
        page = document.new_page()
        page.insert_text((72, 72), "A text notice")
    result = document.tobytes()
    document.close()
    with pytest.raises(ApiError) as error:
        extract_pdf_pages(result, 1)
    assert error.value.code == "TOO_MANY_PAGES"
