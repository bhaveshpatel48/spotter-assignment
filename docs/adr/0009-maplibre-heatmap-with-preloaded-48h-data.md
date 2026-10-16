# ADR-0009: GPU weather layer with 48 hours of data preloaded

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
The brief requires a weather heatmap along the trip corridor with a 0–48 hour forecast slider.
35% of the evaluation is UI, map, and heatmap smoothness and performance.
If moving the slider re-fetched data or redrew the base map, the result would be visibly slow.

## Decision
- **Map:** use **MapLibre GL JS 6** directly, with TomTom's Orbis `basic_mono-light` style. TomTom's own MapLibre-based SDK is still a release candidate (`1.0.0-rc.2`) and pulls in extra dependencies, so plain MapLibre with the TomTom style URL is simpler and stable.
- **Weather layer:** a GPU-rendered **`circle` layer with full blur**, coloured by the risk level of each grid point. Neighbouring circles overlap into one smooth band. Each circle's radius is set from the API's `cell_size_deg`, so short and long trips both blend without gaps.
- **Load once:** after a search, the backend returns one point per weather location along the routes (every checkpoint plus every ~5 miles of road, at 0.1° precision). Each point carries **all 48 hourly risk values**.
- **The 48 hours start at the departure hour**, not at the current time, so the slider covers the trip itself even when departure is days away.
- **The slider only switches the hour.** Each point stores its 48 values as properties `h0`…`h47`. Moving the slider swaps one paint expression that blends the two neighbouring hours (e.g. hour 3.4 = 60% `h3` + 40% `h4`), so colours fade smoothly between hours. There is no network request, and the base map and route layers are not touched.
- Slider updates are limited to **one per animation frame**, via `requestAnimationFrame`.
- **Measured:** moving the slider through all 48 hours (236 updates, Denver → Salt Lake City at 10-mile spacing) took a median of 13.3 ms per frame and 14.0 ms at the 95th percentile, inside the 16 ms frame budget (60 fps). One of the 236 frames took 26 ms.

## Alternatives considered
- **Leaflet with raster tiles and a canvas heatmap plugin.** Rejected. The heatmap is drawn on the CPU, and TomTom's raster tiles have no grey style.
- **Fetching one hour of data per slider position.** Rejected. It adds network delay on every move and multiplies weather API calls.
- **MapLibre's built-in `heatmap` layer.** Rejected after trying it in design: it colours by point *density* (how many points overlap), not by the risk value, so a dense patch of Low-risk points could show as orange. Risk-coloured blurred circles show the actual level.
- **Filtering points by hour with `setFilter`.** Not needed: swapping one paint expression already fits in a frame.

## Consequences
- Slider movement is local and smooth. Base map tiles are never reloaded because of the slider.
- The search response is larger, since every grid point carries 48 values. This is acceptable for a few hundred points.
- The frontend depends only on MapLibre GL JS for the map. MapLibre's worker file is passed to it explicitly (`setWorkerUrl`), because bundling moves the file it would otherwise look for.
