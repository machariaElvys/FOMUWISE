from app.services.evidence import quote_is_on_page, validate_analysis, validate_answer


def test_quote_verification_normalizes_whitespace():
    assert quote_is_on_page(
        "Submit the form by 30 November 2026.",
        "Submit  the form\nby 30 November 2026.",
    )


def test_analysis_removes_unverified_items():
    pages = {1: "Submit the form by 30 November 2026."}
    source = {
        "summary": {
            "text": "Submit the form by November 30.",
            "page_number": 1,
            "evidence_quote": "Submit the form by 30 November 2026.",
        },
        "eligibility_requirements": [
            {
                "text": "Must be a resident.",
                "page_number": 1,
                "evidence_quote": "Must be a resident.",
            }
        ],
        "required_documents": [],
        "deadlines": [
            {
                "date_text": "30 November 2026",
                "normalized_date": "2026-11-30",
                "page_number": 2,
                "evidence_quote": "30 November 2026",
            }
        ],
        "application_steps": [],
        "warnings": [],
    }
    result = validate_analysis(source, pages)
    assert result["summary"]["page_number"] == 1
    assert result["eligibility_requirements"] == []
    assert result["deadlines"] == []


def test_question_answer_fails_closed_without_verified_source():
    result = validate_answer(
        {
            "answer": "Applicants are eligible.",
            "found": True,
            "sources": [{"page_number": 1, "evidence_quote": "Invented quote"}],
        },
        {1: "The notice asks for a form."},
    )
    assert result["found"] is False
    assert result["sources"] == []
    assert "not provide enough information" in result["answer"]
