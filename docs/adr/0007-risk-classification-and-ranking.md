# ADR-0007: Risk classification and route ranking

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
The brief defines thresholds for wind, rain, and snow, load-weight rules, and an order of preference for routes.
Several details are left open:
- some band boundaries overlap;
- how the three conditions combine at one checkpoint;
- what "average risk" means;
- where No Travel fits in the ranking.

## Decision
**Classification:**
- A value exactly on a boundary goes into the **higher** band (for example, rain at 0.25 in/hr is High).
- The No Travel bands are strictly greater than their limits (`>1.00` rain, `>3.0` snow), so 1.00 in/hr rain is Severe.
- Wind is sustained `wind_speed_10m`. Rain is `rain + showers`. Snow is `snowfall`.
- Checkpoint risk = the **worst** of the wind, rain, and snow levels.
- Load rules are applied next, and can only raise the level:

  | Wind | Load | Result |
  |---|---|---|
  | ≥55 mph | Any | No Travel |
  | 45–54 mph | >30,000 lb | No Travel |
  | 35–44 mph | >40,000 lb | Severe |

**Miles at each risk level:**
- Each checkpoint represents the road from that checkpoint to the next one.

**Ranking** (lexicographic: a smaller value is better at each step):
1. No Travel miles
2. Severe miles
3. High miles
4. Mile-weighted average risk, with Low = 0, Moderate = 1, High = 2, Severe = 3, No Travel = 4, rounded to 2 decimals
5. Travel time

If every route has No Travel miles, the best route is still recommended, together with a **"No safe route — consider delaying departure"** warning.

## Alternatives considered
- **A single weighted score combining risk and time.** Rejected. The brief gives an explicit order of preference, and a weighted score would hide it.
- **Leaving No Travel out of the ranking, as the brief does.** Rejected. A route with No Travel miles must never beat a route with only Severe miles.

## Consequences
- The ranking is deterministic and easy to explain. Each route carries a `ranking_reason` generated from the same ranking rules (e.g. *"Same weather risk as Route 2, and 26 m faster."*), so the explanation can never disagree with the ranking.
- Classification and ranking are pure functions with table-driven unit tests, including every boundary value.
- These interpretations are documented in [SCOPE.md](../SCOPE.md#rule-interpretations).
