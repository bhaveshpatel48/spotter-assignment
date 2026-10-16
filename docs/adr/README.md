# Architecture Decision Records

Each record describes one significant decision: its context, the decision itself, the alternatives considered, and the consequences.
Records are numbered and never rewritten. When a decision is replaced, its status changes to `Superseded by ADR-XXXX` and a new record is added.

For what the application does and does not do, see [SCOPE.md](../SCOPE.md).

| ADR | Title | Status |
|---|---|---|
| [0001](0001-pre-trip-planner-not-live-tracking.md) | Pre-trip planner, not live tracking | Accepted |
| [0002](0002-tomtom-for-routing-geocoding-and-map.md) | TomTom for routing, geocoding, and the base map | Accepted |
| [0003](0003-open-meteo-for-weather.md) | Open-Meteo for hourly weather forecasts | Accepted |
| [0004](0004-backend-proxies-third-party-apis.md) | Backend proxies all third-party data APIs, with caching | Accepted |
| [0005](0005-three-route-strategy.md) | Strategy for getting three route options | Accepted |
| [0006](0006-checkpoint-eta-and-forecast-matching.md) | Checkpoint ETAs and matching them to forecast hours | Accepted |
| [0007](0007-risk-classification-and-ranking.md) | Risk classification and route ranking | Accepted |
| [0008](0008-optional-driver-rest-breaks.md) | Driver rest breaks as an opt-in toggle | Accepted |
| [0009](0009-maplibre-heatmap-with-preloaded-48h-data.md) | GPU weather layer with 48 hours of data preloaded | Accepted |
| [0010](0010-drf-rest-api-with-separate-react-frontend.md) | Django REST Framework API with a separate React frontend | Accepted |
| [0011](0011-drf-serializers-and-enums.md) | DRF serializers at the API boundary, pydantic models internally, enums for fixed values | Accepted |
| [0012](0012-sqlite-configured-but-unused.md) | SQLite configured but unused | Accepted |
| [0013](0013-in-process-cache-and-gunicorn-threads.md) | In-process cache, one Gunicorn worker with four threads | Accepted |
| [0014](0014-structlog-and-request-id.md) | Structured logging with structlog, request IDs, and named events | Accepted |
| [0015](0015-docker-render-hosting-and-makefile.md) | Docker, Render hosting, and a Makefile | Accepted |

## Template

```markdown
# ADR-XXXX: Title

- **Status:** Proposed | Accepted | Superseded by ADR-YYYY
- **Date:** YYYY-MM-DD

## Context
What problem or constraint forces a decision?

## Decision
What we will do.

## Alternatives considered
What else was evaluated, and why it was rejected.

## Consequences
What becomes easier or harder, and what risks we accept.
```
