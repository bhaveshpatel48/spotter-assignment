"""Risk classification rules from the brief. Interpretations are documented in ADR-0007.

Bands include their lower bound, so a value on a boundary falls into the higher band.
The No Travel bands for rain and snow are strictly greater than their limit.
"""

from trip_planning.enums import RiskLevel
from trip_planning.models import RiskAssessment, WeatherSample


def wind_level(mph: float) -> RiskLevel:
    if mph >= 55:
        return RiskLevel.NO_TRAVEL
    if mph >= 45:
        return RiskLevel.SEVERE
    if mph >= 35:
        return RiskLevel.HIGH
    if mph >= 25:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def rain_level(inches_per_hour: float) -> RiskLevel:
    if inches_per_hour > 1.00:
        return RiskLevel.NO_TRAVEL
    if inches_per_hour >= 0.50:
        return RiskLevel.SEVERE
    if inches_per_hour >= 0.25:
        return RiskLevel.HIGH
    if inches_per_hour >= 0.10:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def snow_level(inches_per_hour: float) -> RiskLevel:
    if inches_per_hour > 3.0:
        return RiskLevel.NO_TRAVEL
    if inches_per_hour >= 2.0:
        return RiskLevel.SEVERE
    if inches_per_hour >= 1.0:
        return RiskLevel.HIGH
    if inches_per_hour >= 0.5:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def load_level(wind_mph: float, load_weight_lb: int) -> RiskLevel:
    """Minimum risk level imposed by the load-weight rules."""
    if wind_mph >= 55:
        return RiskLevel.NO_TRAVEL
    if wind_mph >= 45 and load_weight_lb > 30_000:
        return RiskLevel.NO_TRAVEL
    if wind_mph >= 35 and load_weight_lb > 40_000:
        return RiskLevel.SEVERE
    return RiskLevel.LOW


def risk_level(
    wind_mph: float, rain_in_hr: float, snow_in_hr: float, load_weight_lb: int
) -> RiskLevel:
    """Worst of wind, rain and snow, raised by the load rules. Used for the heatmap."""
    return max(
        wind_level(wind_mph),
        rain_level(rain_in_hr),
        snow_level(snow_in_hr),
        load_level(wind_mph, load_weight_lb),
    )


def assess(weather: WeatherSample, load_weight_lb: int) -> RiskAssessment:
    """Risk level plus the human-readable reasons behind it. Used for checkpoints."""
    wind = wind_level(weather.wind_mph)
    rain = rain_level(weather.rain_in_hr)
    snow = snow_level(weather.snow_in_hr)
    load = load_level(weather.wind_mph, load_weight_lb)

    reasons = []
    if wind > RiskLevel.LOW:
        reasons.append(f"Wind {weather.wind_mph:.0f} mph ({wind.label})")
    if rain > RiskLevel.LOW:
        reasons.append(f"Rain {weather.rain_in_hr:.2f} in/hr ({rain.label})")
    if snow > RiskLevel.LOW:
        reasons.append(f"Snow {weather.snow_in_hr:.2f} in/hr ({snow.label})")
    if load > wind:
        reasons.append(
            f"Load {load_weight_lb:,} lb with wind {weather.wind_mph:.0f} mph ({load.label})"
        )

    return RiskAssessment(level=max(wind, rain, snow, load), reasons=tuple(reasons))
