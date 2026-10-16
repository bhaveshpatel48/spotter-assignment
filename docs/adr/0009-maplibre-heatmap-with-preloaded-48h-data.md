# ADR-0009: GPU heatmap with 48 hours of data preloaded

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
The brief requires a weather heatmap along the trip corridor with a 0–48 hour forecast slider.
35% of the evaluation is UI, map, and heatmap smoothness and performance.
If moving the slider re-fetched data or redrew the base map, the result would be visibly slow.

## Decision
- **Map:** use the TomTom Maps SDK for JavaScript. It is built on **MapLibre GL JS**, and its `mapLibreMap` property gives access to the underlying MapLibre map. This lets us use MapLibre's **built-in, GPU-rendered `heatmap` layer**.
- **Load once:** after a search, the backend returns the corridor grid, a few hundred points within a band around the routes. Each point carries **all 48 hourly risk values**.
- **The slider only switches the hour.** Moving it changes which hourly value the heatmap reads (a paint-property expression such as `['get', 'h12']`). There is no network request, and the base map and route layers are not touched.
- Slider updates are limited to **one per animation frame**, via `requestAnimationFrame`.
- Heatmap update time is measured with the browser profiler during development. The aim is to stay well under one frame (about 16 ms). The result goes in the README.

## Alternatives considered
- **Leaflet with raster tiles and a canvas heatmap plugin.** Rejected. The heatmap is drawn on the CPU, and TomTom's raster tiles have no grey style.
- **Fetching one hour of data per slider position.** Rejected. It adds network delay on every move and multiplies weather API calls.
- **Filtering points by hour with `setFilter`, instead of switching a value on each point.** Kept as a fallback. Profiling will decide which is faster.

## Consequences
- Slider movement is local and smooth. Base map tiles are never reloaded because of the slider.
- The search response is larger, since every grid point carries 48 values. This is acceptable for a few hundred points.
- The frontend depends on MapLibre GL JS, which the TomTom SDK requires as a peer dependency.
