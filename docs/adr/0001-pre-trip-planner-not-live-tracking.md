# ADR-0001: Pre-trip planner, not live tracking

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
The brief asks for an app that recommends the safest route based on the origin, destination, departure time, and load weight.
In practice, things change after departure: rest stops, breakdowns, delays, and newer forecasts. Tracking the truck live would need a GPS feed, background jobs, stored trip state, and push updates.
The brief also says: *"Prioritize correctness and clarity over extra features."*

## Decision
Build a **stateless pre-trip planner**. Each search calculates routes, ETAs, weather risk, and a recommendation once, and nothing is stored or updated afterwards.
A driver already on the road re-plans by searching again, with the current location as the origin and now as the departure time.

## Alternatives considered
- **Live tracking with automatic recalculation.** Rejected. It needs a mobile client, background workers, and persistent state, which goes beyond the brief and adds a lot of work.
- **Automatic forecast refresh on a timer.** Rejected. It adds little for a planning tool, and searching again gives the same result.

## Consequences
- The backend can stay stateless: there are no trip records, and the only database use is the cache.
- ETAs ignore anything that happens after the plan is made, such as breakdowns, long stops, or detours. This is documented as out of scope in [SCOPE.md](../SCOPE.md).
- Live tracking can be added later without changing the planning logic.
