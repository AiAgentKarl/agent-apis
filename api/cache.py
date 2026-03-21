"""
Shared Context Cache API — Serverless Function fuer Vercel.
Gemeinsamer Cache fuer AI-Agents: Berechnete Ergebnisse teilen,
damit andere Agents sie nicht nochmal berechnen muessen.
Wie ein CDN, aber fuer Agent-Intelligenz. Starker Netzwerkeffekt.
"""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta


# ============================================================
# Pre-seeded Cache-Daten — Realistische Eintraege
# ============================================================

def _now():
    """Aktuelle UTC-Zeit."""
    return datetime.now(timezone.utc)


def _iso(dt):
    """Datetime zu ISO-String."""
    return dt.isoformat()


def _expires(hours=24):
    """Ablaufzeit berechnen."""
    return _now() + timedelta(hours=hours)


# Globaler Cache-Speicher (wird bei Cold Start neu initialisiert)
CACHE_STORE = {}
STATS = {
    "total_hits": 0,
    "total_misses": 0,
    "total_writes": 0,
}


def _seed_cache():
    """Pre-seeded Daten: 30+ realistische Cache-Eintraege."""
    now = _now()
    entries = [
        # --- Wetter (10 Staedte) ---
        {
            "key": "weather_berlin_2026-03-21",
            "value": {"city": "Berlin", "temp_c": 8, "condition": "Cloudy", "humidity": 72, "wind_kmh": 14},
            "tags": ["weather", "berlin", "germany", "europe"],
            "agent_id": "weather-bot",
            "created_at": _iso(now - timedelta(hours=2)),
            "expires_at": _iso(now + timedelta(hours=22)),
            "hit_count": 47,
        },
        {
            "key": "weather_london_2026-03-21",
            "value": {"city": "London", "temp_c": 11, "condition": "Rainy", "humidity": 85, "wind_kmh": 19},
            "tags": ["weather", "london", "uk", "europe"],
            "agent_id": "weather-bot",
            "created_at": _iso(now - timedelta(hours=3)),
            "expires_at": _iso(now + timedelta(hours=21)),
            "hit_count": 63,
        },
        {
            "key": "weather_new-york_2026-03-21",
            "value": {"city": "New York", "temp_c": 14, "condition": "Sunny", "humidity": 55, "wind_kmh": 10},
            "tags": ["weather", "new-york", "usa", "north-america"],
            "agent_id": "weather-bot",
            "created_at": _iso(now - timedelta(hours=1)),
            "expires_at": _iso(now + timedelta(hours=23)),
            "hit_count": 89,
        },
        {
            "key": "weather_tokyo_2026-03-21",
            "value": {"city": "Tokyo", "temp_c": 16, "condition": "Partly Cloudy", "humidity": 60, "wind_kmh": 8},
            "tags": ["weather", "tokyo", "japan", "asia"],
            "agent_id": "weather-bot",
            "created_at": _iso(now - timedelta(hours=4)),
            "expires_at": _iso(now + timedelta(hours=20)),
            "hit_count": 72,
        },
        {
            "key": "weather_sydney_2026-03-21",
            "value": {"city": "Sydney", "temp_c": 24, "condition": "Sunny", "humidity": 50, "wind_kmh": 15},
            "tags": ["weather", "sydney", "australia", "oceania"],
            "agent_id": "weather-bot",
            "created_at": _iso(now - timedelta(hours=5)),
            "expires_at": _iso(now + timedelta(hours=19)),
            "hit_count": 34,
        },
        {
            "key": "weather_paris_2026-03-21",
            "value": {"city": "Paris", "temp_c": 12, "condition": "Overcast", "humidity": 68, "wind_kmh": 11},
            "tags": ["weather", "paris", "france", "europe"],
            "agent_id": "weather-bot",
            "created_at": _iso(now - timedelta(hours=2)),
            "expires_at": _iso(now + timedelta(hours=22)),
            "hit_count": 51,
        },
        {
            "key": "weather_dubai_2026-03-21",
            "value": {"city": "Dubai", "temp_c": 32, "condition": "Sunny", "humidity": 40, "wind_kmh": 6},
            "tags": ["weather", "dubai", "uae", "middle-east"],
            "agent_id": "weather-bot",
            "created_at": _iso(now - timedelta(hours=3)),
            "expires_at": _iso(now + timedelta(hours=21)),
            "hit_count": 28,
        },
        {
            "key": "weather_singapore_2026-03-21",
            "value": {"city": "Singapore", "temp_c": 30, "condition": "Thunderstorm", "humidity": 88, "wind_kmh": 12},
            "tags": ["weather", "singapore", "asia"],
            "agent_id": "weather-bot",
            "created_at": _iso(now - timedelta(hours=1)),
            "expires_at": _iso(now + timedelta(hours=23)),
            "hit_count": 22,
        },
        {
            "key": "weather_toronto_2026-03-21",
            "value": {"city": "Toronto", "temp_c": 5, "condition": "Snow", "humidity": 78, "wind_kmh": 20},
            "tags": ["weather", "toronto", "canada", "north-america"],
            "agent_id": "weather-bot",
            "created_at": _iso(now - timedelta(hours=2)),
            "expires_at": _iso(now + timedelta(hours=22)),
            "hit_count": 41,
        },
        {
            "key": "weather_sao-paulo_2026-03-21",
            "value": {"city": "Sao Paulo", "temp_c": 27, "condition": "Partly Cloudy", "humidity": 65, "wind_kmh": 9},
            "tags": ["weather", "sao-paulo", "brazil", "south-america"],
            "agent_id": "weather-bot",
            "created_at": _iso(now - timedelta(hours=4)),
            "expires_at": _iso(now + timedelta(hours=20)),
            "hit_count": 19,
        },
        # --- Crypto Preise (5 Tokens) ---
        {
            "key": "crypto_bitcoin_2026-03-21",
            "value": {"token": "Bitcoin", "symbol": "BTC", "price_usd": 87432.50, "change_24h": 2.3, "market_cap_b": 1720},
            "tags": ["crypto", "bitcoin", "btc", "price"],
            "agent_id": "crypto-tracker",
            "created_at": _iso(now - timedelta(minutes=15)),
            "expires_at": _iso(now + timedelta(hours=1)),
            "hit_count": 156,
        },
        {
            "key": "crypto_ethereum_2026-03-21",
            "value": {"token": "Ethereum", "symbol": "ETH", "price_usd": 4125.80, "change_24h": -1.1, "market_cap_b": 496},
            "tags": ["crypto", "ethereum", "eth", "price"],
            "agent_id": "crypto-tracker",
            "created_at": _iso(now - timedelta(minutes=15)),
            "expires_at": _iso(now + timedelta(hours=1)),
            "hit_count": 134,
        },
        {
            "key": "crypto_solana_2026-03-21",
            "value": {"token": "Solana", "symbol": "SOL", "price_usd": 178.45, "change_24h": 5.7, "market_cap_b": 82},
            "tags": ["crypto", "solana", "sol", "price"],
            "agent_id": "crypto-tracker",
            "created_at": _iso(now - timedelta(minutes=15)),
            "expires_at": _iso(now + timedelta(hours=1)),
            "hit_count": 98,
        },
        {
            "key": "crypto_cardano_2026-03-21",
            "value": {"token": "Cardano", "symbol": "ADA", "price_usd": 0.72, "change_24h": -0.5, "market_cap_b": 25},
            "tags": ["crypto", "cardano", "ada", "price"],
            "agent_id": "crypto-tracker",
            "created_at": _iso(now - timedelta(minutes=15)),
            "expires_at": _iso(now + timedelta(hours=1)),
            "hit_count": 45,
        },
        {
            "key": "crypto_chainlink_2026-03-21",
            "value": {"token": "Chainlink", "symbol": "LINK", "price_usd": 18.90, "change_24h": 3.2, "market_cap_b": 12},
            "tags": ["crypto", "chainlink", "link", "price", "oracle"],
            "agent_id": "crypto-tracker",
            "created_at": _iso(now - timedelta(minutes=15)),
            "expires_at": _iso(now + timedelta(hours=1)),
            "hit_count": 37,
        },
        # --- Compliance-Checks (5 Eintraege) ---
        {
            "key": "compliance_gdpr_email-collection",
            "value": {
                "action": "Collect user emails for newsletter",
                "gdpr_compliant": True,
                "requirements": ["Explicit consent required", "Unsubscribe option mandatory", "Privacy policy link"],
                "risk_level": "medium",
            },
            "tags": ["compliance", "gdpr", "email", "newsletter", "privacy"],
            "agent_id": "compliance-checker",
            "created_at": _iso(now - timedelta(hours=12)),
            "expires_at": _iso(now + timedelta(hours=168)),
            "hit_count": 83,
        },
        {
            "key": "compliance_gdpr_cookie-tracking",
            "value": {
                "action": "Third-party cookie tracking",
                "gdpr_compliant": False,
                "requirements": ["Explicit opt-in consent", "Cookie banner required", "No pre-checked boxes"],
                "risk_level": "high",
            },
            "tags": ["compliance", "gdpr", "cookies", "tracking", "privacy"],
            "agent_id": "compliance-checker",
            "created_at": _iso(now - timedelta(hours=6)),
            "expires_at": _iso(now + timedelta(hours=168)),
            "hit_count": 112,
        },
        {
            "key": "compliance_ai-act_chatbot-disclosure",
            "value": {
                "action": "Deploy AI chatbot without disclosure",
                "ai_act_compliant": False,
                "requirements": ["Must disclose AI interaction", "Transparency obligation under Art. 52", "User right to human agent"],
                "risk_level": "high",
            },
            "tags": ["compliance", "ai-act", "chatbot", "transparency", "eu"],
            "agent_id": "compliance-checker",
            "created_at": _iso(now - timedelta(hours=8)),
            "expires_at": _iso(now + timedelta(hours=168)),
            "hit_count": 67,
        },
        {
            "key": "compliance_gdpr_data-retention",
            "value": {
                "action": "Store user data indefinitely",
                "gdpr_compliant": False,
                "requirements": ["Define retention period", "Data minimization principle", "Right to erasure"],
                "risk_level": "critical",
            },
            "tags": ["compliance", "gdpr", "data-retention", "storage", "privacy"],
            "agent_id": "compliance-checker",
            "created_at": _iso(now - timedelta(hours=10)),
            "expires_at": _iso(now + timedelta(hours=168)),
            "hit_count": 91,
        },
        {
            "key": "compliance_ai-act_risk-assessment",
            "value": {
                "action": "Deploy high-risk AI system in healthcare",
                "ai_act_compliant": "conditional",
                "requirements": ["Conformity assessment required", "Register in EU database", "Human oversight mandatory", "Quality management system"],
                "risk_level": "high",
            },
            "tags": ["compliance", "ai-act", "healthcare", "high-risk", "eu"],
            "agent_id": "compliance-checker",
            "created_at": _iso(now - timedelta(hours=5)),
            "expires_at": _iso(now + timedelta(hours=168)),
            "hit_count": 58,
        },
        # --- Research-Zusammenfassungen (5 Eintraege) ---
        {
            "key": "research_transformer-architecture_overview",
            "value": {
                "topic": "Transformer Architecture",
                "summary": "Self-attention mechanism enabling parallel processing of sequences. Key components: multi-head attention, positional encoding, feed-forward networks. Foundation of GPT, BERT, and modern LLMs.",
                "key_papers": ["Attention Is All You Need (2017)", "BERT (2018)", "GPT-3 (2020)"],
                "last_updated": "2026-03-20",
            },
            "tags": ["research", "transformer", "architecture", "nlp", "deep-learning"],
            "agent_id": "research-agent",
            "created_at": _iso(now - timedelta(hours=18)),
            "expires_at": _iso(now + timedelta(hours=72)),
            "hit_count": 124,
        },
        {
            "key": "research_rag-best-practices_2026",
            "value": {
                "topic": "RAG Best Practices 2026",
                "summary": "Retrieval-Augmented Generation combines vector search with LLM generation. Best practices: chunk size 512-1024 tokens, hybrid search (BM25 + vector), reranking with cross-encoders, citation tracking.",
                "key_techniques": ["Hybrid search", "Cross-encoder reranking", "Recursive retrieval", "Graph RAG"],
                "last_updated": "2026-03-15",
            },
            "tags": ["research", "rag", "retrieval", "llm", "best-practices"],
            "agent_id": "research-agent",
            "created_at": _iso(now - timedelta(hours=24)),
            "expires_at": _iso(now + timedelta(hours=48)),
            "hit_count": 203,
        },
        {
            "key": "research_mcp-protocol_overview",
            "value": {
                "topic": "Model Context Protocol (MCP)",
                "summary": "Open protocol by Anthropic for AI-tool integration. Enables agents to discover and use external tools via standardized interface. 97M+ monthly SDK downloads as of Feb 2026.",
                "key_features": ["Tool discovery", "Stdio/HTTP transport", "OAuth 2.1 auth", "Server Cards"],
                "adoption": "Anthropic, OpenAI, Google, Microsoft, Amazon",
                "last_updated": "2026-03-20",
            },
            "tags": ["research", "mcp", "protocol", "agents", "tools"],
            "agent_id": "research-agent",
            "created_at": _iso(now - timedelta(hours=6)),
            "expires_at": _iso(now + timedelta(hours=72)),
            "hit_count": 178,
        },
        {
            "key": "research_agent-architectures_comparison",
            "value": {
                "topic": "AI Agent Architectures Comparison",
                "summary": "Major patterns: ReAct (reasoning + acting), Plan-and-Execute, Multi-Agent Systems, Tool-Augmented LLMs. ReAct most popular for single-agent tasks. Multi-agent best for complex workflows.",
                "frameworks": ["LangChain", "CrewAI", "AutoGen", "Claude Code"],
                "last_updated": "2026-03-18",
            },
            "tags": ["research", "agents", "architecture", "comparison", "langchain"],
            "agent_id": "research-agent",
            "created_at": _iso(now - timedelta(hours=30)),
            "expires_at": _iso(now + timedelta(hours=42)),
            "hit_count": 145,
        },
        {
            "key": "research_vector-databases_benchmark",
            "value": {
                "topic": "Vector Database Benchmark 2026",
                "summary": "Performance comparison of major vector DBs. Qdrant leads in recall@10, Weaviate fastest for hybrid search, Pinecone best managed service, Chroma best for prototyping.",
                "databases": {
                    "Qdrant": {"recall": 0.98, "qps": 5200, "type": "self-hosted/cloud"},
                    "Weaviate": {"recall": 0.96, "qps": 4800, "type": "self-hosted/cloud"},
                    "Pinecone": {"recall": 0.95, "qps": 4500, "type": "managed"},
                    "Chroma": {"recall": 0.93, "qps": 3200, "type": "embedded"},
                },
                "last_updated": "2026-03-10",
            },
            "tags": ["research", "vector-db", "benchmark", "rag", "databases"],
            "agent_id": "research-agent",
            "created_at": _iso(now - timedelta(hours=48)),
            "expires_at": _iso(now + timedelta(hours=120)),
            "hit_count": 167,
        },
        # --- API-Referenz (3 Eintraege) ---
        {
            "key": "api-ref_openai_gpt4o-pricing",
            "value": {
                "model": "GPT-4o",
                "provider": "OpenAI",
                "input_per_1m": 2.50,
                "output_per_1m": 10.00,
                "context_window": 128000,
                "last_verified": "2026-03-20",
            },
            "tags": ["api", "openai", "gpt-4o", "pricing", "llm"],
            "agent_id": "cost-router",
            "created_at": _iso(now - timedelta(hours=12)),
            "expires_at": _iso(now + timedelta(hours=168)),
            "hit_count": 94,
        },
        {
            "key": "api-ref_anthropic_claude-opus4-pricing",
            "value": {
                "model": "Claude Opus 4",
                "provider": "Anthropic",
                "input_per_1m": 15.00,
                "output_per_1m": 75.00,
                "context_window": 200000,
                "last_verified": "2026-03-20",
            },
            "tags": ["api", "anthropic", "claude", "opus", "pricing", "llm"],
            "agent_id": "cost-router",
            "created_at": _iso(now - timedelta(hours=12)),
            "expires_at": _iso(now + timedelta(hours=168)),
            "hit_count": 76,
        },
        {
            "key": "api-ref_google_gemini-flash-pricing",
            "value": {
                "model": "Gemini 2.0 Flash",
                "provider": "Google",
                "input_per_1m": 0.10,
                "output_per_1m": 0.40,
                "context_window": 1000000,
                "last_verified": "2026-03-20",
            },
            "tags": ["api", "google", "gemini", "pricing", "llm"],
            "agent_id": "cost-router",
            "created_at": _iso(now - timedelta(hours=12)),
            "expires_at": _iso(now + timedelta(hours=168)),
            "hit_count": 61,
        },
        # --- Geo/Standort (2 Eintraege) ---
        {
            "key": "geo_berlin_coordinates",
            "value": {"city": "Berlin", "lat": 52.52, "lon": 13.405, "country": "Germany", "timezone": "Europe/Berlin", "population": 3748148},
            "tags": ["geo", "berlin", "germany", "coordinates"],
            "agent_id": "geo-agent",
            "created_at": _iso(now - timedelta(hours=72)),
            "expires_at": _iso(now + timedelta(hours=720)),
            "hit_count": 210,
        },
        {
            "key": "geo_new-york_coordinates",
            "value": {"city": "New York", "lat": 40.7128, "lon": -74.006, "country": "USA", "timezone": "America/New_York", "population": 8336817},
            "tags": ["geo", "new-york", "usa", "coordinates"],
            "agent_id": "geo-agent",
            "created_at": _iso(now - timedelta(hours=72)),
            "expires_at": _iso(now + timedelta(hours=720)),
            "hit_count": 185,
        },
        # --- Conversion/Utilities (2 Eintraege) ---
        {
            "key": "conversion_eur-usd_2026-03-21",
            "value": {"from": "EUR", "to": "USD", "rate": 1.0845, "date": "2026-03-21"},
            "tags": ["conversion", "currency", "eur", "usd", "forex"],
            "agent_id": "finance-bot",
            "created_at": _iso(now - timedelta(hours=1)),
            "expires_at": _iso(now + timedelta(hours=4)),
            "hit_count": 142,
        },
        {
            "key": "conversion_gbp-usd_2026-03-21",
            "value": {"from": "GBP", "to": "USD", "rate": 1.2635, "date": "2026-03-21"},
            "tags": ["conversion", "currency", "gbp", "usd", "forex"],
            "agent_id": "finance-bot",
            "created_at": _iso(now - timedelta(hours=1)),
            "expires_at": _iso(now + timedelta(hours=4)),
            "hit_count": 88,
        },
    ]

    for entry in entries:
        CACHE_STORE[entry["key"]] = entry


# Beim Import/Cold Start sofort seeden
_seed_cache()


# ============================================================
# Hilfsfunktionen
# ============================================================

def _json_response(handler, status_code, data):
    """JSON-Antwort senden mit CORS-Headern."""
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Cache-Control", "no-cache")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, indent=2).encode())


def _get_cached(key):
    """Cache-Eintrag abrufen und hit_count erhoehen."""
    if key in CACHE_STORE:
        entry = CACHE_STORE[key]
        entry["hit_count"] += 1
        STATS["total_hits"] += 1
        return entry
    STATS["total_misses"] += 1
    return None


def _search_cache(query):
    """Cache nach Keywords durchsuchen (Keys und Tags)."""
    query_lower = query.lower().replace("+", " ")
    terms = query_lower.split()
    results = []

    for key, entry in CACHE_STORE.items():
        # Suche in Key und Tags
        searchable = key.lower() + " " + " ".join(entry.get("tags", []))
        score = sum(1 for term in terms if term in searchable)
        if score > 0:
            results.append((score, entry))

    # Nach Relevanz sortieren (hoechster Score zuerst)
    results.sort(key=lambda x: (-x[0], -x[1]["hit_count"]))
    return [r[1] for r in results]


def _cache_stats():
    """Cache-Statistiken berechnen."""
    total_entries = len(CACHE_STORE)
    total_hits = STATS["total_hits"]
    total_misses = STATS["total_misses"]
    total_requests = total_hits + total_misses

    # Top-Queries nach Hits
    sorted_entries = sorted(CACHE_STORE.values(), key=lambda e: e["hit_count"], reverse=True)
    top_queries = [
        {"key": e["key"], "hit_count": e["hit_count"], "agent_id": e["agent_id"]}
        for e in sorted_entries[:10]
    ]

    # Aktivste Agents
    agent_counts = {}
    agent_hits = {}
    for entry in CACHE_STORE.values():
        aid = entry["agent_id"]
        agent_counts[aid] = agent_counts.get(aid, 0) + 1
        agent_hits[aid] = agent_hits.get(aid, 0) + entry["hit_count"]
    most_active = sorted(
        [{"agent_id": k, "entries": v, "total_hits": agent_hits[k]} for k, v in agent_counts.items()],
        key=lambda x: x["total_hits"],
        reverse=True,
    )

    # Eintraege nach Tag
    tag_counts = {}
    for entry in CACHE_STORE.values():
        for tag in entry.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    entries_by_tag = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))

    return {
        "total_entries": total_entries,
        "total_hits": total_hits,
        "total_misses": total_misses,
        "cache_hit_rate": f"{(total_hits / total_requests * 100):.1f}%" if total_requests > 0 else "0%",
        "total_writes": STATS["total_writes"],
        "top_queries": top_queries,
        "most_active_agents": most_active,
        "entries_by_tag": entries_by_tag,
    }


def _format_entry(entry, include_value=True):
    """Cache-Eintrag fuer die Ausgabe formatieren."""
    result = {
        "key": entry["key"],
        "tags": entry["tags"],
        "agent_id": entry["agent_id"],
        "created_at": entry["created_at"],
        "expires_at": entry["expires_at"],
        "hit_count": entry["hit_count"],
    }
    if include_value:
        result["value"] = entry["value"]
    return result


# ============================================================
# HTTP Handler
# ============================================================

class handler(BaseHTTPRequestHandler):
    """
    Shared Context Cache — CDN fuer Agent-Intelligenz.

    GET  /api/cache?key=weather_berlin_2026-03-21  — Cached Wert abrufen
    GET  /api/cache?search=weather+berlin           — Cache durchsuchen
    GET  /api/cache?stats=true                      — Cache-Statistiken
    POST /api/cache                                 — Neuen Eintrag speichern
         Body: {"key": "...", "value": {...}, "ttl_hours": 24, "tags": [...], "agent_id": "..."}
    """

    def do_OPTIONS(self):
        """CORS Preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        query_params = parse_qs(urlparse(self.path).query)

        key = query_params.get("key", [""])[0].strip()
        search = query_params.get("search", [""])[0].strip()
        stats = query_params.get("stats", [""])[0].strip().lower()

        # --- Statistiken ---
        if stats == "true":
            _json_response(self, 200, {
                "source": "agent-context-cache",
                "description": "Shared cache for AI agents — like a CDN for agent intelligence",
                "stats": _cache_stats(),
                "network_effect": "More agents caching = more cache hits = faster for everyone",
            })
            return

        # --- Key-Lookup ---
        if key:
            entry = _get_cached(key)
            if entry:
                _json_response(self, 200, {
                    "source": "agent-context-cache",
                    "cache_hit": True,
                    "entry": _format_entry(entry),
                })
            else:
                _json_response(self, 404, {
                    "source": "agent-context-cache",
                    "cache_hit": False,
                    "key": key,
                    "message": "Key nicht im Cache gefunden",
                    "suggestion": "Nutze ?search= um aehnliche Eintraege zu finden",
                })
            return

        # --- Suche ---
        if search:
            results = _search_cache(search)
            _json_response(self, 200, {
                "source": "agent-context-cache",
                "query": search.replace("+", " "),
                "results_count": len(results),
                "results": [_format_entry(r) for r in results[:20]],
            })
            return

        # --- Kein Parameter: Usage-Info ---
        _json_response(self, 200, {
            "service": "Shared Context Cache API",
            "description": "CDN for agent intelligence — agents share computed results so others skip recomputation",
            "network_effect": "More agents caching = more cache hits = faster for everyone",
            "version": "1.0.0",
            "endpoints": {
                "GET /api/cache?key=<key>": "Cached Ergebnis abrufen (erhoet hit_count)",
                "GET /api/cache?search=<query>": "Cache nach Keywords durchsuchen (Keys + Tags)",
                "GET /api/cache?stats=true": "Cache-Statistiken: Hits, Misses, Top-Queries, Agents",
                "POST /api/cache": "Neuen Eintrag speichern",
            },
            "post_body": {
                "key": "Eindeutiger Schluessel (z.B. weather_berlin_2026-03-21)",
                "value": "Beliebiges JSON-Objekt mit dem gecachten Ergebnis",
                "ttl_hours": "Time-to-live in Stunden (Standard: 24)",
                "tags": "Liste von Tags fuer die Suche (z.B. ['weather', 'berlin'])",
                "agent_id": "ID des Agents der den Eintrag erstellt",
            },
            "examples": [
                "/api/cache?key=weather_berlin_2026-03-21",
                "/api/cache?search=crypto+price",
                "/api/cache?search=compliance+gdpr",
                "/api/cache?stats=true",
            ],
            "current_entries": len(CACHE_STORE),
        })

    def do_POST(self):
        """Neuen Cache-Eintrag speichern."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                _json_response(self, 400, {
                    "error": "Leerer Request-Body",
                    "required_fields": ["key", "value"],
                    "optional_fields": ["ttl_hours (Standard: 24)", "tags", "agent_id"],
                })
                return

            body = json.loads(self.rfile.read(content_length))

            # Pflichtfelder pruefen
            key = body.get("key", "").strip()
            value = body.get("value")

            if not key:
                _json_response(self, 400, {"error": "Feld 'key' ist erforderlich"})
                return
            if value is None:
                _json_response(self, 400, {"error": "Feld 'value' ist erforderlich"})
                return

            # Optionale Felder
            ttl_hours = body.get("ttl_hours", 24)
            tags = body.get("tags", [])
            agent_id = body.get("agent_id", "anonymous")

            # TTL validieren (min 1 Stunde, max 720 Stunden = 30 Tage)
            try:
                ttl_hours = max(1, min(720, int(ttl_hours)))
            except (ValueError, TypeError):
                ttl_hours = 24

            # Eintrag erstellen
            now = _now()
            is_update = key in CACHE_STORE
            entry = {
                "key": key,
                "value": value,
                "tags": tags if isinstance(tags, list) else [tags],
                "agent_id": agent_id,
                "created_at": _iso(now),
                "expires_at": _iso(now + timedelta(hours=ttl_hours)),
                "hit_count": CACHE_STORE[key]["hit_count"] if is_update else 0,
            }

            CACHE_STORE[key] = entry
            STATS["total_writes"] += 1

            _json_response(self, 201 if not is_update else 200, {
                "source": "agent-context-cache",
                "status": "updated" if is_update else "created",
                "entry": _format_entry(entry),
                "ttl_hours": ttl_hours,
                "total_entries": len(CACHE_STORE),
                "message": f"Eintrag '{key}' {'aktualisiert' if is_update else 'gespeichert'} — jetzt fuer alle Agents verfuegbar",
            })

        except json.JSONDecodeError:
            _json_response(self, 400, {
                "error": "Ungueltiges JSON im Request-Body",
                "expected_format": {
                    "key": "weather_berlin_2026-03-21",
                    "value": {"temp": 8, "condition": "cloudy"},
                    "ttl_hours": 24,
                    "tags": ["weather", "berlin"],
                    "agent_id": "weather-bot",
                },
            })
        except Exception as e:
            _json_response(self, 500, {"error": f"Interner Fehler: {str(e)}"})
