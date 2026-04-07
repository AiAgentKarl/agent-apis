"""
Wetter-API — Serverless Function für Vercel.
Liefert aktuelle Wetterdaten für jeden Ort weltweit.
Primär: wttr.in (robust, schnell, kein API-Key).
Fallback: Open-Meteo (Geocoding + Forecast).
"""

from http.server import BaseHTTPRequestHandler
import json
import httpx
from urllib.parse import urlparse, parse_qs


WTTR_URL = "https://wttr.in"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO-Wettercodes
WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Thunderstorm + heavy hail",
}


def _json_response(handler, status_code, data):
    """JSON-Antwort senden."""
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Cache-Control", "public, max-age=300")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, indent=2).encode())


def _fetch_wttr(location: str) -> dict | None:
    """Wetterdaten via wttr.in holen (primäre Quelle, sehr zuverlässig)."""
    try:
        resp = httpx.get(
            f"{WTTR_URL}/{location}",
            params={"format": "j1"},
            timeout=8.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; agent-apis/1.0)"},
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        current = data["current_condition"][0]
        area = data.get("nearest_area", [{}])[0]

        # Standortname aus wttr.in
        area_name = area.get("areaName", [{}])[0].get("value", location)
        country = area.get("country", [{}])[0].get("value", "")
        location_str = f"{area_name}, {country}" if country else area_name

        return {
            "location": location_str,
            "latitude": float(area.get("latitude", 0)),
            "longitude": float(area.get("longitude", 0)),
            "temperature_c": float(current.get("temp_C", 0)),
            "feels_like_c": float(current.get("FeelsLikeC", 0)),
            "humidity_pct": int(current.get("humidity", 0)),
            "wind_speed_kmh": float(current.get("windspeedKmph", 0)),
            "wind_gusts_kmh": float(current.get("WindGustKmph", 0)),
            "wind_direction_deg": int(current.get("winddirDegree", 0)),
            "precipitation_mm": float(current.get("precipMM", 0)),
            "cloud_cover_pct": int(current.get("cloudcover", 0)),
            "pressure_hpa": float(current.get("pressure", 0)),
            "uv_index": int(current.get("uvIndex", 0)),
            "visibility_km": float(current.get("visibility", 0)),
            "condition": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
            "source": "wttr.in",
        }
    except Exception:
        return None


def _fetch_openmeteo(location: str, lat: str, lon: str) -> dict | None:
    """Fallback: Open-Meteo API."""
    try:
        if location and not (lat and lon):
            geo = httpx.get(
                GEOCODING_URL,
                params={"name": location, "count": 1, "language": "en"},
                timeout=5.0,
            ).json()
            if not geo.get("results"):
                return None
            r = geo["results"][0]
            lat = r["latitude"]
            lon = r["longitude"]
            name = f"{r.get('name', location)}, {r.get('country', '')}"
        else:
            lat = float(lat)
            lon = float(lon)
            name = f"{lat}, {lon}"

        weather = httpx.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_gusts_10m,cloud_cover,surface_pressure,uv_index,is_day",
                "timezone": "auto",
            },
            timeout=5.0,
        ).json()

        current = weather.get("current", {})
        wc = current.get("weather_code", 0)
        return {
            "location": name,
            "latitude": lat,
            "longitude": lon,
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "wind_gusts_kmh": current.get("wind_gusts_10m"),
            "precipitation_mm": current.get("precipitation"),
            "cloud_cover_pct": current.get("cloud_cover"),
            "pressure_hpa": current.get("surface_pressure"),
            "uv_index": current.get("uv_index"),
            "condition": WMO_CODES.get(wc, "Unknown"),
            "weather_code": wc,
            "timezone": weather.get("timezone", ""),
            "source": "open-meteo",
        }
    except Exception:
        return None


class handler(BaseHTTPRequestHandler):
    """
    GET /api/weather?location=Berlin
    GET /api/weather?location=New+York
    GET /api/weather?lat=52.52&lon=13.41
    """

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        location = query.get("location", [""])[0]
        lat = query.get("lat", [""])[0]
        lon = query.get("lon", [""])[0]

        if not location and not (lat and lon):
            _json_response(self, 400, {
                "error": "Parameter 'location' oder 'lat'+'lon' erforderlich",
                "usage": "/api/weather?location=Berlin oder /api/weather?lat=52.52&lon=13.41",
            })
            return

        # Zuerst wttr.in (schnell, zuverlässig)
        search_term = location if location else f"{lat},{lon}"
        data = _fetch_wttr(search_term)

        # Fallback Open-Meteo
        if not data:
            data = _fetch_openmeteo(location, lat, lon)

        if not data:
            _json_response(self, 503, {
                "error": "Wetterdaten momentan nicht verfügbar",
                "hint": "Beide Wetter-APIs nicht erreichbar. Bitte später erneut versuchen.",
            })
            return

        _json_response(self, 200, data)
