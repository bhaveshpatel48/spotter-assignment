# ADR-0004: Backend proxies all third-party data APIs, with caching

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
- API keys placed in browser code are visible to anyone.
- The free quotas are small and are shared by every reviewer who uses the hosted app, all coming from the same server address.
- Typing in the autocomplete field could fire one request per keystroke.

## Decision
- **Geocoding, routing, and weather are called only from Django.** The React app calls our own API.
- **The TomTom map tiles are the only exception.** The browser loads tiles directly using a key restricted to our domain, which is the standard practice for tile keys.
- Autocomplete waits **300 ms after typing stops** and needs **at least 3 characters** before it sends a request.
- Django caches responses:
  - geocoding results, keyed on the normalised query text;
  - weather responses, keyed on the grid cell and time window, for 30–60 minutes.
- Weather coordinates are snapped to a 0.1° grid and duplicates are removed before one bulk Open-Meteo request is made.
- Each provider is wrapped in a small interface (`geocode()`, `get_routes()`, `get_forecast()`), so providers can be swapped and tests can use fakes.

## Alternatives considered
- **Calling the APIs directly from the browser.** Rejected. It exposes keys, cannot cache across users, and spreads quota handling across the frontend.

## Consequences
- Keys stay on the server, and repeated searches are fast and do not use quota.
- Autocomplete has one extra network hop, which the 300 ms wait hides.
- Provider errors (TomTom `403` for over-quota, Open-Meteo `429` for rate limits, and timeouts) are turned into clear API errors that the UI can display.
