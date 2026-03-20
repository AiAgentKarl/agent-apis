"""
Crypto-Preis API — Serverless Function für Vercel.
Liefert aktuelle Preise, Marktdaten und 24h-Änderungen für Kryptowährungen.
Nutzt CoinGecko Free API (kein Key nötig, 30 Calls/Min).
"""

from http.server import BaseHTTPRequestHandler
import json
import httpx
from urllib.parse import urlparse, parse_qs


COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Häufige Aliase auf CoinGecko-IDs mappen
TOKEN_ALIASES = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "ada": "cardano",
    "doge": "dogecoin",
    "dot": "polkadot",
    "avax": "avalanche-2",
    "matic": "matic-network",
    "link": "chainlink",
    "uni": "uniswap",
    "atom": "cosmos",
    "ltc": "litecoin",
    "near": "near",
    "apt": "aptos",
    "arb": "arbitrum",
    "op": "optimism",
    "sui": "sui",
    "sei": "sei-network",
    "jup": "jupiter-exchange-solana",
    "bonk": "bonk",
    "wif": "dogwifcoin",
    "pepe": "pepe",
    "shib": "shiba-inu",
    "render": "render-token",
    "fet": "artificial-superintelligence-alliance",
    "inj": "injective-protocol",
    "ton": "the-open-network",
}


def _resolve_token_id(token):
    """Token-Symbol oder Name auf CoinGecko-ID auflösen."""
    token_lower = token.lower().strip()
    # Erst in Aliase schauen
    if token_lower in TOKEN_ALIASES:
        return TOKEN_ALIASES[token_lower]
    # Sonst als CoinGecko-ID direkt verwenden
    return token_lower


def _format_number(value):
    """Große Zahlen lesbar formatieren."""
    if value is None:
        return None
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.2f}K"
    return f"${value:.2f}"


def _json_response(handler, status_code, data):
    """Hilfsfunktion: JSON-Antwort senden."""
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Cache-Control", "public, max-age=60")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, indent=2).encode())


class handler(BaseHTTPRequestHandler):
    """
    GET /api/crypto?token=bitcoin
    GET /api/crypto?token=sol
    GET /api/crypto?token=ethereum&currency=eur
    """

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        token = query.get("token", [""])[0]
        currency = query.get("currency", ["usd"])[0].lower()

        if not token:
            _json_response(self, 400, {
                "error": "Parameter 'token' erforderlich",
                "usage": "/api/crypto?token=bitcoin",
                "examples": [
                    "/api/crypto?token=sol",
                    "/api/crypto?token=eth&currency=eur",
                    "/api/crypto?token=bitcoin",
                ]
            })
            return

        token_id = _resolve_token_id(token)

        try:
            # CoinGecko Marktdaten holen
            response = httpx.get(
                f"{COINGECKO_BASE}/coins/{token_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "market_data": "true",
                    "community_data": "false",
                    "developer_data": "false",
                },
                timeout=8.0,
                headers={"Accept": "application/json"},
            )

            if response.status_code == 404:
                _json_response(self, 404, {
                    "error": f"Token '{token}' nicht gefunden",
                    "hint": "Versuche den vollen CoinGecko-Namen, z.B. 'bitcoin' statt 'btc'"
                })
                return

            if response.status_code == 429:
                _json_response(self, 429, {
                    "error": "Rate Limit erreicht. Bitte warte kurz."
                })
                return

            response.raise_for_status()
            data = response.json()
            market = data.get("market_data", {})

            # Preisdaten extrahieren
            price = market.get("current_price", {}).get(currency)
            if price is None:
                _json_response(self, 400, {
                    "error": f"Währung '{currency}' nicht verfügbar"
                })
                return

            result = {
                "token": data.get("id", token_id),
                "name": data.get("name", ""),
                "symbol": data.get("symbol", "").upper(),
                "price": price,
                "currency": currency.upper(),
                "change_24h_pct": market.get("price_change_percentage_24h"),
                "change_7d_pct": market.get("price_change_percentage_7d"),
                "change_30d_pct": market.get("price_change_percentage_30d"),
                "market_cap": market.get("market_cap", {}).get(currency),
                "market_cap_formatted": _format_number(
                    market.get("market_cap", {}).get(currency)
                ),
                "market_cap_rank": data.get("market_cap_rank"),
                "volume_24h": market.get("total_volume", {}).get(currency),
                "volume_24h_formatted": _format_number(
                    market.get("total_volume", {}).get(currency)
                ),
                "high_24h": market.get("high_24h", {}).get(currency),
                "low_24h": market.get("low_24h", {}).get(currency),
                "ath": market.get("ath", {}).get(currency),
                "ath_change_pct": market.get("ath_change_percentage", {}).get(currency),
                "circulating_supply": market.get("circulating_supply"),
                "total_supply": market.get("total_supply"),
                "max_supply": market.get("max_supply"),
                "last_updated": data.get("last_updated", ""),
            }

            _json_response(self, 200, result)

        except httpx.TimeoutException:
            _json_response(self, 504, {"error": "CoinGecko API Timeout"})
        except httpx.HTTPStatusError as e:
            _json_response(self, 502, {
                "error": f"CoinGecko API Fehler: {e.response.status_code}"
            })
        except Exception as e:
            _json_response(self, 500, {"error": f"Interner Fehler: {str(e)}"})
