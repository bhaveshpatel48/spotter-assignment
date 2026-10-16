# ADR-0005: Strategy for getting three route options

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
The brief asks for **3 route options**. TomTom's `maxAlternatives` is an upper limit, not a guarantee: it only returns alternatives it considers reasonable.
Short trips, or trips with only one sensible corridor, may return just 1 or 2 routes. Alternatives can also share most of their road with the main route.

## Decision
1. Request the main route with `maxAlternatives=5`.
2. Keep the main route plus the **2 alternatives that differ most** from it, measured by the share of road length not shared with the main route.
3. If fewer than 3 routes remain, make **one extra request** with `avoidAreas`: a box of about 30×30 km centred on the midpoint of the main route. This forces a different path. Add the result if it is distinct.
4. If there are still fewer than 3 routes, return what was found and tell the user that only N practical routes exist.

## Alternatives considered
- **Always returning exactly what TomTom gives.** Rejected. It often produces fewer than 3 routes, or near-duplicates.
- **Inventing waypoints to force 3 routes.** Rejected. It can produce unrealistic detours and needs several extra requests.

## Consequences
- In most cases a search uses 1 TomTom request, and at most 2.
- The routes shown are meaningfully different choices.
- The UI must handle 1, 2, or 3 routes.
