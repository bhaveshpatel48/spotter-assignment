# ADR-0003: Open-Meteo for hourly weather forecasts

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
The risk rules need **hourly** wind speed (mph), rain rate (in/hr), and snow rate (in/hr) at every checkpoint.
The forecast must be taken for the hour of the truck's ETA there, which can be anywhere from the departure time to the end of the trip.
The heatmap needs the same data for a grid of points along the route for the next 0–48 hours.
A long trip can involve hundreds of locations per search, and the service must not require a credit card.

## Decision
Use **Open-Meteo's forecast API**:
- Variables: `wind_speed_10m`, `wind_gusts_10m`, `rain`, `showers`, and `snowfall`.
- Units: `wind_speed_unit=mph` and `precipitation_unit=inch`.
- Times: `timeformat=unixtime`, in UTC.
- **Many locations per request**: comma-separated coordinates, sent with POST so long lists fit.

## Alternatives considered
| Option | Why rejected |
|---|---|
| NWS api.weather.gov | Rain and snow come in 6-hour blocks rather than hourly, rain is not separated from total precipitation, and each point needs 2 requests. Kept as a possible future source of official alerts. |
| WeatherAPI.com | Only one location per request on the free plan, so a search would need hundreds of requests. |
| OpenWeatherMap | The free forecast is 3-hourly. The hourly One Call product needs a paid subscription. |
| Tomorrow.io, Pirate Weather, Weatherbit, AccuWeather | Their free quotas are too small for hundreds of points per search. |
| MET Norway | Has no separate snowfall field. |

## Consequences
- No API key is needed. The US forecast uses NOAA models (HRRR and GFS).
- Each location counts as at least 1 call (10,000/day, 5,000/hour, 600/minute). Each search therefore requests at most 550 locations: every checkpoint at about 7-mile precision first, then the heatmap grid. Correct checkpoint weather is prioritised over search throughput, so a second new search within the same minute may be asked to retry. Responses are cached for 30 minutes.
- The forecast extends up to 16 days, so the whole trip must fit inside that window.
- The free tier is non-commercial, which is acceptable for this assignment.
- The map must show Open-Meteo attribution.
