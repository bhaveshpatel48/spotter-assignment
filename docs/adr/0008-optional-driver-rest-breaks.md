# ADR-0008: Driver rest breaks as an opt-in toggle

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
TomTom travel times assume the truck drives non-stop.
Under US Hours-of-Service rules, a truck driver must take a 30-minute break after 8 hours of driving and may drive at most 11 hours before a 10-hour rest.
On long trips, non-stop ETAs at later checkpoints are therefore too early, so the weather is checked for the wrong hour.
The brief does not mention driver rest.

## Decision
Add an **"Include driver rest breaks"** toggle, **off by default** so the default behaviour matches the brief exactly. When it is on, the ETA calculation inserts:
- a **30-minute break** after 8 hours of cumulative driving;
- a **10-hour rest** after 11 hours of driving, after which both counters reset.

## Alternatives considered
- **Always applying rest breaks.** Rejected. This would change the default behaviour beyond the brief.
- **Full Hours-of-Service modelling** (14-hour on-duty window, 60/70-hour weekly limits, sleeper-berth splits). Rejected. It is too complex for the value it adds here.
- **Ignoring rest breaks entirely.** Rejected. A small, isolated function makes the ETAs and weather timing realistic on long trips.

## Consequences
- The logic is a small pure function applied to the timeline of checkpoint ETAs, and it is unit-tested.
- With the toggle on, a trip can extend further into the forecast window, so the 16-day limit is checked after rest time is added.
- Full Hours-of-Service compliance remains out of scope ([SCOPE.md](../SCOPE.md)).
