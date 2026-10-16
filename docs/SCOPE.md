# Scope — Weather-Aware Truck Routing

This document sets expectations for what the application does and does not do.
It is a **pre-trip planning tool**: it answers *"Which route should I take if I leave at this time?"*
It is not a live tracking or dispatch system.

---

## In scope

### Inputs
- Origin and destination (address or city), with autocomplete.
- Departure date and time.
- Load weight in pounds (lb).
- Checkpoint spacing: 10, 25, or 50 miles (user selectable).
- Optional toggle: **Include driver rest breaks** (off by default; see below).

### Routing
- Up to **3 truck-aware route options** from TomTom (`travelMode=truck`, load weight, commercial vehicle).
- If TomTom returns fewer than 3 routes, one extra request avoids an area around the middle of the main route to find a different road.
- If 3 distinct routes still do not exist, the app shows the routes it found and says so.

### Checkpoints and ETAs
- Checkpoints are placed every 10 / 25 / 50 miles along each route, plus the destination.
- Each checkpoint gets an ETA based on the departure time and TomTom's travel-time estimate. That estimate uses historic and live traffic.
- **Optional driver rest breaks.** When the toggle is on, ETAs include a simplified version of the US Hours-of-Service rules:
  - a 30-minute break after 8 hours of driving;
  - a 10-hour rest after 11 hours of driving.

### Weather and risk
- The forecast at each checkpoint is taken for the hour of the truck's ETA there (Open-Meteo hourly forecast).
- The risk level comes from the wind, rain, and snow thresholds in the brief. The worst of the three applies, and the load-weight rules are applied on top. See [Rule interpretations](#rule-interpretations).

### Recommendation
Routes are ranked in this order. A smaller value is better at each step, and each step only matters when the earlier ones are tied.

1. Fewest **No Travel** miles. If every route has some, show a warning.
2. Fewest **Severe** miles.
3. Fewest **High** miles.
4. Lowest mile-weighted average risk.
5. Shortest travel time.

### Map and UI
- All routes are drawn on a TomTom vector map (grey `basic_mono-light` style), and the selected route is highlighted (the recommended one at first).
- Checkpoint markers are coloured by risk level. Each popup shows the ETA, wind, gusts, rain, snow, and risk level, plus the reason for the risk.
- A route summary panel shows distance, travel time, and miles at each risk level.
- A weather heatmap is drawn along each route, with a forecast slider covering the 48 hours from the **departure hour**. Clicking a checkpoint moves the slider to its ETA. The full 48 hours of data is loaded once, so moving the slider does not trigger any network request.

### Re-planning
- A driver who is already on the road can get an updated plan by searching again, using their **current location as the origin** and **now as the departure time**.

### Geography
- **USA only.** Origin and destination must be in the contiguous United States (the lower 48 states).
- Address search is limited to the US.

---

## Out of scope

### Real-world events that change the timeline
ETAs assume the truck leaves on time and drives the route as planned. The app does **not** account for:
- truck breakdowns or repairs;
- unplanned or extended stops, such as long waits at a checkpoint, loading or unloading, fuel, inspections, or weigh stations;
- accidents, road closures, or detours that happen after the plan is made;
- the driver deviating from the chosen route;
- any other reason the truck reaches a checkpoint earlier or later than planned.

### Other limits
- **Full Hours-of-Service compliance.** The optional rest-break toggle is a simplification. It does not model the 14-hour on-duty window, the 60/70-hour weekly limits, split sleeper-berth rules, or exceptions.
- **Live tracking.** There is no GPS tracking and no automatic recalculation while driving. ETAs, risk levels, and the recommendation are calculated once per search.
- **Automatic forecast refresh.** Weather data is fetched once per search, so a newer forecast needs a new search.
- **Geography outside the US.** Canada, Mexico, Alaska, Hawaii, and US territories are not supported.
  - A route that briefly passes through Canada (if TomTom chooses one) is still shown and checked for weather. Origins and destinations outside the contiguous US are rejected.
- **Departure times in the past or too far ahead.** The whole trip must fit within the 16-day forecast range.
- **Weather hazards other than wind, rain, and snow.** Ice, fog, visibility, extreme heat or cold, and official weather alerts are not included.
- **Truck restrictions beyond weight.** Height, width, length, axles, and hazmat are not inputs. Routing uses load weight and the commercial-vehicle flag only.
- **Fuel stops, tolls, parking, cost optimisation, and multi-stop trips.**
- **Authentication and user management.** There is no sign-up, login, roles, or per-user data. The app is a public, anonymous planning tool.
- **Rate limiting.** There are no per-user or per-IP request limits. If the free third-party quotas run out, the API returns a clear error until they reset the next day.
- **Saved trips, trip history, notifications, and mobile apps.** Nothing is stored between searches.

---

## Rule interpretations

The brief leaves some details open. The application uses these interpretations.

| Topic | Interpretation |
|---|---|
| Shared boundaries (e.g. rain 0.25 sits in both "0.10–0.25" and "0.25–0.50") | A value exactly on a boundary goes into the **higher** band (0.25 → High). Exception: the No Travel bands are strictly greater than the limit (`>1.00` rain, `>3.0` snow), so 1.00 in/hr rain is Severe. |
| Combining conditions | Checkpoint risk = the worst of the wind, rain, and snow levels, then the load rules are applied. |
| Load rules | ≥55 mph → No Travel. 45–54 mph with load >30,000 lb → No Travel. 35–44 mph with load >40,000 lb → Severe. These rules can only raise a risk level, never lower it. |
| Wind measure | Sustained wind speed at 10 m (`wind_speed_10m`). Gusts are shown for information only. |
| Rain rate | Open-Meteo `rain` + `showers` for the hour (inches/hour), so thunderstorm downpours are included. |
| Snow rate | Open-Meteo `snowfall`: inches of snow per hour, as snow depth rather than melted-water equivalent. |
| Forecast hour at ETA | Rain and snow use the hour that contains the ETA. Wind uses the nearest hour. |
| Miles per risk level | Each checkpoint represents the road from that checkpoint to the next one. |
| Average risk | Mile-weighted average with Low = 0, Moderate = 1, High = 2, Severe = 3, No Travel = 4. It is rounded to 2 decimals before comparing routes. |
| No Travel in ranking | Not mentioned in the brief. It is ranked first, ahead of Severe miles. |

---

## Third-party services

| Purpose | Provider | Free limit |
|---|---|---|
| Base map (vector, `basic_mono-light`) | TomTom Orbis map style, drawn with MapLibre GL JS | 50,000 tile requests/day |
| Geocoding and autocomplete | TomTom Search | 2,500 non-tile requests/day, shared with routing |
| Truck routing (up to 3 routes) | TomTom Routing | Shared with the line above |
| Hourly weather forecast | Open-Meteo | 10,000 calls/day, no API key, non-commercial use |

To stay within these limits:
- Autocomplete waits 300 ms after typing stops and needs at least 3 characters before it sends a request.
- Geocoding results are cached in Django.
- Weather for all checkpoints and the road between them (at about 7-mile precision) is fetched in one bulk forecast request of at most 550 locations.

---

## Possible future improvements
- Live GPS tracking with automatic recalculation of ETAs and risk.
- Automatic forecast refresh while the page is open.
- Full Hours-of-Service modelling.
- NWS severe-weather alerts along the route.
- Truck dimension and hazmat inputs.
