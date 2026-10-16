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


# The risk levels compared by the first three positions of rank_key, in the same order.
RANKED_LEVELS = (RiskLevel.NO_TRAVEL, RiskLevel.SEVERE, RiskLevel.HIGH)


def ranking_reasons(summaries: Sequence[RouteSummary]) -> list[str]:
    """One sentence per route (in the order of `summaries`) explaining its place in the ranking.

    The recommended route is compared with the runner-up; every other route with the route
    ranked just above it. The sentence names the first ranking rule that tells them apart,
    so it always matches rank_key.
    """
    order = rank_order(summaries)
    reasons = [""] * len(summaries)
    if len(order) == 1:
        reasons[order[0]] = "The only practical route for this trip."
        return reasons

    best, runner_up = order[0], order[1]
    reasons[best] = _compare(summaries[best], summaries[runner_up], other_rank=2, better=True)
    for rank, index in enumerate(order[1:], start=2):
        above = summaries[order[rank - 2]]
        reasons[index] = _compare(summaries[index], above, other_rank=rank - 1, better=False)
    return reasons


def _compare(route: RouteSummary, other: RouteSummary, other_rank: int, better: bool) -> str:
    """Why `route` ranks above (better=True) or below `other`."""
    name = f"Route {other_rank}"
    mine, theirs = rank_key(route), rank_key(other)
    position = next((i for i, (a, b) in enumerate(zip(mine, theirs, strict=True)) if a != b), None)

    if position is None:
        return f"Same weather risk and travel time as {name}."
    if position < len(RANKED_LEVELS):
        label = RANKED_LEVELS[position].label
        comparison = "Fewer" if better else "More"
        values = f"{mine[position]:.0f} vs {theirs[position]:.0f} mi"
        return f"{comparison} {label} miles than {name} ({values})."
    if position == len(RANKED_LEVELS):
        comparison = "Lower" if better else "Higher"
        values = f"{mine[position]:.2f} vs {theirs[position]:.2f}"
        return f"{comparison} average risk than {name} ({values})."
    difference = _duration(abs(route.travel_time_s - other.travel_time_s))
    if better:
        return f"Same weather risk as {name}, and {difference} faster."
    return f"Same weather risk as {name}, but {difference} slower."


def _duration(seconds: int) -> str:
    hours, minutes = divmod(round(seconds / 60), 60)
    return f"{hours} h {minutes} m" if hours else f"{minutes} m"
