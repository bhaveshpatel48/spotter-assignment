# ADR-0006: Checkpoint ETAs and matching them to forecast hours

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
Weather must be sampled every 10, 25, or 50 miles, at the truck's **estimated arrival time** at each checkpoint.
TomTom returns:
- the route shape as `legs[].points`;
- a `progress[]` array (with `extendedRouteRepresentation=distance,travelTime`) giving cumulative distance and travel time, but **only at some points**. The first and last points are always included.

Open-Meteo returns hourly values:
- `rain`, `showers`, and `snowfall` are totals for the **preceding hour**;
- `wind_speed_10m` is the value **at that moment**.

## Decision
- **Distance along the route:** add up the haversine distances between consecutive route points.
- **Checkpoint positions:** place checkpoints at every N miles along that distance, and add the destination.
- **ETA at a checkpoint:** estimate the travel time in proportion to distance between the nearest `progress` entries before and after the checkpoint. ETA = departure time + travel time (+ rest breaks if enabled, see [ADR-0008](0008-optional-driver-rest-breaks.md)).
- **All times are handled in UTC.** They are converted to local time only for display.
- **Matching the forecast hour:**
  - rain and snow use the hour that **contains** the ETA (an ETA of 15:40 uses the 16:00 value, which covers 15:00–16:00);
  - wind uses the **nearest** hour.
- **Unit conversion:** the load is entered in pounds and converted to kg for TomTom (× 0.4536). The risk rules are evaluated in pounds.

## Alternatives considered
- **Assuming a constant average speed for the whole route.** Rejected. It ignores the difference between highway and urban speeds, while TomTom's `progress` data captures it.
- **Using the nearest hour for every variable.** Rejected. Rain and snow are totals for the preceding hour, so taking the nearest hour could pick the wrong period.

## Consequences
- ETAs are about as accurate as TomTom's travel-time model allows, without extra API calls.
- The ETA logic is pure Python and can be unit-tested with fixed route data.
