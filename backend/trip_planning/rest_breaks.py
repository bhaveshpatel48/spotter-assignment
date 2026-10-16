"""Simplified Hours-of-Service rest time (ADR-0008).

A 30-minute break after 8 hours of driving, and a 10-hour rest after 11 hours of driving.
The 10-hour rest resets both counters.
"""

BREAK_AFTER_S = 8 * 3600
BREAK_S = 30 * 60
REST_AFTER_S = 11 * 3600
REST_S = 10 * 3600


def rest_seconds_before(driving_s: float) -> float:
    """Total break and rest time taken before reaching `driving_s` seconds of driving."""
    if driving_s <= 0:
        return 0.0
    full_shifts, into_shift = divmod(driving_s, REST_AFTER_S)
    if into_shift == 0:
        # Arriving exactly at the 11-hour limit: that shift's rest has not started yet.
        full_shifts -= 1
        into_shift = REST_AFTER_S
    rest = full_shifts * (BREAK_S + REST_S)
    if into_shift > BREAK_AFTER_S:
        rest += BREAK_S
    return rest
