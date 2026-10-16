# ADR-0014: Structured logging with structlog, request IDs, and named events

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
Logs should be machine-readable, so dashboards and alerts can be built on them later.
It must be possible to trace everything that happened during one request, across our own code and third-party calls.

## Decision
- Use **structlog**, wired into Django's standard `logging`, so log lines from Django, Gunicorn, and our code share one format.
  - **JSON output** in Docker and on Render.
  - **Readable coloured output** in local development, chosen by an environment variable.
- **Request-ID middleware:**
  - takes the incoming `X-Request-ID` header if it is a valid UUID, otherwise creates a new `uuid4`;
  - attaches it to structlog's context variables, so **every log line during that request includes `request_id`**;
  - returns it in the `X-Request-ID` response header;
  - clears the context when the request ends.
- **Named events.** Business and integration events use an **`EventName` enum** rather than free-text messages. Examples:

  | Event | Key fields |
  |---|---|
  | `request.completed` | method, path, status, duration_ms |
  | `geocode.requested` | query_length, cache_hit |
  | `plan.requested` | spacing, load_lb, rest_breaks |
  | `plan.completed` | route_count, recommended_route, checkpoint_count, duration_ms |
  | `plan.no_safe_route` | route_count |
  | `routes.fallback_used` | routes_before, routes_after |
  | `provider.called` | provider, endpoint, status, duration_ms |
  | `provider.failed` | provider, endpoint, error_type |
  | `provider.quota_exceeded` | provider |
  | `weather.requested` | location_count, cached, fetched, hours |

- No secrets (API keys) or full addresses are logged.

## Alternatives considered
- **Plain `logging` with text messages.** Rejected. The output is hard to parse into dashboards.
- **The `django-structlog` package.** Rejected. A small middleware written by us covers the request-ID requirement and is easier to explain.

## Consequences
- Every request can be traced end to end by `request_id`.
- Event names are consistent and easy to search, ready for log-based dashboards.
- The frontend can show the `X-Request-ID` in error messages to help debugging.
