# ADR-0010: Django REST Framework API with a separate React frontend

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
The brief requires React and Django.
The backend does the routing, weather, and risk work. The frontend shows the form, map, heatmap, and route summaries.
The two need a clear contract between them, and should be possible to build, test, and deploy independently.

## Decision
- **Backend:** Django 6.1 on Python 3.14, with **Django REST Framework (DRF)** exposing a JSON REST API under `/api/`.
- **Frontend:** a standalone **React 19.2 + TypeScript** app built with **Vite**. It talks to the backend only through the REST API.
- The two apps live in separate top-level folders in one repository: `backend/` and `frontend/`.
- The API base URL is passed to the frontend at build time (`VITE_API_BASE_URL`).
- The backend allows cross-origin requests only from the frontend's origin, using `django-cors-headers`.

## Alternatives considered
| Option | Why rejected |
|---|---|
| Django Ninja | Uses pydantic natively and is lighter, but DRF is the more established, production-proven standard. |
| Django templates with React islands | Couples the frontend build to Django, and makes the map-heavy UI harder to structure. |
| Serving the React build from Django (one service) | Avoids CORS, but means a slower deploy and the frontend would sleep with the backend on Render's free tier. See [ADR-0015](0015-docker-render-hosting-and-makefile.md). |
| Next.js | Server-side rendering adds nothing to a single-page map tool. |

## Consequences
- The frontend and backend can be developed, tested, and deployed separately.
- The API contract is defined in [ARCHITECTURE.md](../ARCHITECTURE.md).
- CORS must be configured correctly for each environment (local and Render).
