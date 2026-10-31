import fitz
import pytest

from app import create_app, db


class FakeGemmaService:
    def generate_json(self, prompt):
        if "QUESTION:" in prompt:
            if "what documents" in prompt.lower():
                return {
                    "answer": "Attach a copy of the parent/guardian ID.",
                    "found": True,
                    "sources": [
                        {
                            "page_number": 1,
                            "evidence_quote": "Attach a copy of the parent/guardian ID.",
                        }
                    ],
                }
            return {
                "answer": "The notice does not provide enough information to answer that question.",
                "found": False,
                "sources": [],
            }
        return {
            "summary": {
                "text": "The notice explains a bursary application.",
                "page_number": 1,
                "evidence_quote": "Apply for the county bursary.",
            },
            "eligibility_requirements": [
                {
                    "text": "Applicants must be county residents.",
                    "page_number": 1,
                    "evidence_quote": "Applicants must be county residents.",
                }
            ],
            "required_documents": [
                {
                    "text": "Parent or guardian ID copy.",
                    "page_number": 1,
                    "evidence_quote": "Attach a copy of the parent/guardian ID.",
                }
            ],
            "deadlines": [
                {
                    "date_text": "by 30 November 2026",
                    "normalized_date": "2026-11-30",
                    "page_number": 1,
                    "evidence_quote": "Submit the form by 30 November 2026.",
                }
            ],
            "application_steps": [
                {
                    "text": "Submit the completed form to the ward office.",
                    "page_number": 1,
                    "evidence_quote": "Submit the completed form to the ward office.",
                }
            ],
            "warnings": [],
        }


@pytest.fixture()
def app(tmp_path):
    database_path = tmp_path / "fomuwise-test.db"
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///{}".format(database_path.as_posix()),
            "GEMINI_API_KEY": "",
            "GEMMA_SERVICE": FakeGemmaService(),
            "MAX_UPLOAD_MB": 10,
            "MAX_PDF_PAGES": 30,
            "DOCUMENT_TTL_HOURS": 12,
            "MAX_QUESTION_LENGTH": 500,
            "MAX_PROMPT_CHARS": 24000,
            "FRONTEND_ORIGIN": "http://localhost:5173",
        }
    )
    with application.app_context():
        db.drop_all()
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def sample_pdf():
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Apply for the county bursary. Applicants must be county residents. "
        "Attach a copy of the parent/guardian ID. Submit the form by 30 November 2026. "
        "Submit the completed form to the ward office.",
    )
    data = document.tobytes()
    document.close()
    return data
