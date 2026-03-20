"""
Wetter-API — Serverless Function für Vercel.
Liefert aktuelle Wetterdaten für jeden Ort weltweit.
Nutzt Open-Meteo (kostenlos, kein API-Key nötig).
"""

from http.server import BaseHTTPRequestHandler
import json
import httpx
from urllib.parse import urlparse, parse_qs


# WMO-Wettercodes auf lesbare Beschreibungen mappen
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# Open-Meteo API-Endpunkte
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _json_response(handler, status_code, data):
    """Hilfsfunktion: JSON-Antwort senden."""
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Cache-Control", "public, max-age=300")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, indent=2).encode())


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

        # Entweder location oder lat+lon müssen angegeben sein
        if not location and not (lat and lon):
            _json_response(self, 400, {
                "error": "Parameter 'location' oder 'lat'+'lon' erforderlich",
                "usage": "/api/weather?location=Berlin oder /api/weather?lat=52.52&lon=13.41"
            })
            return

        try:
            # Koordinaten ermitteln
            if location:
                geo = httpx.get(
                    GEOCODING_URL,
                    params={"name": location, "count": 1, "language": "en"},
                    timeout=5.0
                ).json()

                if not geo.get("results"):
                    _json_response(self, 404, {
                        "error": f"Ort '{location}' nicht gefunden"
                    })
                    return

                result = geo["results"][0]
                lat = result["latitude"]
                lon = result["longitude"]
                name = result.get("name", location)
                country = result.get("country", "")
                admin1 = result.get("admin1", "")
            else:
                lat = float(lat)
                lon = float(lon)
                name = f"{lat}, {lon}"
                country = ""
                admin1 = ""

            # Wetterdaten holen
            weather = httpx.get(
                FORECAST_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": ",".join([
                        "temperature_2m",
                        "apparent_temperature",
                        "relative_humidity_2m",
                        "precipitation",
                        "weather_code",
                        "wind_speed_10m",
                        "wind_direction_10m",
                        "wind_gusts_10m",
                        "cloud_cover",
                        "surface_pressure",
                        "uv_index",
                        "is_day",
                    ]),
                    "timezone": "auto",
                },
                timeout=5.0
            ).json()

            current = weather.get("current", {})
            weather_code = current.get("weather_code", 0)

            # Standort-String zusammenbauen
            location_parts = [name]
            if admin1 and admin1 != name:
                location_parts.append(admin1)
            if country:
                location_parts.append(country)

            response_data = {
                "location": ", ".join(location_parts),
                "latitude": lat,
                "longitude": lon,
                "temperature_c": current.get("temperature_2m"),
                "feels_like_c": current.get("apparent_temperature"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "wind_speed_kmh": current.get("wind_speed_10m"),
                "wind_gusts_kmh": current.get("wind_gusts_10m"),
                "wind_direction_deg": current.get("wind_direction_10m"),
                "precipitation_mm": current.get("precipitation"),
                "cloud_cover_pct": current.get("cloud_cover"),
                "pressure_hpa": current.get("surface_pressure"),
                "uv_index": current.get("uv_index"),
                "is_day": bool(current.get("is_day", 1)),
                "condition": WMO_CODES.get(weather_code, "Unknown"),
                "weather_code": weather_code,
                "timezone": weather.get("timezone", ""),
            }

            _json_response(self, 200, response_data)

        except httpx.TimeoutException:
            _json_response(self, 504, {"error": "Upstream-API Timeout"})
        except Exception as e:
            _json_response(self, 500, {"error": f"Interner Fehler: {str(e)}"})
