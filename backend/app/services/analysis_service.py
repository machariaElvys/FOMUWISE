import json

from app.errors import ApiError
from app.services.evidence import validate_analysis
from app.services.prompts import analysis_prompt


def analyze_pages(pages, gemma):
    page_texts = {index: text for index, text in enumerate(pages, start=1)}
    try:
        raw = gemma.generate_json(analysis_prompt(page_texts))
        payload = json.loads(raw) if isinstance(raw, str) else raw
        return validate_analysis(payload, page_texts)
    except ApiError:
        raise
    except Exception:
        raise ApiError(
            "AI_OUTPUT_INVALID",
            "FomuWise could not verify the analysis from this notice. Please try again.",
            502,
        )
