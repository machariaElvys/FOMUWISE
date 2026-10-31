import unicodedata
from datetime import date


def normalize_text(value):
    return " ".join(unicodedata.normalize("NFKC", value or "").split())


def quote_is_on_page(quote, page_text):
    clean_quote = normalize_text(quote)
    return bool(clean_quote) and clean_quote in normalize_text(page_text)


def _valid_page(value, page_texts):
    return isinstance(value, int) and not isinstance(value, bool) and value in page_texts


def _verified_item(item, page_texts, text_key="text"):
    if not isinstance(item, dict):
        return None
    text = item.get(text_key)
    quote = item.get("evidence_quote")
    page_number = item.get("page_number")
    if not isinstance(text, str) or not text.strip():
        return None
    if not isinstance(quote, str) or not quote.strip():
        return None
    if not _valid_page(page_number, page_texts):
        return None
    if not quote_is_on_page(quote, page_texts[page_number]):
        return None
    return {
        text_key: text.strip(),
        "page_number": page_number,
        "evidence_quote": quote.strip(),
    }


def validate_analysis(payload, page_texts):
    keys = (
        "summary",
        "eligibility_requirements",
        "required_documents",
        "deadlines",
        "application_steps",
        "warnings",
    )
    if not isinstance(payload, dict) or any(key not in payload for key in keys):
        raise ValueError("Analysis response is missing required fields")

    summary = _verified_item(payload["summary"], page_texts)
    if summary is None:
        raise ValueError("Analysis summary has no verifiable source")
    result = {"summary": summary}
    for key in keys[1:]:
        values = payload[key]
        if not isinstance(values, list):
            raise ValueError("Analysis field must be a list")
        result[key] = []
        for item in values:
            text_key = "date_text" if key == "deadlines" else "text"
            verified = _verified_item(item, page_texts, text_key)
            if verified is None:
                continue
            if key == "deadlines":
                normalized = item.get("normalized_date")
                if normalized is not None:
                    try:
                        date.fromisoformat(normalized)
                    except (TypeError, ValueError):
                        normalized = None
                verified["normalized_date"] = normalized
            result[key].append(verified)
    return result


def validate_answer(payload, page_texts):
    if not isinstance(payload, dict):
        raise ValueError("Question response must be an object")
    answer = payload.get("answer")
    found = payload.get("found")
    sources = payload.get("sources")
    if not isinstance(answer, str) or not isinstance(found, bool) or not isinstance(sources, list):
        raise ValueError("Question response is missing required fields")
    verified_sources = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        verified = _verified_item(
            {
                "text": "Source",
                "page_number": source.get("page_number"),
                "evidence_quote": source.get("evidence_quote"),
            },
            page_texts,
        )
        if verified:
            verified_sources.append({
                "page_number": verified["page_number"],
                "evidence_quote": verified["evidence_quote"],
            })
    if not found or not verified_sources:
        return {
            "answer": "The notice does not provide enough information to answer that question.",
            "found": False,
            "sources": [],
        }
    return {"answer": answer.strip(), "found": True, "sources": verified_sources}
