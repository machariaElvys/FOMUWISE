import json
import re

from app.errors import ApiError
from app.services.evidence import validate_answer
from app.services.prompts import question_prompt


def select_relevant_pages(question, page_texts, max_prompt_chars):
    words = set(re.findall(r"[\w]{3,}", question.lower(), flags=re.UNICODE))
    ranked = []
    for page_number, text in page_texts.items():
        page_words = set(re.findall(r"[\w]{3,}", text.lower(), flags=re.UNICODE))
        ranked.append((len(words & page_words), page_number, text))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected = []
    used = 0
    for _, page_number, text in ranked:
        remaining = max_prompt_chars - used
        if remaining <= 0:
            break
        excerpt = text[:remaining]
        if excerpt.strip():
            selected.append((page_number, excerpt))
            used += len(excerpt)
    selected.sort(key=lambda item: item[0])
    return {number: text for number, text in selected}


def answer_question(question, page_texts, gemma, max_prompt_chars):
    excerpts = select_relevant_pages(question, page_texts, max_prompt_chars)
    if not excerpts:
        return {
            "answer": "The notice does not provide enough information to answer that question.",
            "found": False,
            "sources": [],
        }
    try:
        raw = gemma.generate_json(question_prompt(question, excerpts))
        payload = json.loads(raw) if isinstance(raw, str) else raw
        return validate_answer(payload, excerpts)
    except ApiError:
        raise
    except Exception:
        raise ApiError(
            "AI_OUTPUT_INVALID",
            "FomuWise could not verify an answer from this notice. Please try again.",
            502,
        )
