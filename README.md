# FomuWise

FomuWise turns a bursary or scholarship notice into a clear application guide. Upload a text-based PDF to get a sourced summary, eligibility requirements, document checklist, deadlines, application steps, and answers grounded in that notice.

## What is included

- React and Vite single-page application with responsive FomuWise branding.
- Flask JSON API with PyMuPDF text extraction, SQLAlchemy temporary storage, and Gemini API access to Gemma 4.
- Evidence checks that keep generated statements only when the cited quote appears on the cited page.
- Token-protected document workspaces with a 12-hour expiry and explicit deletion.
- API and service tests, environment examples, and DigitalOcean deployment notes.

## Requirements

- Python 3.10 or newer.
- Node.js 20.19+ or 22.12+ and npm (required by Vite 8).
- A Google AI Studio / Gemini API key with access to the configured Gemma model.

## Run locally

Open two WSL terminal tabs in the FomuWise folder.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit backend/.env and set GEMINI_API_KEY to your own key.
python run.py
```

The API runs at `http://localhost:5000`; `GET /api/v1/health` checks readiness.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`.

## Update the existing WSL FOMUWISE folder from the ZIP

Copy `FomuWise_MVP.zip` into Windows Downloads, then in your WSL terminal run:

```bash
cd ~/projects/FOMUWISE
unzip -o /mnt/c/Users/User/Downloads/FomuWise_MVP.zip -d .
bash scripts/archive-old-vite-scaffold.sh
code .
```

The archive overlays the project files. The helper moves the old `vite@latest` scaffold and its orphan root `package-lock.json` to a timestamped sibling backup, keeping their contents available. It does not remove the repository's existing `.git` history or user files. Review the backup and `git status` after extraction.

If `unzip` is missing, install it with `sudo apt update && sudo apt install unzip`.

## Privacy and model behavior

FomuWise accepts text-based PDFs up to 10 MB and 30 pages by default. The original upload is held in a temporary file only while its text is extracted; the temporary file is removed immediately afterward. Extracted page text and the generated guide are held in a local SQL database for up to 12 hours so the workspace can be reopened in the same browser session. A random access token protects each workspace; only its SHA-256 hash is stored. Users can delete the workspace sooner.

For analysis and questions, extracted text is sent to Google's Gemini API with Gemma 4. FomuWise does not currently support scanned PDFs/OCR, user accounts, web search, or permanent document storage. Review Google's current API terms and avoid uploading notices containing information you are not permitted to share. Model/API references are in [docs/model-notices.md](docs/model-notices.md).

## Checks

Backend tests:

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m pytest
```

Frontend production build:

```bash
cd frontend
npm install
npm run build
```

## Configuration

Copy `backend/.env.example` to `backend/.env`. Supported settings include `GEMINI_API_KEY`, `GEMMA_MODEL`, `DATABASE_URL`, `FRONTEND_ORIGIN`, `DOCUMENT_TTL_HOURS`, `MAX_UPLOAD_MB`, and `MAX_PDF_PAGES`. See [docs/api-contract.md](docs/api-contract.md) and [docs/deployment.md](docs/deployment.md).
