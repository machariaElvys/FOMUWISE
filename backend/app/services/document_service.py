import hashlib
import hmac

from app import db
from app.errors import ApiError
from app.models import Document
from app.time_utils import utcnow


def token_digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def delete_expired_documents():
    expired = Document.query.filter(Document.expires_at <= utcnow()).all()
    for document in expired:
        db.session.delete(document)
    if expired:
        db.session.commit()


def authenticate_document(document_id, token):
    document = db.session.get(Document, document_id)
    if document is None:
        raise ApiError("DOCUMENT_NOT_FOUND", "This document workspace was not found.", 404)
    if document.expires_at <= utcnow():
        db.session.delete(document)
        db.session.commit()
        raise ApiError(
            "DOCUMENT_EXPIRED",
            "This document workspace has expired. Upload the notice again.",
            410,
        )
    if not token:
        raise ApiError("DOCUMENT_TOKEN_REQUIRED", "A document access token is required.", 401)
    if not hmac.compare_digest(token_digest(token), document.access_token_hash):
        raise ApiError("INVALID_DOCUMENT_TOKEN", "The document access token is invalid.", 401)
    return document


def document_payload(document):
    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "mime_type": document.mime_type,
        "file_size_bytes": document.file_size_bytes,
        "page_count": document.page_count,
        "created_at": document.created_at.isoformat() + "Z",
        "expires_at": document.expires_at.isoformat() + "Z",
        "analysis": document.analysis_json,
    }
