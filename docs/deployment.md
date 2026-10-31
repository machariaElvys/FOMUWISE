# Deployment notes

The build guide targets DigitalOcean App Platform. This repository contains the application source and deployment outline, but has not been deployed to a cloud account.

## Services

- **Web service:** Python service rooted at `backend/`, start command `gunicorn --chdir backend wsgi:app` (`gunicorn` is included in backend requirements).
- **Static site:** build `frontend/` with `npm install && npm run build`; publish `frontend/dist`.
- **Database:** configure a managed PostgreSQL database and set `DATABASE_URL` using the provider's connection string. The `psycopg[binary]` SQLAlchemy driver is included in backend requirements.
- **Environment:** set `GEMINI_API_KEY`, `GEMMA_MODEL`, `FRONTEND_ORIGIN` to the deployed site origin, and `DATABASE_URL` in the backend environment. Never commit a real key or `.env` file.
- **CORS:** the API allows the configured frontend origin. Set `FRONTEND_ORIGIN` exactly to the deployed URL.

Before launch, install production server/database dependencies, run the tests and frontend build, configure TLS and backups for the database, confirm current Gemini API data terms, and validate the deployed origin and health endpoint. The default SQLite configuration is for local development and is not suitable for a multi-instance production service.
