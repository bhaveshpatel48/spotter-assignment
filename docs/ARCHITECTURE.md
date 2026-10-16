# Architecture — Weather-Aware Truck Routing

This document covers **how** the app is built:
- the system's parts and how they connect;
- the API contract between frontend and backend;
- the code layout;
- the build order.

Two other documents cover the rest:
- what the app does and doesn't do: [SCOPE.md](SCOPE.md);
- why each choice was made: [ADRs](adr/README.md).

---

## 1. System overview

```
┌──────────────────────────── Browser ────────────────────────────┐
│  React 19 + TypeScript (Vite)                                   │
│  TomTom Maps SDK (MapLibre GL) — monoLight base map             │
└───────────┬───────────────────────────────────┬─────────────────┘
            │ REST/JSON  (/api/*)               │ map tiles (direct, domain-restricted key)
            ▼                                   ▼
┌──────────────── Django 6.1 + DRF ───────────────┐      ┌──────────────┐
│ RequestID middleware → structlog (JSON)         │      │ TomTom tiles │
│ api/        serializers + views                 │      └──────────────┘
│ trip_planning/ pure logic (risk, ETA, ranking)  │
│ providers/  TomTom + Open-Meteo clients         │──► TomTom Search + Routing
│ LocMemCache (in-process)   SQLite (unused)      │──► Open-Meteo forecast (bulk)
└─────────────────────────────────────────────────┘
  Gunicorn: 1 worker × 4 threads (Render web service, Docker)
```

| Part | Technology | Hosting |
|---|---|---|
| Frontend | React 19.2, TypeScript, Vite, TomTom Maps SDK for JS | Render static site |
| Backend | Python 3.14, Django 6.1, DRF, pydantic, structlog, httpx, Gunicorn | Render web service (Docker) |
| Data providers | TomTom (search, routing, tiles), Open-Meteo (weather) | External |

---

## 2. Request flow — "Find routes"

1. The user picks an origin and a destination.
   - Autocomplete calls `GET /api/geocode`, waiting 300 ms after typing stops and requiring at least 3 characters.
   - Results are cached in Django.
2. The user sets the departure time, load weight, and checkpoint spacing, then submits. This sends `POST /api/plan`.
3. Django validates the request with a serializer, then `trip_planning.service.plan_trip()` runs:
   1. **Routes.** One TomTom truck route request with `maxAlternatives=5`. Keep the main route plus the 2 most different alternatives. If fewer than 3 routes remain, make one extra request with `avoidAreas` ([ADR-0005](adr/0005-three-route-strategy.md)).
   2. **Checkpoints.** Place a checkpoint every N miles along each route, plus one at the destination. Estimate each checkpoint's ETA from TomTom's `progress[]` data, adding rest breaks if that option is on ([ADR-0006](adr/0006-checkpoint-eta-and-forecast-matching.md), [ADR-0008](adr/0008-optional-driver-rest-breaks.md)).
   3. **Weather locations.** Every checkpoint gets its own location, rounded to 0.1° (about 7 miles). The heatmap grid around the routes uses the rest of the 550-location budget (section 6).
   4. **Weather.** Make **one bulk Open-Meteo request** for all locations, covering `now` to `max(now + 48 h, latest ETA)`, and cache the result.
   5. **Risk.** Classify each checkpoint at its ETA hour, and each grid point for every hour from 0 to 47. The rules are in [ADR-0007](adr/0007-risk-classification-and-ranking.md).
   6. **Ranking.** Add up the miles at each risk level per route, rank the routes, and mark the recommended one.
4. The serializer builds the response.
5. React draws the routes, checkpoints, summaries, and heatmap.
   - The slider only changes which hour the heatmap displays. It makes no network request ([ADR-0009](adr/0009-maplibre-heatmap-with-preloaded-48h-data.md)).

---

## 3. API contract

All responses are JSON, and every response carries an `X-Request-ID` header.

### `GET /api/health`
`200 {"status": "ok"}`. Render uses this as its health check.

### `GET /api/geocode?q=denv`
`q` must be at least 3 characters. Results are limited to US places.
```json
{ "results": [ { "label": "Denver, CO", "lat": 39.7392, "lon": -104.9903 } ] }
```

### `POST /api/plan`
Request:
```json
{
  "origin":      { "label": "Denver, CO",         "lat": 39.7392, "lon": -104.9903 },
  "destination": { "label": "Salt Lake City, UT", "lat": 40.7608, "lon": -111.8910 },
  "departure_time": "2026-10-17T08:00:00-05:00",
  "load_weight_lb": 42000,
  "checkpoint_spacing_miles": 25,
  "include_rest_breaks": false
}
```

Validation rules:
- Both points must be inside the contiguous US.
- `load_weight_lb` must be between 1 and 80,000.
- `departure_time` must be no earlier than now and no more than 14 days ahead.
- `checkpoint_spacing_miles` must be 10, 25, or 50.

Response (shortened):
```json
{
  "generated_at": "2026-10-16T14:02:11Z",
  "recommended_route_id": "route-1",
  "warnings": [ { "code": "FEWER_ROUTES", "message": "Only 2 practical route(s) exist for this trip." } ],
  "routes": [
    {
      "id": "route-1",
      "rank": 1,
      "is_recommended": true,
      "summary": {
        "distance_miles": 967.4,
        "travel_time_seconds": 52200,
        "departure_time": "2026-10-17T13:00:00Z",
        "arrival_time": "2026-10-18T03:30:00Z",
        "miles_by_risk": { "LOW": 820.0, "MODERATE": 97.4, "HIGH": 50.0, "SEVERE": 0.0, "NO_TRAVEL": 0.0 },
        "average_risk": 0.22
      },
      "geometry": [[-96.797, 32.7767], [-96.79, 32.79]],
      "checkpoints": [
        {
          "index": 3,
          "mile": 75.0,
          "lat": 33.65,
          "lon": -96.6,
          "eta": "2026-10-17T14:10:00Z",
          "weather": { "wind_mph": 38.0, "gust_mph": 51.0, "rain_in_hr": 0.04, "snow_in_hr": 0.0 },
          "risk_level": "SEVERE",
          "risk_reasons": ["Wind 38 mph (High)", "Load 42,000 lb with wind 38 mph (Severe)"]
        }
      ]
    }
  ],
  "heatmap": {
    "start_time": "2026-10-16T14:00:00Z",
    "hours": 48,
    "cell_size_deg": 0.2,
    "points": [ { "lat": 40.8, "lon": -105.0, "risk": [0, 0, 1, 2, "… 48 values"] } ]
  }
}
```

Format rules:
- Routes are ordered by rank.
- `geometry` uses GeoJSON order, `[lon, lat]`.
- All times are UTC. The frontend converts them to local time for display.
- Risk levels are enum names (`LOW` … `NO_TRAVEL`).
- `heatmap.points[].risk[h]` is the risk level as a number from 0 to 4 at hour `start_time + h`, including the load rules.
- `heatmap.cell_size_deg` is the spacing between neighbouring heatmap points (0.2° or coarser on long trips). The frontend uses it to size each heatmap point so neighbours blend into one band.
- `warnings[].code` is `FEWER_ROUTES` (fewer than 3 distinct routes exist) or `NO_SAFE_ROUTE` (every route has No Travel miles).

### Errors
Every error has the same shape:
```json
{ "error": { "code": "PROVIDER_QUOTA_EXCEEDED", "message": "Routing quota exhausted for today.", "request_id": "…" } }
```

| Status | `code` | When |
|---|---|---|
| 400 | `VALIDATION_ERROR` | The serializer rejects the input. A `fields` object holds the details for each field. |
| 400 | `TRIP_OUTSIDE_FORECAST_RANGE` | The trip would end beyond the 16-day forecast. |
| 404 | `NO_ROUTE_FOUND` | TomTom finds no truck route between the two points. |
| 502 | `PROVIDER_ERROR` | TomTom or Open-Meteo fails, after one retry on connection errors and 5xx responses. |
| 503 | `PROVIDER_QUOTA_EXCEEDED` | TomTom returns `403` (over quota) or Open-Meteo returns `429` (rate limited). |
| 503 | `PROVIDER_NOT_CONFIGURED` | The TomTom API key is missing on the server. |
| 504 | `PROVIDER_TIMEOUT` | TomTom doesn't respond within 10 s, or Open-Meteo within 30 s. |

---

## 4. Backend structure

```
backend/
├── config/                 settings.py, urls.py, wsgi.py
├── core/
│   ├── logging.py          structlog configuration (JSON or console, chosen by LOG_FORMAT)
│   ├── middleware.py       RequestIDMiddleware
│   ├── events.py           EventName enum
│   ├── errors.py           application errors (plain Python, raised by any layer)
│   └── exception_handler.py  DRF exception handler → error shape above
├── providers/
│   ├── http.py             shared httpx client (timeouts, one retry on connection errors/5xx, provider.called events)
│   ├── tomtom.py           geocode(), calculate_routes()   (+ pydantic response models)
│   └── open_meteo.py       get_hourly_forecasts(points, start, end)   (+ pydantic response models)
├── trip_planning/          pure logic: no Django, no HTTP
│   ├── enums.py            RiskLevel, CheckpointSpacing
│   ├── models.py           frozen pydantic models: Route, PointForecast, Checkpoint, RouteSummary, TripPlan, …
│   ├── geo.py              haversine, cumulative distance, interpolation, resampling, grid snapping
│   ├── route_selection.py  pick 3 most distinct routes, midpoint avoid-area
│   ├── checkpoints.py      place checkpoints every N miles, estimate ETAs
│   ├── rest_breaks.py      optional rest-break time shifts
│   ├── risk.py             thresholds, load rules, worst-of combination
│   ├── ranking.py          miles by level, average risk, ordering
│   ├── weather.py          match forecast hours to ETAs
│   ├── heatmap.py          corridor grid + 48-hour risk values
│   └── service.py          plan_trip(): runs the whole pipeline
├── api/                    the only Django app
│   ├── serializers.py      PlanRequest/PlanResponse, GeocodeResponse
│   ├── views.py            HealthView, GeocodeView, PlanView
│   └── urls.py
├── tests/                  pytest + pytest-django; saved provider JSON in tests/fixtures/
├── Dockerfile
└── pyproject.toml          managed with uv
```

Layering rules:
- **`trip_planning/` never imports Django or `providers/`.** `service.py` receives the provider functions as arguments, so tests can pass in fakes.
- **Only `api/` knows about HTTP and DRF.**
- **Only `providers/` knows the TomTom and Open-Meteo JSON formats.**

---

## 5. Frontend structure

```
frontend/src/
├── api/            client.ts (fetch wrapper, error mapping), types.ts (mirrors the API contract)
├── hooks/          useDebouncedValue.ts, usePlaceSearch.ts, usePlanTrip.ts
├── lib/            risk.ts (colours, labels), format.ts (miles, durations, local times)
├── components/
│   ├── SearchForm.tsx        inputs + submit
│   ├── PlaceAutocomplete.tsx reusable for origin and destination
│   ├── RouteList.tsx  / RouteCard.tsx   summaries; click to select a route
│   ├── RiskBadge.tsx         colour + text label (accessible)
│   ├── ForecastSlider.tsx    0–47 h, at most one update per animation frame
│   ├── StatusBanner.tsx      loading / "waking up server" / errors with request ID
│   └── map/
│       ├── MapView.tsx           creates the TomTom map (monoLight)
│       ├── RoutesLayer.tsx       3 route lines, recommended one highlighted
│       ├── CheckpointsLayer.tsx  circles coloured by risk, with popups
│       └── HeatmapLayer.tsx      MapLibre heatmap; reads the hour h value from each point's risk list
└── App.tsx         holds the state: plan result, selected route, slider hour
```

State lives in `useState` in `App`, passed down as props. There is no store library.

Map layers, bottom to top:
1. base map;
2. heatmap;
3. route lines;
4. checkpoints.

---

## 6. Key algorithms (summary)

| Topic | Approach |
|---|---|
| Checkpoint placement | Walk the route, adding up haversine distance. When the running total crosses k × N miles, interpolate a point between the two route points either side. Add a final checkpoint at the destination. |
| ETA | Estimate travel time in proportion to distance between the nearest `progress` entries before and after the checkpoint. ETA = departure + travel time + rest time. |
| Forecast hour | Rain and snow use the hour that contains the ETA. Wind uses the nearest hour. |
| Risk | Worst of the wind, rain, and snow levels, then the load rules can raise it. Boundary rules are in [ADR-0007](adr/0007-risk-classification-and-ranking.md). |
| Distinct routes | Sample a point every 0.5 miles on each alternative. An alternative's distinctness is the share of its sample points more than about 1 km from every route already chosen. Keep the best 2 above 10%. |
| Checkpoint weather | Each checkpoint's location is rounded to 0.1° (about 7 miles), so checkpoints keep their own forecast. Only if a very long trip with 10-mile spacing would exceed 400 locations does the rounding get coarser, just enough to fit. |
| Heatmap grid | Covers each route cell and its 8 neighbours. It starts at 0.2° and gets 0.1° coarser until it fits the locations left after checkpoints (at least 150). |
| Weather volume | At most **550 locations** per uncached plan, under Open-Meteo's 600 calls/minute. A second *new* search within the same minute can be refused (`429`); the API then returns `PROVIDER_QUOTA_EXCEEDED` with "try again in a minute". Repeated or overlapping searches come from the 30-minute cache. |

---

## 7. Configuration

| Variable | Used by | Example |
|---|---|---|
| `TOMTOM_API_KEY` | backend | (secret) |
| `DJANGO_SECRET_KEY` | backend | (secret) |
| `DEBUG` | backend | `false` |
| `ALLOWED_HOSTS` | backend | `api-truck-routing.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | backend | `https://truck-routing.onrender.com` |
| `LOG_FORMAT` | backend | `json` or `console` |
| `VITE_API_BASE_URL` | frontend (build time) | `https://api-truck-routing.onrender.com` |
| `VITE_TOMTOM_MAP_KEY` | frontend (build time) | key restricted to the frontend domain |

`.env.example` lists every variable. The real `.env` is in `.gitignore`.

---

## 8. Testing

| Layer | What is tested | How |
|---|---|---|
| `trip_planning/risk.py`, `ranking.py` | Every threshold boundary, every load rule, all ranking tie-breaks, the No Travel warning | Table-driven pytest |
| `trip_planning/checkpoints.py`, `rest_breaks.py` | Checkpoint spacing, destination checkpoint, ETA estimation, break insertion | pytest with small handmade routes |
| `providers/` | Parsing real responses, error mapping (403, 429, timeout) | Saved JSON fixtures, mocked httpx |
| `api/` | Validation errors, response shape, error shape, `X-Request-ID` header | DRF `APITestCase` with fake providers |
| Frontend `lib/` + hooks | Risk colours and labels, formatting, debounce | Vitest |
| Heatmap smoothness | Time per slider update stays under one frame (16 ms) | Manual check in the Chrome Performance panel. The result goes in the README. |

---

## 9. Build plan

The steps run in this order. Each step finishes with a check that confirms it is done.

| # | Step | Done when |
|---|---|---|
| 1 | **Backend foundation:** Django + DRF project, SQLite configured but unused, `GET /api/health`, `make dev` and `make test`. | Health returns 200, and the test runner works. |
| 2 | **TomTom spike:** one real truck route, Denver → Salt Lake City, to confirm `progress[]` data and alternative routes. | The response matches the assumptions in [ADR-0006](adr/0006-checkpoint-eta-and-forecast-matching.md). |
| 3 | **Logging:** structlog + request-ID middleware. | Logs are JSON with `request_id`, and responses carry `X-Request-ID`. |
| 4 | **Cache:** LocMemCache configured. | Settings are in place. |
| 5 | **Core logic, test-first:** enums, pydantic models, `risk.py`, `ranking.py`. | Every boundary and ranking test passes. |
| 6 | **TomTom client + route selection** (including the fallback). | Up to 3 distinct routes come back for a real trip. |
| 7 | **Checkpoints + ETAs** (+ optional rest breaks). | Unit tests pass for spacing, the destination checkpoint, ETAs, and breaks. |
| 8 | **Open-Meteo client.** | A bulk forecast request is parsed and cached. |
| 9 | **Heatmap grid, `plan_trip()`, and the `/api/geocode` and `/api/plan` endpoints.** Deploy the bare backend to Render early. | `POST /api/plan` returns 3 ranked routes with checkpoints and heatmap data, both locally and on Render. |
| 10 | **React app:** search form + autocomplete → map + routes + checkpoints → route cards → heatmap + slider. | The full flow works in the browser against the local backend. |
| 11 | **Packaging:** Dockerfiles, `docker-compose.yml`, `render.yaml`, Gunicorn with 1 worker × 4 threads, and the complete Makefile. | `make up` works, and the hosted app works end to end. |
| 12 | **Polish:** error states, cold-start banner, slider profiling. | Slider updates stay under 16 ms. |
| 13 | **README** (with a key-decisions table) and **Loom walkthrough**. | Both deliverables are done. |

If the schedule slips, the rest-break toggle is the first thing to drop. It is isolated in `rest_breaks.py`, so dropping it touches nothing else.
