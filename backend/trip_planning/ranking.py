"""Route summaries and ranking (ADR-0007)."""

from collections.abc import Sequence

from trip_planning.enums import RiskLevel
from trip_planning.models import Checkpoint, RouteSummary


def miles_by_risk(checkpoints: Sequence[Checkpoint]) -> dict[RiskLevel, float]:
    """Each checkpoint represents the road from itself to the next checkpoint."""
    totals = dict.fromkeys(RiskLevel, 0.0)
    for current, following in zip(checkpoints, checkpoints[1:], strict=False):
        totals[current.risk.level] += following.mile - current.mile
    return {level: round(miles, 1) for level, miles in totals.items()}


def average_risk(miles: dict[RiskLevel, float]) -> float:
    """Mile-weighted average of the risk scores (Low = 0 ... No Travel = 4)."""
    total = sum(miles.values())
    if total == 0:
        return 0.0
    return round(sum(level * distance for level, distance in miles.items()) / total, 2)


def rank_key(summary: RouteSummary) -> tuple[float, float, float, float, int]:
    """Smaller is better at every position; later positions only break ties."""
    miles = summary.miles_by_risk
    return (
        miles[RiskLevel.NO_TRAVEL],
        miles[RiskLevel.SEVERE],
        miles[RiskLevel.HIGH],
        summary.average_risk,
        summary.travel_time_s,
    )


def rank_order(summaries: Sequence[RouteSummary]) -> list[int]:
    """Indexes of `summaries`, best route first. Ties keep the provider's order."""
    return sorted(range(len(summaries)), key=lambda i: rank_key(summaries[i]))


def has_no_safe_route(summaries: Sequence[RouteSummary]) -> bool:
    return all(summary.miles_by_risk[RiskLevel.NO_TRAVEL] > 0 for summary in summaries)
