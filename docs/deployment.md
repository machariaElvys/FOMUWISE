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

## Render: prevent AI requests from killing workers

For a Render Python web service with **Root Directory `backend`**:

- Build: `pip install -r requirements.txt`
- Start: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --timeout 120 --access-logfile - --error-logfile - --log-level info`
- Health check path: `/api/v1/health` (the API root `/` intentionally returns 404).
- Environment: `GEMINI_API_KEY`, `FRONTEND_ORIGIN=https://fomuwise.pages.dev`, and optionally `AI_TIMEOUT_MS=40000`.

If Root Directory is blank instead, prefix the start command with `gunicorn --chdir backend` in place of `gunicorn` and use `pip install -r backend/requirements.txt` for the build.

The Google SDK now has an explicit 40-second timeout per call and one attempt (no automatic retries). There can be at most two calls: initial generation and one JSON repair. `AI_TIMEOUT_MS` accepts 1000–45000 milliseconds, leaving room under the 120-second worker and frontend timeouts for two calls plus local processing. This is an SDK request timeout, not a hard wall-clock deadline for the entire upload. Do not increase it beyond the supported range. A longer Gunicorn timeout does not make the provider faster.

Timeouts return `AI_TIMEOUT` (504); rejected requests (400/401/403/404) return `AI_CONFIGURATION_ERROR`; quota failures return `AI_RATE_LIMITED`. A repair-call provider error retains its classification. Safe INFO timing logs include model, duration, HTTP status, exception class and the configured timeout; they do not include keys, prompts, document text or raw provider exception messages. Check `fomuwise_ai_request` and `fomuwise_analysis` in Render logs after redeployment. The health endpoint does not validate model/key access.

No model is automatically switched. To compare models, set `GEMMA_MODEL` to an exact model identifier available to your Google API key, redeploy, and upload the same non-sensitive PDF. Compare latency, JSON repair frequency and citation quality. Use persistent PostgreSQL storage for production; a default SQLite database on an ephemeral service is not durable.
