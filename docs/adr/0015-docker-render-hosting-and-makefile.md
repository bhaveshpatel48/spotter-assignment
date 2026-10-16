# ADR-0015: Docker, Render hosting, and a Makefile

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
The app must be hosted for free, with no credit card.
It should run the same way locally and in production, and reviewers should be able to start it with one command.

## Decision
**Hosting on Render**, described in one `render.yaml` blueprint in the repository:

| Part | Render service | Why |
|---|---|---|
| Backend | **Web service built from `backend/Dockerfile`** | Render supports Docker natively, and the free plan needs no card. |
| Frontend | **Static site** (`npm run build` → `dist/`) | Served from a CDN and **never sleeps**, unlike free web services. |

**Docker:**
- `backend/Dockerfile`:
  - Python 3.14 slim base, dependencies installed with **uv**;
  - runs as a non-root user;
  - starts Gunicorn as described in [ADR-0013](0013-in-process-cache-and-gunicorn-threads.md).
- `frontend/Dockerfile`:
  - a multi-stage build: Node builds the app, nginx serves it;
  - used for local Docker runs only.
- `docker-compose.yml` runs both containers locally.

**Configuration:**
- Environment variables only: `TOMTOM_API_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DEBUG`, `LOG_FORMAT`, `VITE_API_BASE_URL`, `VITE_TOMTOM_MAP_KEY`.
- An `.env.example` file is committed. The real `.env` is not.

**Makefile:**
```make
make install   # backend deps (uv) + frontend deps (npm)
make dev       # run backend + frontend locally without Docker
make up        # build and run everything with docker compose
make down      # stop docker compose
make test      # backend + frontend tests
make lint      # ruff + oxlint + tsc
```

## Alternatives considered
| Option | Why rejected |
|---|---|
| Vercel | Python runs only as short serverless functions with a ~10 s timeout on the free plan, and it cannot run our Docker backend. |
| Vercel (frontend) + Render (backend) | A second platform with no real gain, since Render's static sites are also served from a CDN. |
| Frontend as a Docker web service on Render | It would sleep after 15 minutes like the backend, adding a second cold start. |
| Fly.io / Railway | Neither has a no-card free tier any more. |

## Consequences
- One command starts the app locally, with or without Docker.
- **The free backend sleeps after 15 minutes idle, and the first request then takes about 1 minute.** This is mitigated as follows:
  - the frontend shows a "Waking up the server…" state;
  - the README explains the delay;
  - the app is opened once before recording the Loom video.
- The frontend Docker image is not used on Render. It exists for local Docker parity.
