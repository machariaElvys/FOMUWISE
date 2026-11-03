import json
from time import perf_counter

from app.errors import ApiError
from app.services.evidence import validate_analysis
from app.services.prompts import analysis_prompt


def analyze_pages(pages, gemma, metrics=None):
    page_texts = {index: text for index, text in enumerate(pages, start=1)}
    try:
        if hasattr(gemma, "set_metrics"):
            gemma.set_metrics(metrics)
        prompt_started = perf_counter()
        try:
            prompt = analysis_prompt(page_texts)
        finally:
            if metrics is not None:
                metrics["prompt_construction_seconds"] = round(
                    metrics.get("prompt_construction_seconds", 0.0)
                    + perf_counter()
                    - prompt_started,
                    3,
                )
        if metrics is not None:
            metrics["initial_prompt_characters"] = len(prompt)
        raw = gemma.generate_json(prompt)
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
