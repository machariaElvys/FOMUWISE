import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///./fomuwise.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")
    DOCUMENT_TTL_HOURS = int(os.getenv("DOCUMENT_TTL_HOURS", "12"))
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
    MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "30"))
    MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "120000"))
    MAX_QUESTION_LENGTH = int(os.getenv("MAX_QUESTION_LENGTH", "500"))
    MAX_PROMPT_CHARS = int(os.getenv("MAX_PROMPT_CHARS", "24000"))
