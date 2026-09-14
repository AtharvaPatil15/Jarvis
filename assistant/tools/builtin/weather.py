"""Weather from Open-Meteo (free, keyless)."""
from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, Field

from assistant.tools.base import BaseTool

WMO_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain", 71: "light snow", 73: "snow", 75: "heavy snow",
    77: "snow grains", 80: "light showers", 81: "showers", 82: "violent showers", 85: "snow showers",
    86: "heavy snow showers", 95: "thunderstorm", 96: "thunderstorm with hail", 99: "severe thunderstorm with hail",
}


def _describe(code: Any) -> str:
    return WMO_CODES.get(int(code), "unknown conditions")


def _chance(value: Any) -> str:
    return "unknown" if value is None else f"{round(value)}%"


class GetWeatherArgs(BaseModel):
    location: str | None = Field(default=None, description="City name. Omit for the user's home location.")


class GetWeatherTool(BaseTool):
    name = "get_weather"
    description = "Current weather plus today's and tomorrow's forecast for a city (default: the user's home)."
    Args = GetWeatherArgs
    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, home_name: str, latitude: float, longitude: float,
                 transport: httpx.BaseTransport | None = None) -> None:
        self._home = (home_name, latitude, longitude)
        self._transport = transport

    def run(self, args: GetWeatherArgs) -> str:
        try:
            with httpx.Client(transport=self._transport, timeout=10) as client:
                if args.location:
                    geo = client.get(self.GEOCODE_URL, params={"name": args.location, "count": 1,
                                                               "language": "en", "format": "json"}).json()
                    results = geo.get("results") or []
                    if not results:
                        return f"ERROR: could not find a place called {args.location!r}"
                    place = results[0]
                    name = ", ".join(p for p in (place.get("name"), place.get("admin1"), place.get("country")) if p)
                    latitude, longitude = place["latitude"], place["longitude"]
                else:
                    name, latitude, longitude = self._home
                data = client.get(self.FORECAST_URL, params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
                    "timezone": "auto",
                    "forecast_days": 2,
                }).json()
        except (httpx.HTTPError, ValueError) as exc:
            return f"ERROR: weather service unavailable: {exc}"
        try:
            now, daily = data["current"], data["daily"]
            parts = [
                f"{name} now: {round(now['temperature_2m'])}°C (feels like {round(now['apparent_temperature'])}°C), "
                f"{_describe(now['weather_code'])}, humidity {round(now['relative_humidity_2m'])}%, "
                f"wind {round(now['wind_speed_10m'])} km/h."
            ]
            for index, label in enumerate(("Today", "Tomorrow")):
                parts.append(
                    f"{label}: {round(daily['temperature_2m_min'][index])}-{round(daily['temperature_2m_max'][index])}°C, "
                    f"{_describe(daily['weather_code'][index])}, "
                    f"rain chance {_chance(daily['precipitation_probability_max'][index])}."
                )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            return f"ERROR: unexpected weather data: {exc}"
        return " ".join(parts)