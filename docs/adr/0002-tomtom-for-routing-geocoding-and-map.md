# ADR-0002: TomTom for routing, geocoding, and the base map

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
The app needs three things from location services:
- truck-aware routing with alternative routes over long US distances;
- address geocoding with autocomplete;
- an interactive base map.

The constraints are:
- a free tier with **no credit card**;
- support for the US;
- as few third-party integrations as possible, to keep maintenance low.

## Decision
Use **TomTom** for all three, with one account (a server key, plus a browser key for the map only):
- **Routing API** with `travelMode=truck`, `vehicleWeight`, and `vehicleCommercial=true`, plus `maxAlternatives` for extra routes.
- **Search API** for geocoding and autocomplete, limited to the US.
- **Orbis map style** `basic_mono-light` (vector tiles), loaded directly into MapLibre GL JS, for the base map. The browser uses a separate key with only Map Display (Orbis) enabled, restricted to the site's domain.

Free limits are 2,500 non-tile requests per day (shared by routing and search) and 50,000 tile requests per day. No card is needed.

## Alternatives considered
| Option | Why rejected |
|---|---|
| OpenRouteService (`driving-hgv`) | Alternative routes are capped at **100 km**, so they cannot be used for long US trips. |
| Geoapify | Has no alternative-routes parameter. Using it only for geocoding would mean a second provider. |
| HERE | Has the best truck data, but the free plan now needs a card on file. |
| Google Routes / Mapbox | Both need a card, and neither has a truck profile. |
| GraphHopper (free) | The free plan has no truck profile. |
| OSRM demo server | Car profile only, and its usage policy does not allow production use. |
| OSM community tiles | The tile usage policy forbids heavy or production use. |

## Consequences
- One account, one key, one client module, and consistent coordinates between search results and routes.
- TomTom has the best US address data among the free options that need no card.
- Search and routing share the 2,500/day quota. A search uses about 11 requests (roughly 10 autocomplete calls and 1 route call), so about 200 searches a day are possible. That is enough for evaluation. See [ADR-0004](0004-backend-proxies-third-party-apis.md) for how usage is reduced.
- TomTom is a single point of failure for location services. This is accepted for an assignment, and the code keeps provider access behind small interfaces so another provider could be swapped in.
- The map must show TomTom attribution.
