import os
import re
import tempfile

import fitz

from app.errors import ApiError


def extract_pdf_pages(pdf_bytes, max_pages):
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-"):
        raise ApiError("INVALID_PDF", "The selected file is not a valid PDF.", 415)

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="fomuwise-", suffix=".pdf", delete=False) as temp:
            temporary_path = temp.name
            temp.write(pdf_bytes)
        try:
            document = fitz.open(temporary_path)
        except Exception:
            raise ApiError("UNREADABLE_PDF", "FomuWise could not read this PDF.", 422)

        with document:
            if document.is_encrypted:
                raise ApiError(
                    "ENCRYPTED_PDF",
                    "This PDF is password-protected. Remove the password and try again.",
                    422,
                )
            if document.page_count < 1:
                raise ApiError("EMPTY_PDF", "This PDF has no pages.", 422)
            if document.page_count > max_pages:
                raise ApiError(
                    "TOO_MANY_PAGES",
                    "This PDF has more than the {} page limit.".format(max_pages),
                    413,
                )
            pages = [page.get_text("text") for page in document]
    except ApiError:
        raise
    except Exception:
        raise ApiError("UNREADABLE_PDF", "FomuWise could not read this PDF.", 422)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            try:
                os.remove(temporary_path)
            except OSError:
                pass

    meaningful = any(re.search(r"[\w]{2,}", text, flags=re.UNICODE) for text in pages)
    if not meaningful:
        raise ApiError(
            "UNSUPPORTED_SCANNED_PDF",
            "This PDF has no selectable text. Scanned PDFs are not supported yet.",
            422,
        )
    return pages
