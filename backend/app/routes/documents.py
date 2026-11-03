import json
import secrets
import uuid
from datetime import timedelta
from time import perf_counter

from flask import Blueprint, current_app, g, jsonify, request

from app import db
from app.errors import ApiError
from app.models import Document, DocumentPage
from app.services.analysis_service import analyze_pages
from app.services.document_service import (
    authenticate_document,
    delete_expired_documents,
    document_payload,
    token_digest,
)
from app.services.gemma_service import GemmaService
from app.services.pdf_service import extract_pdf_pages
from app.services.question_service import answer_question
from app.time_utils import utcnow

documents_bp = Blueprint("documents", __name__)


@documents_bp.after_request
def log_document_analysis_metrics(response):
    metrics = getattr(g, "fomuwise_analysis_metrics", None)
    if metrics is not None:
        event = {key: value for key, value in metrics.items() if not key.startswith("_")}
        event.update(
            {
                "event": "document_analysis",
                "http_status": response.status_code,
                "total_endpoint_seconds": round(perf_counter() - metrics["_started"], 3),
            }
        )
        current_app.logger.info("fomuwise_analysis %s", json.dumps(event, sort_keys=True))
    return response


def _filename(upload_name):
    name = (upload_name or "").replace("\\", "/").split("/")[-1].strip()
    return name[:255] or "application-notice.pdf"


def _gemma():
    service = current_app.config.get("GEMMA_SERVICE")
    return service if service is not None else GemmaService.from_config(current_app.config)


@documents_bp.post("/documents")
def upload_document():
    metrics = {
        "request_id": uuid.uuid4().hex[:12],
        "_started": perf_counter(),
        "pdf_extraction_seconds": None,
        "extracted_text_characters": 0,
        "prompt_construction_seconds": 0.0,
        "initial_prompt_characters": 0,
        "gemini_request_seconds": 0.0,
        "gemini_input_characters": 0,
        "gemini_output_characters": 0,
        "ai_call_count": 0,
        "database_save_seconds": None,
        "expired_document_cleanup_seconds": None,
        "token_usage": {},
        "json_repair_used": False,
    }
    g.fomuwise_analysis_metrics = metrics
    if "file" not in request.files:
        raise ApiError("FILE_REQUIRED", "Choose a PDF file to analyse.", 400)
    upload = request.files["file"]
    if not upload.filename:
        raise ApiError("FILE_REQUIRED", "Choose a PDF file to analyse.", 400)

    max_bytes = current_app.config["MAX_UPLOAD_MB"] * 1024 * 1024
    pdf_bytes = upload.stream.read(max_bytes + 1)
    if len(pdf_bytes) > max_bytes:
        raise ApiError("UPLOAD_TOO_LARGE", "The PDF exceeds the configured upload limit.", 413)

    extraction_started = perf_counter()
    try:
        pages = extract_pdf_pages(pdf_bytes, current_app.config["MAX_PDF_PAGES"])
    finally:
        metrics["pdf_extraction_seconds"] = round(perf_counter() - extraction_started, 3)
    extracted_chars = sum(len(page) for page in pages)
    metrics["extracted_text_characters"] = extracted_chars
    if extracted_chars > current_app.config["MAX_TEXT_CHARS"]:
        raise ApiError(
            "TEXT_TOO_LONG",
            "This PDF contains more text than FomuWise can process at once.",
            413,
        )
    analysis = analyze_pages(pages, _gemma(), metrics=metrics)
    now = utcnow()
    access_token = secrets.token_urlsafe(32)
    document = Document(
        document_id=str(uuid.uuid4()),
        filename=_filename(upload.filename),
        mime_type="application/pdf",
        file_size_bytes=len(pdf_bytes),
        page_count=len(pages),
        analysis_json=analysis,
        access_token_hash=token_digest(access_token),
        created_at=now,
        expires_at=now + timedelta(hours=current_app.config["DOCUMENT_TTL_HOURS"]),
        pages=[
            DocumentPage(page_number=index, page_text=text)
            for index, text in enumerate(pages, start=1)
        ],
    )

    database_started = perf_counter()
    cleanup_started = perf_counter()
    try:
        try:
            delete_expired_documents()
        finally:
            metrics["expired_document_cleanup_seconds"] = round(
                perf_counter() - cleanup_started, 3
            )
        db.session.add(document)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.error("Document persistence failed")
        raise ApiError(
            "DATABASE_UNAVAILABLE",
            "The temporary workspace could not be saved. Please try again.",
            503,
        )
    finally:
        metrics["database_save_seconds"] = round(perf_counter() - database_started, 3)

    payload = document_payload(document)
    payload["access_token"] = access_token
    return jsonify(payload), 201


@documents_bp.get("/documents/<document_id>")
def get_document(document_id):
    document = authenticate_document(document_id, request.headers.get("X-Document-Token"))
    return jsonify(document_payload(document))


@documents_bp.post("/documents/<document_id>/questions")
def ask_question(document_id):
    document = authenticate_document(document_id, request.headers.get("X-Document-Token"))
    body = request.get_json(silent=True)
    question_value = body.get("question") if isinstance(body, dict) else None
    if not isinstance(question_value, str):
        raise ApiError("INVALID_QUESTION", "Enter a question with at least 5 characters.", 400)
    question = question_value.strip()
    if len(question) < 5:
        raise ApiError("INVALID_QUESTION", "Enter a question with at least 5 characters.", 400)
    if len(question) > current_app.config["MAX_QUESTION_LENGTH"]:
        raise ApiError(
            "QUESTION_TOO_LONG",
            "Keep your question under {} characters.".format(
                current_app.config["MAX_QUESTION_LENGTH"]
            ),
            413,
        )

    pages = {page.page_number: page.page_text for page in document.pages}
    result = answer_question(
        question,
        pages,
        _gemma(),
        current_app.config["MAX_PROMPT_CHARS"],
    )
    return jsonify(result)


@documents_bp.delete("/documents/<document_id>")
def delete_document(document_id):
    document = authenticate_document(document_id, request.headers.get("X-Document-Token"))
    db.session.delete(document)
    db.session.commit()
    return jsonify({"deleted": True, "document_id": document_id})
