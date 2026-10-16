# ADR-0013: In-process cache, one Gunicorn worker with four threads

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
Geocoding and weather responses should be cached to cut latency and save free API quota ([ADR-0004](0004-backend-proxies-third-party-apis.md)).
A separate cache service such as Redis adds a component to run, configure, and host.

A plan request spends about 2–5 seconds waiting on TomTom and Open-Meteo. Gunicorn's default is **1 worker handling 1 request at a time**, so while one plan request runs, every other request waits, including other users' autocomplete calls.

Render's free instance has 512 MB of RAM.

## Decision
- Use Django's **in-process memory cache** (`django.core.cache.backends.locmem.LocMemCache`).
- Run Gunicorn with **1 worker and 4 threads** (`--workers 1 --threads 4`):
  - **1 worker** means 1 process, so every request shares one cache, and memory stays low.
  - **4 threads** let up to 4 requests run at once. That suits this workload because each request spends most of its time waiting on external APIs.
- `LocMemCache` is safe to use from multiple threads.

## Alternatives considered
| Option | Why rejected |
|---|---|
| Redis | An extra service for no benefit at this scale. |
| Multiple Gunicorn workers | Each worker would have its own separate cache, so fewer cache hits, and memory use would multiply on a 512 MB instance. |
| 1 worker, 1 thread (Gunicorn default) | A single slow plan request would block every other request. |
| Async (ASGI + async views) | More complex. DRF does not support async views out of the box. |

## Consequences
- No extra infrastructure.
- The cache is emptied whenever the service restarts or Render puts it to sleep, so the first requests after that are slower.
- Scaling to multiple instances later would need a shared cache such as Redis. That only means changing the `CACHES` setting.
