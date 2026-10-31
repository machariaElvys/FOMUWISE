# API contract

Base URL: `http://localhost:5000/api/v1`

All error responses use `{ "error": { "code": "...", "message": "..." } }`.

## `GET /health`

Returns `200 { "status": "ok", "service": "fomuwise-api" }`.

## `POST /documents`

Multipart form with one `file` field (PDF, maximum 10 MB and 30 pages by default). Returns `201` with the document metadata, analysis, and a random `access_token`. The client must keep the token private and send it in `X-Document-Token` for later operations.

Analysis includes `summary`, `eligibility_requirements`, `required_documents`, `deadlines`, `application_steps`, and `warnings`. Every retained item includes its `page_number` and `evidence_quote`. Unverified model claims are discarded.

## `GET /documents/{document_id}`

Requires `X-Document-Token`. Returns document metadata and analysis; the token is not returned again.

## `POST /documents/{document_id}/questions`

Requires `X-Document-Token` and JSON `{ "question": "..." }`. Questions must be 5–500 characters by default. Returns `{ "answer": "...", "found": true|false, "sources": [...] }`. When the notice does not support an answer, `found` is false and `sources` is empty.

## `DELETE /documents/{document_id}`

Requires `X-Document-Token`. Deletes the workspace and returns `{ "deleted": true, "document_id": "..." }`.

Common upload errors include `INVALID_PDF`, `ENCRYPTED_PDF`, `UNSUPPORTED_SCANNED_PDF`, `TOO_MANY_PAGES`, `UPLOAD_TOO_LARGE`, and `AI_NOT_CONFIGURED`. A workspace expires after `DOCUMENT_TTL_HOURS` (12 by default).
