# ADR-0011: DRF serializers at the API boundary, pydantic models internally, enums for fixed values

- **Status:** Accepted
- **Date:** 2026-10-15

## Context
The API needs strict validation of incoming data and a consistent response shape.
Inside the backend, data passes between the provider clients and the planning functions: route points, checkpoints, forecasts, and risk results. That data needs to be typed and validated too, because TomTom and Open-Meteo responses come from outside our control.
Several values come from a fixed set:
- risk levels;
- checkpoint spacing;
- weather conditions;
- log event names.

## Decision
- **DRF serializers** cover the HTTP boundary only: request validation and response shaping.
  - Input checks: coordinates inside the contiguous US, a load-weight range, a departure-time window that fits within the forecast range, and spacing values from the enum.
- **pydantic models** are used for all internal data:
  - **Provider responses.** TomTom and Open-Meteo JSON is parsed into pydantic models in the provider clients, so missing or malformed fields fail early, with a clear error, at the integration edge.
  - **Domain data.** Route points, checkpoints, hourly forecasts, risk results, and route summaries are passed between the planning functions as pydantic models. They are frozen (`model_config = ConfigDict(frozen=True)`), so values cannot change unexpectedly.
- **Python enums** hold every fixed set of values:
  - `RiskLevel` (`IntEnum`: `LOW=0` to `NO_TRAVEL=4`, so levels can be compared and averaged);
  - `CheckpointSpacing` (10 / 25 / 50 miles);
  - `WeatherCondition` (wind / rain / snow);
  - `EventName` (see [ADR-0014](0014-structlog-and-request-id.md)).
- Both serializers (`ChoiceField`) and pydantic models use these enums, so allowed values are defined in a single place.

## Alternatives considered
- **pydantic for the API boundary too, instead of serializers.** Rejected. DRF serializers are the standard DRF approach ([ADR-0010](0010-drf-rest-api-with-separate-react-frontend.md)).
- **Standard-library `dataclasses` for internal data.** Rejected. They do no validation, which matters when parsing third-party responses.
- **Serializers for internal data.** Rejected. Serializers belong at the HTTP boundary. Using them inside pure calculation code adds overhead and couples that code to DRF.
- **Plain dictionaries.** Rejected. They are untyped and easy to misspell.

## Consequences
- Each layer has one validation tool:
  - serializers check the requests that clients send us;
  - pydantic checks the responses third-party services send us, and the data passed between our own functions.
- The planning logic does not depend on DRF and is easy to unit-test.
- Response serializers read from the internal pydantic models. The data passes through two layers, a small and deliberate cost for keeping these concerns apart.
- pydantic is added as a backend dependency.
