# ADR-0012: SQLite configured but unused

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
The app stores nothing between requests ([ADR-0001](0001-pre-trip-planner-not-live-tracking.md)):
- routes, checkpoints, weather, and risk are calculated per request and returned;
- the cache is in memory ([ADR-0013](0013-in-process-cache-and-gunicorn-threads.md));
- there are no users, logins, or sessions ([SCOPE.md](../SCOPE.md));
- logs go to standard output.

Even so, Django expects a database configuration, and its test tools (`TestCase`, DRF's `APITestCase`) expect a database to exist.

## Decision
- Configure **SQLite** as the default database, and define **no application models**.
- Keep only the Django apps that are needed. `admin`, `auth`, and `sessions` are left out, so no tables or migrations exist for them.
- Turn off DRF's default authentication classes, which depend on `django.contrib.auth`.

## Alternatives considered
| Option | Why rejected |
|---|---|
| Render free PostgreSQL | Free databases **expire 30 days after creation**, so the hosted app would break after that. It is also an extra service to configure, for data that does not exist. |
| No database (`DATABASES = {}`) | Unusual for Django. Database-backed test cases fail, and readers would be surprised. |

## Consequences
- No database setup locally, in Docker, or on Render.
- Render's free disk is wiped on every redeploy or restart. This is harmless because nothing is stored.
- Saving trips later only needs models plus a switch to PostgreSQL in `DATABASES`.
