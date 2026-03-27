"""
AgriMind AI – Weather Module
Fetches current conditions + 7-day forecast from the free Open-Meteo API.
No API key required.
"""

from __future__ import annotations
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES: dict[int, tuple[str, str]] = {
    0:  ("Clear sky", "☀️"),
    1:  ("Mainly clear", "🌤️"),
    2:  ("Partly cloudy", "⛅"),
    3:  ("Overcast", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Icy fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    61: ("Light rain", "🌧️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    71: ("Light snow", "❄️"),
    80: ("Rain showers", "🌦️"),
    95: ("Thunderstorm", "⛈️"),
    99: ("Heavy thunderstorm", "⛈️"),
}


def _weather_label(code: int) -> tuple[str, str]:
    """Return (description, emoji) for a WMO weather code."""
    if code in WEATHER_CODES:
        return WEATHER_CODES[code]
    if code <= 3:
        return "Partly cloudy", "⛅"
    if code <= 49:
        return "Foggy / misty", "🌫️"
    if code <= 67:
        return "Rainy", "🌧️"
    if code <= 77:
        return "Snow", "❄️"
    if code <= 82:
        return "Rain showers", "🌦️"
    if code <= 99:
        return "Thunderstorm", "⛈️"
    return "Variable", "🌤️"


async def get_weather_by_coords(latitude: float, longitude: float) -> dict:
    """
    Get weather for given coordinates (lat, lon).
    Attempts reverse geocoding for friendly location name (best-effort).
    Raises ValueError on fatal failure.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        # Try reverse geocoding for a friendly name, but fail gracefully
        name = f"Your Location ({latitude:.2f}, {longitude:.2f})"
        try:
            geo_res = await client.get(
                GEOCODE_URL,
                params={"name": f"{latitude},{longitude}", "count": 1}
            )
            if geo_res.status_code == 200:
                geo = geo_res.json()
                results = geo.get("results") or []
                if results:
                    place = results[0]
                    name = f"{place.get('name', 'Your location')}, {place.get('country', '')}"
        except Exception:
            # Silently fall back to coordinate-based name
            pass

        # Fetch weather (this is the critical part)
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,"
                "wind_speed_10m,precipitation,weather_code"
            ),
            "daily": (
                "precipitation_sum,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max"
            ),
            "timezone": "auto",
            "forecast_days": 7,
        }
        w_res = await client.get(FORECAST_URL, params=params)
        w_res.raise_for_status()
        w = w_res.json()

    return _format_weather_response(w, name)


async def get_weather(location: str) -> dict:
    """
    Geocode a location string and return structured weather data.
    Raises ValueError on failure.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        # Step 1 – geocode
        geo_res = await client.get(GEOCODE_URL, params={"name": location, "count": 1})
        geo_res.raise_for_status()
        geo = geo_res.json()

        results = geo.get("results") or []
        if not results:
            raise ValueError(f"Location '{location}' not found.")

        place = results[0]
        lat, lon = place["latitude"], place["longitude"]
        name = f"{place.get('name', location)}, {place.get('country', '')}"

        # Step 2 – forecast
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,relative_humidity_2m,"
                "wind_speed_10m,precipitation,weather_code"
            ),
            "daily": (
                "precipitation_sum,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max"
            ),
            "timezone": "auto",
            "forecast_days": 7,
        }
        w_res = await client.get(FORECAST_URL, params=params)
        w_res.raise_for_status()
        w = w_res.json()

    return _format_weather_response(w, name)


def _format_weather_response(w: dict, name: str) -> dict:
    """
    Format raw OpenMeteo response into structured weather data.
    """
    c = w["current"]
    daily = w["daily"]

    desc, emoji = _weather_label(c["weather_code"])

    weekly_rain = sum(v or 0 for v in daily["precipitation_sum"])
    max_temp = max(daily["temperature_2m_max"])
    min_temp = min(daily["temperature_2m_min"])
    avg_rain_prob = (
        sum(v or 0 for v in daily.get("precipitation_probability_max", [0] * 7)) / 7
    )

    # Farming-specific risk flags
    flags: list[str] = []
    if c["relative_humidity_2m"] > 75:
        flags.append("High humidity – elevated fungal disease risk")
    if c["precipitation"] > 10:
        flags.append("Significant rainfall today – avoid fertiliser/pesticide application")
    if c["temperature_2m"] > 38:
        flags.append("Extreme heat – increase irrigation frequency")
    if c["temperature_2m"] < 5:
        flags.append("Near-frost conditions – protect sensitive crops")
    if c["wind_speed_10m"] > 40:
        flags.append("High winds – avoid spraying operations")

    return {
        "location": name,
        "current": {
            "temperature": c["temperature_2m"],
            "humidity": c["relative_humidity_2m"],
            "precipitation": c["precipitation"],
            "wind_speed": c["wind_speed_10m"],
            "description": desc,
            "emoji": emoji,
        },
        "forecast": {
            "weekly_rain_mm": round(weekly_rain, 1),
            "max_temp": max_temp,
            "min_temp": min_temp,
            "avg_rain_probability_pct": round(avg_rain_prob),
        },
        "farming_flags": flags,
        # Compact string injected into AI prompt
        "context_string": (
            f"Weather at {name}: {c['temperature_2m']}°C, {desc}, "
            f"Humidity {c['relative_humidity_2m']}%, "
            f"Rain today {c['precipitation']}mm, "
            f"Wind {c['wind_speed_10m']} km/h. "
            f"7-day forecast: {round(weekly_rain,1)}mm rain, "
            f"{min_temp}–{max_temp}°C range, "
            f"~{round(avg_rain_prob)}% rain probability. "
            + (f"Farming alerts: {'; '.join(flags)}." if flags else "")
        ),
    }