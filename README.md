# Agent APIs

Free serverless APIs for AI agents. Deploy on Vercel with zero configuration.

## Endpoints

### Weather API

Get current weather data for any location worldwide. Powered by Open-Meteo (free, no API key).

```
GET /api/weather?location=Berlin
GET /api/weather?location=New+York
GET /api/weather?lat=52.52&lon=13.41
```

**Response:**
```json
{
  "location": "Berlin, Germany",
  "temperature_c": 18.5,
  "feels_like_c": 16.2,
  "humidity_pct": 65,
  "wind_speed_kmh": 12.3,
  "precipitation_mm": 0.0,
  "cloud_cover_pct": 40,
  "condition": "Partly cloudy",
  "timezone": "Europe/Berlin"
}
```

### PII Scanner API

Detect and redact personally identifiable information in text. Supports email, phone, credit card, SSN, IBAN, and IP addresses. No external APIs — pure regex.

```
GET /api/pii?text=Contact+me+at+john@example.com+or+555-123-4567
POST /api/pii  (Body: {"text": "..."})
```

**Response:**
```json
{
  "pii_found": true,
  "pii_count": 2,
  "types_found": ["email", "phone"],
  "redacted_text": "Contact me at [EMAIL] or [PHONE]",
  "findings": [
    {"type": "email", "value_preview": "j***@example.com"},
    {"type": "phone", "value_preview": "***4567"}
  ]
}
```

**Supported PII types:**
- Email addresses
- Phone numbers (international formats)
- Credit cards (Visa, Mastercard, Amex, Discover)
- US Social Security Numbers
- IBANs
- IPv4 addresses

### Crypto Price API

Get real-time cryptocurrency prices, market data, and trends. Powered by CoinGecko (free, no API key).

```
GET /api/crypto?token=bitcoin
GET /api/crypto?token=sol
GET /api/crypto?token=eth&currency=eur
```

**Response:**
```json
{
  "token": "bitcoin",
  "name": "Bitcoin",
  "symbol": "BTC",
  "price": 67543.21,
  "currency": "USD",
  "change_24h_pct": 2.3,
  "change_7d_pct": -1.5,
  "market_cap_formatted": "$1.32T",
  "volume_24h_formatted": "$28.45B",
  "market_cap_rank": 1
}
```

**Supports:** BTC, ETH, SOL, BNB, XRP, ADA, DOGE, DOT, AVAX, LINK, UNI, ATOM, and 100+ more tokens via symbol or CoinGecko ID.

## Deploy

### Vercel (recommended)

1. Fork this repo
2. Import in [Vercel](https://vercel.com)
3. Deploy — done. No environment variables needed.

### Local Development

```bash
pip install httpx
vercel dev
```

## Rate Limits

| API | Source | Limit |
|-----|--------|-------|
| Weather | Open-Meteo | 10,000 req/day (free) |
| PII | Local regex | Unlimited |
| Crypto | CoinGecko | 30 req/min (free) |

## License

MIT
