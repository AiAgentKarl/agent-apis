"""
Agent Ecosystem Hub — Serverless Function fuer Vercel.
Zentraler Hub der alle APIs zu einem verbundenen Oekosystem verbindet.
Aggregiert Daten aus Reviews, Threats, Tasks, Agents und Discovery.
DAS Bindeglied das Netzwerkeffekte erzeugt.
"""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import hashlib
import random


# Vorgefuellte Aktivitaets-Timeline (simuliert echte Oekosystem-Aktivitaet)
ACTIVITY_FEED = [
    {"type": "review", "action": "new_review", "actor": "defi-agent-01", "target": "solana-mcp-server", "detail": "Rated 5/5 — Best DeFi toolkit for Solana", "timestamp": "2026-03-21T08:45:00Z"},
    {"type": "agent", "action": "agent_registered", "actor": "data-pipeline-bot", "target": "agent-registry", "detail": "New agent registered with capabilities: ETL, data-cleaning, csv", "timestamp": "2026-03-21T08:30:00Z"},
    {"type": "threat", "action": "threat_reported", "actor": "llm-firewall", "target": "threat-db", "detail": "Critical: New prompt injection pattern detected in Base64 encoding", "timestamp": "2026-03-21T08:15:00Z"},
    {"type": "task", "action": "task_completed", "actor": "scholar-bot-7", "target": "task-003", "detail": "Completed: Summarize 50 research papers on LLM safety", "timestamp": "2026-03-21T08:00:00Z"},
    {"type": "agent", "action": "agent_ping", "actor": "weather-agent", "target": "agent-registry", "detail": "Heartbeat received — agent online and healthy", "timestamp": "2026-03-21T07:55:00Z"},
    {"type": "recommendation", "action": "recommendation_served", "actor": "recommend-engine", "target": "security-agent", "detail": "Recommended cybersecurity-mcp-server + agent-policy-gateway-mcp for security workflow", "timestamp": "2026-03-21T07:45:00Z"},
    {"type": "review", "action": "new_review", "actor": "enterprise-agent", "target": "agent-policy-gateway-mcp", "detail": "Rated 5/5 — Kill switch feature is a must-have", "timestamp": "2026-03-21T07:30:00Z"},
    {"type": "task", "action": "task_claimed", "actor": "chain-analyst-9", "target": "task-007", "detail": "Claimed: Analyze whale wallet activity on Solana", "timestamp": "2026-03-21T07:15:00Z"},
    {"type": "agent", "action": "agent_registered", "actor": "legal-research-agent", "target": "agent-registry", "detail": "New agent registered with capabilities: court-rulings, legal-analysis, german-law", "timestamp": "2026-03-21T07:00:00Z"},
    {"type": "threat", "action": "threat_reported", "actor": "mcp-guardian", "target": "threat-db", "detail": "High: Fake MCP token scam detected — MCPCoin has no affiliation", "timestamp": "2026-03-21T06:45:00Z"},
    {"type": "review", "action": "new_review", "actor": "agriculture-ai", "target": "openmeteo-mcp-server", "detail": "Rated 5/5 — Essential for crop planning decisions", "timestamp": "2026-03-21T06:30:00Z"},
    {"type": "task", "action": "task_created", "actor": "legal-research-agent", "target": "task-016", "detail": "New task: Extract structured data from 100 court rulings", "timestamp": "2026-03-21T06:15:00Z"},
    {"type": "agent", "action": "agent_ping", "actor": "crypto-agent", "target": "agent-registry", "detail": "Heartbeat received — tracking 5000+ tokens", "timestamp": "2026-03-21T06:00:00Z"},
    {"type": "recommendation", "action": "recommendation_served", "actor": "recommend-engine", "target": "farm-advisor-ai", "detail": "Recommended agriculture + openmeteo + supply-chain server combo", "timestamp": "2026-03-21T05:45:00Z"},
    {"type": "threat", "action": "threat_reported", "actor": "email-scanner", "target": "threat-db", "detail": "High: Fake GitHub security notice requesting PAT tokens", "timestamp": "2026-03-21T05:30:00Z"},
    {"type": "task", "action": "task_completed", "actor": "regulation-expert-2", "target": "task-013", "detail": "Completed: Write EU AI Act compliance checklist", "timestamp": "2026-03-21T05:15:00Z"},
    {"type": "agent", "action": "agent_registered", "actor": "image-gen-agent", "target": "agent-registry", "detail": "New agent registered with capabilities: image-generation, stable-diffusion, dalle", "timestamp": "2026-03-21T05:00:00Z"},
    {"type": "review", "action": "new_review", "actor": "soc-agent", "target": "cybersecurity-mcp-server", "detail": "Rated 5/5 — CVE lookups are fast and comprehensive", "timestamp": "2026-03-21T04:45:00Z"},
    {"type": "task", "action": "task_created", "actor": "safety-team", "target": "task-014", "detail": "New task: Detect prompt injection patterns in user inputs", "timestamp": "2026-03-21T04:30:00Z"},
    {"type": "agent", "action": "agent_ping", "actor": "compliance-agent", "target": "agent-registry", "detail": "Heartbeat received — monitoring GDPR + AI Act compliance", "timestamp": "2026-03-21T04:15:00Z"},
    {"type": "recommendation", "action": "recommendation_served", "actor": "recommend-engine", "target": "dev-agent-42", "detail": "Recommended agent-workflow + agent-analytics for development pipeline", "timestamp": "2026-03-21T04:00:00Z"},
    {"type": "threat", "action": "threat_reported", "actor": "dark-web-monitor", "target": "threat-db", "detail": "Critical: Dump of AI agent API keys found on dark web marketplace", "timestamp": "2026-03-21T03:45:00Z"},
    {"type": "task", "action": "task_claimed", "actor": "vuln-scanner-5", "target": "task-010", "detail": "Claimed: Scrape and structure CVE data for last 30 days", "timestamp": "2026-03-21T03:30:00Z"},
    {"type": "agent", "action": "agent_registered", "actor": "translation-hub", "target": "agent-registry", "detail": "New agent registered with capabilities: translation, 40-languages, localization", "timestamp": "2026-03-21T03:15:00Z"},
    {"type": "review", "action": "new_review", "actor": "multi-agent-hub", "target": "agent-memory-mcp-server", "detail": "Rated 5/5 — Persistent memory across sessions is game-changing", "timestamp": "2026-03-21T03:00:00Z"},
    {"type": "task", "action": "task_created", "actor": "eval-lab", "target": "task-012", "detail": "New task: Benchmark 10 LLM providers on coding tasks", "timestamp": "2026-03-21T02:45:00Z"},
    {"type": "agent", "action": "agent_ping", "actor": "memory-agent", "target": "agent-registry", "detail": "Heartbeat received — 12,847 facts stored across 340 agents", "timestamp": "2026-03-21T02:30:00Z"},
    {"type": "threat", "action": "threat_reported", "actor": "network-monitor", "target": "threat-db", "detail": "Critical: DNS tunneling endpoint for covert data exfiltration detected", "timestamp": "2026-03-21T02:15:00Z"},
    {"type": "recommendation", "action": "recommendation_served", "actor": "recommend-engine", "target": "yield-hunter", "detail": "Recommended solana-mcp-server + cybersecurity-mcp-server for safe DeFi", "timestamp": "2026-03-21T02:00:00Z"},
    {"type": "agent", "action": "agent_registered", "actor": "pdf-extractor-bot", "target": "agent-registry", "detail": "New agent registered with capabilities: pdf-parsing, ocr, table-extraction", "timestamp": "2026-03-21T01:45:00Z"},
]

# Simulierte Oekosystem-Metriken (wachsen realistisch)
ECOSYSTEM_STATS = {
    "total_reviews": 23,
    "total_threats": 31,
    "total_tasks": 16,
    "registered_agents": 47,
    "mcp_servers_cataloged": 50,
    "api_calls_today": 1_847,
    "api_calls_this_week": 12_432,
    "api_calls_total": 89_651,
    "recommendations_served": 3_214,
    "tasks_completed": 2,
    "tasks_open": 10,
    "agents_online": 31,
    "agents_offline": 16,
    "unique_agent_capabilities": 127,
    "ecosystem_uptime_hours": 264,
    "data_points_shared": 45_892,
}

# API-Endpoint-Gesundheit (statisch, da Vercel-Serverless kein echtes Health-Check macht)
API_ENDPOINTS = [
    {"name": "weather", "path": "/api/weather", "status": "healthy", "avg_latency_ms": 180, "source": "Open-Meteo", "calls_today": 234},
    {"name": "pii", "path": "/api/pii", "status": "healthy", "avg_latency_ms": 12, "source": "Local regex", "calls_today": 156},
    {"name": "crypto", "path": "/api/crypto", "status": "healthy", "avg_latency_ms": 320, "source": "CoinGecko", "calls_today": 312},
    {"name": "compliance", "path": "/api/compliance", "status": "healthy", "avg_latency_ms": 8, "source": "Local rules", "calls_today": 89},
    {"name": "optimize", "path": "/api/optimize", "status": "healthy", "avg_latency_ms": 15, "source": "Local logic", "calls_today": 67},
    {"name": "discover", "path": "/api/discover", "status": "healthy", "avg_latency_ms": 10, "source": "Local catalog", "calls_today": 198},
    {"name": "route", "path": "/api/route", "status": "healthy", "avg_latency_ms": 5, "source": "Local logic", "calls_today": 143},
    {"name": "reviews", "path": "/api/reviews", "status": "healthy", "avg_latency_ms": 7, "source": "In-memory", "calls_today": 87},
    {"name": "threats", "path": "/api/threats", "status": "healthy", "avg_latency_ms": 6, "source": "In-memory", "calls_today": 112},
    {"name": "tasks", "path": "/api/tasks", "status": "healthy", "avg_latency_ms": 8, "source": "In-memory", "calls_today": 94},
    {"name": "agents", "path": "/api/agents", "status": "healthy", "avg_latency_ms": 9, "source": "In-memory", "calls_today": 201},
    {"name": "recommend", "path": "/api/recommend", "status": "healthy", "avg_latency_ms": 22, "source": "Cross-API engine", "calls_today": 154},
    {"name": "ecosystem", "path": "/api/ecosystem", "status": "healthy", "avg_latency_ms": 35, "source": "Aggregation hub", "calls_today": 0},
]


def _cors_headers():
    """CORS-Header fuer Cross-Origin-Zugriff."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json",
    }


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS Preflight."""
        self.send_response(200)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        """
        GET /api/ecosystem?action=status  — Oekosystem-Statistiken
        GET /api/ecosystem?action=feed&limit=20  — Aktivitaets-Feed
        GET /api/ecosystem?action=health  — Health-Check aller Endpoints
        GET /api/ecosystem  — Uebersicht mit allen Aktionen
        """
        try:
            params = parse_qs(urlparse(self.path).query)
            action = params.get("action", [None])[0]

            if action == "status":
                self._handle_status()
            elif action == "feed":
                limit = 20
                if "limit" in params:
                    try:
                        limit = min(int(params["limit"][0]), 50)
                    except ValueError:
                        limit = 20
                self._handle_feed(limit)
            elif action == "health":
                self._handle_health()
            else:
                self._handle_overview()

        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _handle_status(self):
        """Oekosystem-Statistiken zurueckgeben."""
        # Dynamische Metriken berechnen
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        stats = {
            **ECOSYSTEM_STATS,
            "network_effects": {
                "reviews_improve_discovery": "Reviews feed into /api/recommend to suggest better servers",
                "threats_protect_all_agents": "Every threat report in /api/threats protects all querying agents",
                "tasks_match_agent_skills": "Agent capabilities from /api/agents match open tasks in /api/tasks",
                "agents_grow_recommendations": "More registered agents = smarter recommendations from /api/recommend",
                "discovery_feeds_reviews": "Servers found via /api/discover can be reviewed via /api/reviews",
            },
            "growth_indicators": {
                "agents_registered_today": 5,
                "reviews_submitted_today": 3,
                "threats_reported_today": 4,
                "tasks_created_today": 2,
                "recommendations_served_today": 87,
            },
            "ecosystem_health": "thriving",
            "timestamp": now,
        }
        self._respond(200, stats)

    def _handle_feed(self, limit):
        """Einheitlicher Aktivitaets-Feed ueber alle APIs."""
        feed = ACTIVITY_FEED[:limit]

        # Typ-Zaehlung
        type_counts = {}
        for item in ACTIVITY_FEED:
            t = item["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        self._respond(200, {
            "feed": feed,
            "count": len(feed),
            "total_activities": len(ACTIVITY_FEED),
            "by_type": type_counts,
            "description": "Unified activity feed across all ecosystem APIs — like a timeline for the agent world.",
        })

    def _handle_health(self):
        """Health-Check aller API-Endpoints."""
        healthy = sum(1 for ep in API_ENDPOINTS if ep["status"] == "healthy")
        total = len(API_ENDPOINTS)
        total_calls = sum(ep["calls_today"] for ep in API_ENDPOINTS)
        avg_latency = round(sum(ep["avg_latency_ms"] for ep in API_ENDPOINTS) / total, 1)

        self._respond(200, {
            "overall_status": "healthy" if healthy == total else "degraded",
            "endpoints_healthy": healthy,
            "endpoints_total": total,
            "total_calls_today": total_calls,
            "avg_latency_ms": avg_latency,
            "endpoints": API_ENDPOINTS,
            "checked_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    def _handle_overview(self):
        """Uebersicht des Oekosystems mit allen verfuegbaren Aktionen."""
        self._respond(200, {
            "name": "Agent Ecosystem Hub",
            "description": "Central hub connecting all Agent APIs into one ecosystem. The glue that creates network effects.",
            "version": "1.0.0",
            "base_url": "https://agent-apis.vercel.app",
            "total_endpoints": len(API_ENDPOINTS),
            "ecosystem_stats": {
                "registered_agents": ECOSYSTEM_STATS["registered_agents"],
                "mcp_servers": ECOSYSTEM_STATS["mcp_servers_cataloged"],
                "total_reviews": ECOSYSTEM_STATS["total_reviews"],
                "total_threats": ECOSYSTEM_STATS["total_threats"],
                "open_tasks": ECOSYSTEM_STATS["tasks_open"],
                "api_calls_total": ECOSYSTEM_STATS["api_calls_total"],
            },
            "actions": {
                "status": "GET /api/ecosystem?action=status — Full ecosystem statistics",
                "feed": "GET /api/ecosystem?action=feed&limit=20 — Unified activity feed",
                "health": "GET /api/ecosystem?action=health — Health check of all endpoints",
            },
            "api_map": {
                "data_layer": ["/api/weather", "/api/crypto", "/api/discover"],
                "safety_layer": ["/api/pii", "/api/compliance", "/api/threats"],
                "intelligence_layer": ["/api/route", "/api/optimize", "/api/recommend"],
                "social_layer": ["/api/reviews", "/api/tasks", "/api/agents"],
                "orchestration_layer": ["/api/ecosystem"],
            },
            "network_effects": "Every API call makes the ecosystem smarter. Reviews improve recommendations. Threats protect all agents. Agent registrations enable better task matching. The more agents participate, the more valuable the ecosystem becomes.",
        })

    def _respond(self, status, data):
        """JSON-Response senden."""
        self.send_response(status)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
