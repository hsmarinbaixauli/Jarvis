"""OpenWeatherMap REST client."""

from __future__ import annotations

import os
from typing import Any

import requests

_ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"
_TIMEOUT_SECONDS = 5.0


def _format_response(raw: dict[str, Any], units: str) -> dict[str, Any]:
    return {
        "city": raw.get("name", ""),
        "temperature": round(raw["main"]["temp"]),
        "feels_like": round(raw["main"]["feels_like"]),
        "description": raw["weather"][0]["description"],
        "humidity": raw["main"]["humidity"],
        "wind_kmh": round(raw["wind"]["speed"] * 3.6),
        "units": units,
    }


def get_current_weather(city: str | None = None, units: str | None = None) -> dict[str, Any]:
    """Fetch current weather from OpenWeatherMap.

    Args:
        city: City name e.g. "Valencia,ES". Falls back to OPENWEATHER_CITY env var.
        units: "metric" or "imperial". Falls back to OPENWEATHER_UNITS env var, then "metric".

    Returns:
        Normalised dict: city, temperature, feels_like, description, humidity, wind_kmh, units.

    Raises:
        RuntimeError: If OPENWEATHER_API_KEY is missing or city is unresolvable.
        requests.RequestException: On network failure.
    """
    api_key: str | None = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is not set.")

    resolved_city: str | None = city or os.environ.get("OPENWEATHER_CITY")
    if not resolved_city:
        raise RuntimeError("No city specified. Pass city= or set OPENWEATHER_CITY in .env.")

    resolved_units: str = units or os.environ.get("OPENWEATHER_UNITS", "metric")

    response = requests.get(
        _ENDPOINT,
        params={
            "q": resolved_city,
            "appid": api_key,
            "units": resolved_units,
            "lang": "es",
        },
        timeout=_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return _format_response(response.json(), resolved_units)
