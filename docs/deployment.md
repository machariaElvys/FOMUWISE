# Deployment notes

The build guide targets DigitalOcean App Platform. This repository contains the application source and deployment outline, but has not been deployed to a cloud account.

## Services

- **Web service:** Python service rooted at `backend/`, start command `gunicorn --chdir backend wsgi:app` (`gunicorn` is included in backend requirements).
- **Static site:** build `frontend/` with `npm install && npm run build`; publish `frontend/dist`.
- **Database:** configure a managed PostgreSQL database and set `DATABASE_URL` using the provider's connection string. The `psycopg[binary]` SQLAlchemy driver is included in backend requirements.
- **Environment:** set `GEMINI_API_KEY`, `GEMMA_MODEL`, `FRONTEND_ORIGIN` to the deployed site origin, and `DATABASE_URL` in the backend environment. Never commit a real key or `.env` file.
- **CORS:** the API allows the configured frontend origin. Set `FRONTEND_ORIGIN` exactly to the deployed URL.

Before launch, install production server/database dependencies, run the tests and frontend build, configure TLS and backups for the database, confirm current Gemini API data terms, and validate the deployed origin and health endpoint. The default SQLite configuration is for local development and is not suitable for a multi-instance production service.

## Frontend routing and loading

The frontend defaults to the same-origin `/api/v1` URL. In production, route `/api/*` to the Flask service before the SPA fallback. For a separately hosted API, set `VITE_API_BASE_URL=https://your-api-host/api/v1` **when building** the static site and configure `FRONTEND_ORIGIN` on Flask. Vite's development proxy is not part of the static production build.

Local development uses Vite's `/api` proxy to Flask on port 5000; no frontend `.env` is required. Remove any old `VITE_API_BASE_URL=http://localhost:5000/api/v1` override when using a remote preview.

The UI uses local system fonts rather than a blocking external font stylesheet. Saved workspaces restore in the background with an 8-second timeout and a retry option. Temporary network/server failures preserve session credentials; invalid or expired workspaces clear them. Other API operations have a 120-second client timeout to allow AI processing. A client timeout does not cancel server-side analysis.

Serve versioned `/assets/*` files with compression and long-lived immutable caching; keep `index.html` revalidated so new deployments load correctly. Measure cold-start delays against the deployed host before changing hosting capacity.
