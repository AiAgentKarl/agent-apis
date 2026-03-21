"""
Agent Registry API — Serverless Function fuer Vercel.
DER Netzwerkeffekt-Play: Agents registrieren sich und ihre Faehigkeiten.
Andere Agents finden sie. Mehr Agents = nuetzlicher fuer alle.
Jede Registrierung macht das gesamte Oekosystem wertvoller.
"""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import hashlib


# Vorgefuellte Agent-Registry mit unseren Servern + fiktiven Drittanbietern
AGENTS_DB = {
    # === Unsere eigenen Agents (basierend auf MCP-Servern) ===
    "weather-agent": {
        "id": "weather-agent",
        "name": "Weather Agent",
        "capabilities": ["weather", "forecast", "climate", "temperature", "wind", "uv-index"],
        "description": "Global weather data powered by Open-Meteo. Current conditions, forecasts, and climate analytics for any location worldwide.",
        "endpoint": "https://agent-apis.vercel.app/api/weather",
        "version": "1.2.0",
        "owner": "AiAgentKarl",
        "status": "online",
        "last_seen": "2026-03-21T08:55:00Z",
        "registered_at": "2026-01-15T10:00:00Z",
        "queries": 2847,
        "rating": 4.5,
        "tags": ["free", "no-api-key", "global"],
    },
    "crypto-agent": {
        "id": "crypto-agent",
        "name": "Crypto Intelligence Agent",
        "capabilities": ["crypto", "bitcoin", "ethereum", "solana", "defi", "token-price", "whale-tracking", "yield-farming"],
        "description": "Real-time crypto prices, DeFi yields, whale tracking, and token safety checks. Covers 5000+ tokens across major chains.",
        "endpoint": "https://agent-apis.vercel.app/api/crypto",
        "version": "2.0.0",
        "owner": "AiAgentKarl",
        "status": "online",
        "last_seen": "2026-03-21T08:50:00Z",
        "registered_at": "2026-01-15T10:00:00Z",
        "queries": 4123,
        "rating": 4.7,
        "tags": ["free", "real-time", "multi-chain"],
    },
    "compliance-agent": {
        "id": "compliance-agent",
        "name": "Compliance Checker Agent",
        "capabilities": ["gdpr", "ai-act", "compliance", "pii-detection", "risk-assessment", "audit"],
        "description": "GDPR and EU AI Act compliance checking. PII detection, risk assessment, and regulatory guidance for AI systems.",
        "endpoint": "https://agent-apis.vercel.app/api/compliance",
        "version": "1.1.0",
        "owner": "AiAgentKarl",
        "status": "online",
        "last_seen": "2026-03-21T08:45:00Z",
        "registered_at": "2026-02-01T08:00:00Z",
        "queries": 1567,
        "rating": 4.6,
        "tags": ["enterprise", "eu-regulation", "unique"],
    },
    "memory-agent": {
        "id": "memory-agent",
        "name": "Persistent Memory Agent",
        "capabilities": ["memory", "storage", "recall", "knowledge-base", "fact-store", "context-persistence"],
        "description": "Persistent memory for AI agents across sessions. Store, recall, and manage facts and context without losing information.",
        "endpoint": "https://pypi.org/project/agent-memory-mcp-server/",
        "version": "1.3.0",
        "owner": "AiAgentKarl",
        "status": "online",
        "last_seen": "2026-03-21T08:40:00Z",
        "registered_at": "2026-01-20T12:00:00Z",
        "queries": 3891,
        "rating": 4.4,
        "tags": ["persistent", "cross-session", "essential"],
    },
    "security-agent": {
        "id": "security-agent",
        "name": "Cybersecurity Intelligence Agent",
        "capabilities": ["cve", "vulnerability", "exploit", "threat-intel", "malware", "osint", "pii-scan"],
        "description": "CVE database, vulnerability scanning, threat intelligence, and PII detection. Essential for security-conscious agents.",
        "endpoint": "https://pypi.org/project/cybersecurity-mcp-server/",
        "version": "1.1.0",
        "owner": "AiAgentKarl",
        "status": "online",
        "last_seen": "2026-03-21T08:35:00Z",
        "registered_at": "2026-01-25T09:00:00Z",
        "queries": 2234,
        "rating": 4.6,
        "tags": ["security", "cve", "threat-intel"],
    },
    "discovery-agent": {
        "id": "discovery-agent",
        "name": "MCP Server Discovery Agent",
        "capabilities": ["mcp-discovery", "server-search", "tool-catalog", "recommendations"],
        "description": "Search and discover MCP servers from a curated catalog of 50+ servers. Fuzzy keyword matching and category filtering.",
        "endpoint": "https://agent-apis.vercel.app/api/discover",
        "version": "1.0.0",
        "owner": "AiAgentKarl",
        "status": "online",
        "last_seen": "2026-03-21T08:30:00Z",
        "registered_at": "2026-02-10T14:00:00Z",
        "queries": 1987,
        "rating": 4.3,
        "tags": ["meta", "catalog", "unique"],
    },
    "cost-router-agent": {
        "id": "cost-router-agent",
        "name": "AI Cost Router Agent",
        "capabilities": ["cost-optimization", "model-routing", "llm-comparison", "pricing"],
        "description": "Routes AI requests to the cheapest or best provider based on task type, token count, and priority. Covers 15+ models.",
        "endpoint": "https://agent-apis.vercel.app/api/route",
        "version": "1.0.0",
        "owner": "AiAgentKarl",
        "status": "online",
        "last_seen": "2026-03-21T08:25:00Z",
        "registered_at": "2026-02-15T11:00:00Z",
        "queries": 1432,
        "rating": 4.4,
        "tags": ["cost-saving", "unique", "essential"],
    },
    "agriculture-agent": {
        "id": "agriculture-agent",
        "name": "Agriculture Data Agent",
        "capabilities": ["agriculture", "crop-data", "fao", "soil", "livestock", "harvest", "food-security"],
        "description": "FAO statistics, crop data, livestock counts, soil quality, and food security indicators. Global agricultural intelligence.",
        "endpoint": "https://pypi.org/project/agriculture-mcp-server/",
        "version": "1.0.0",
        "owner": "AiAgentKarl",
        "status": "online",
        "last_seen": "2026-03-21T08:20:00Z",
        "registered_at": "2026-01-20T10:00:00Z",
        "queries": 1876,
        "rating": 4.3,
        "tags": ["free", "global", "fao-data"],
    },
    "workflow-agent": {
        "id": "workflow-agent",
        "name": "Workflow Orchestration Agent",
        "capabilities": ["workflow", "pipeline", "automation", "orchestration", "task-sequence"],
        "description": "Define, execute, and automate multi-step workflows. Pipeline templates for common agent tasks.",
        "endpoint": "https://pypi.org/project/agent-workflow-mcp-server/",
        "version": "1.2.0",
        "owner": "AiAgentKarl",
        "status": "online",
        "last_seen": "2026-03-21T08:15:00Z",
        "registered_at": "2026-02-05T15:00:00Z",
        "queries": 1654,
        "rating": 4.2,
        "tags": ["automation", "multi-step", "templates"],
    },
    "analytics-agent": {
        "id": "analytics-agent",
        "name": "Usage Analytics Agent",
        "capabilities": ["analytics", "metrics", "usage-tracking", "dashboards", "reporting"],
        "description": "Track and analyze tool usage, API calls, and performance metrics. Dashboards and reporting for agent operations.",
        "endpoint": "https://pypi.org/project/agent-analytics-mcp-server/",
        "version": "1.1.0",
        "owner": "AiAgentKarl",
        "status": "online",
        "last_seen": "2026-03-21T08:10:00Z",
        "registered_at": "2026-02-08T09:00:00Z",
        "queries": 1321,
        "rating": 4.1,
        "tags": ["metrics", "monitoring", "insights"],
    },
    "reputation-agent": {
        "id": "reputation-agent",
        "name": "Agent Reputation & Trust Agent",
        "capabilities": ["reputation", "trust-score", "quality-metrics", "reliability", "review-aggregation"],
        "description": "Trust scoring system for AI agents. Track reliability, quality metrics, and build reputation across interactions.",
        "endpoint": "https://pypi.org/project/agent-reputation-mcp-server/",
        "version": "1.0.0",
        "owner": "AiAgentKarl",
        "status": "online",
        "last_seen": "2026-03-21T08:05:00Z",
        "registered_at": "2026-01-28T11:00:00Z",
        "queries": 1198,
        "rating": 4.3,
        "tags": ["trust", "quality", "social"],
    },
    "space-agent": {
        "id": "space-agent",
        "name": "Space Data Agent",
        "capabilities": ["nasa", "esa", "satellite", "asteroid", "mars", "iss-tracking", "astronomy"],
        "description": "NASA and ESA data: APOD, asteroid tracking, ISS position, Mars rover photos, and satellite data.",
        "endpoint": "https://pypi.org/project/space-mcp-server/",
        "version": "1.0.0",
        "owner": "AiAgentKarl",
        "status": "online",
        "last_seen": "2026-03-21T07:55:00Z",
        "registered_at": "2026-01-22T16:00:00Z",
        "queries": 987,
        "rating": 4.4,
        "tags": ["free", "nasa", "science"],
    },

    # === Fiktive Drittanbieter-Agents ===
    "translation-agent": {
        "id": "translation-agent",
        "name": "Multi-Language Translation Agent",
        "capabilities": ["translation", "localization", "language-detection", "40-languages", "technical-translation"],
        "description": "Professional-grade translation across 40+ languages. Supports technical, legal, and medical terminology.",
        "endpoint": "https://translate-agent.example.com/api",
        "version": "3.1.0",
        "owner": "PolyglotAI",
        "status": "online",
        "last_seen": "2026-03-21T08:52:00Z",
        "registered_at": "2026-01-10T08:00:00Z",
        "queries": 5621,
        "rating": 4.7,
        "tags": ["premium", "40-languages", "certified"],
    },
    "code-review-agent": {
        "id": "code-review-agent",
        "name": "Code Review & Analysis Agent",
        "capabilities": ["code-review", "static-analysis", "bug-detection", "security-audit", "python", "javascript", "rust"],
        "description": "Automated code review with security audit, bug detection, and style checks. Supports Python, JS, Rust, Go.",
        "endpoint": "https://code-review-bot.example.com/api",
        "version": "2.0.0",
        "owner": "DevToolsInc",
        "status": "online",
        "last_seen": "2026-03-21T08:48:00Z",
        "registered_at": "2026-01-12T14:00:00Z",
        "queries": 3456,
        "rating": 4.5,
        "tags": ["security", "multi-language", "ci-cd"],
    },
    "data-analysis-agent": {
        "id": "data-analysis-agent",
        "name": "Data Analysis & Visualization Agent",
        "capabilities": ["data-analysis", "visualization", "statistics", "pandas", "charts", "csv", "excel"],
        "description": "Analyze datasets, generate visualizations, compute statistics. Handles CSV, Excel, JSON, and SQL databases.",
        "endpoint": "https://data-agent.example.com/api",
        "version": "1.5.0",
        "owner": "DataScienceLab",
        "status": "online",
        "last_seen": "2026-03-21T08:44:00Z",
        "registered_at": "2026-01-18T10:00:00Z",
        "queries": 4210,
        "rating": 4.6,
        "tags": ["analytics", "visualization", "big-data"],
    },
    "image-generation-agent": {
        "id": "image-generation-agent",
        "name": "Image Generation Agent",
        "capabilities": ["image-generation", "stable-diffusion", "dalle", "midjourney", "editing", "upscaling"],
        "description": "Generate, edit, and upscale images using multiple models. Supports Stable Diffusion, DALL-E, and custom models.",
        "endpoint": "https://img-gen-agent.example.com/api",
        "version": "2.3.0",
        "owner": "CreativeAI",
        "status": "online",
        "last_seen": "2026-03-21T08:40:00Z",
        "registered_at": "2026-01-08T09:00:00Z",
        "queries": 7823,
        "rating": 4.4,
        "tags": ["creative", "multi-model", "premium"],
    },
    "email-agent": {
        "id": "email-agent",
        "name": "Email Management Agent",
        "capabilities": ["email", "smtp", "inbox-analysis", "spam-filter", "scheduling", "templates"],
        "description": "Send, receive, and analyze emails. Smart inbox management, spam filtering, and automated responses.",
        "endpoint": "https://email-agent.example.com/api",
        "version": "1.4.0",
        "owner": "MailBotInc",
        "status": "online",
        "last_seen": "2026-03-21T08:36:00Z",
        "registered_at": "2026-02-01T11:00:00Z",
        "queries": 2987,
        "rating": 4.2,
        "tags": ["productivity", "automation", "enterprise"],
    },
    "calendar-agent": {
        "id": "calendar-agent",
        "name": "Calendar & Scheduling Agent",
        "capabilities": ["calendar", "scheduling", "reminders", "timezone", "booking", "availability"],
        "description": "Calendar management, meeting scheduling, timezone conversion, and availability checking across platforms.",
        "endpoint": "https://calendar-agent.example.com/api",
        "version": "1.2.0",
        "owner": "ScheduleAI",
        "status": "online",
        "last_seen": "2026-03-21T08:32:00Z",
        "registered_at": "2026-02-05T13:00:00Z",
        "queries": 1876,
        "rating": 4.3,
        "tags": ["productivity", "enterprise", "cross-platform"],
    },
    "search-agent": {
        "id": "search-agent",
        "name": "Web Search & Research Agent",
        "capabilities": ["web-search", "research", "fact-checking", "news", "academic-search", "summarization"],
        "description": "Web search, academic research, fact-checking, and news monitoring. Aggregates multiple search engines.",
        "endpoint": "https://search-agent.example.com/api",
        "version": "2.1.0",
        "owner": "SearchMaster",
        "status": "online",
        "last_seen": "2026-03-21T08:28:00Z",
        "registered_at": "2026-01-05T10:00:00Z",
        "queries": 8912,
        "rating": 4.5,
        "tags": ["essential", "multi-source", "real-time"],
    },
    "database-agent": {
        "id": "database-agent",
        "name": "Database Operations Agent",
        "capabilities": ["sql", "nosql", "postgres", "mongodb", "redis", "query-optimization", "schema-design"],
        "description": "Database operations across SQL and NoSQL. Query optimization, schema design, migration, and monitoring.",
        "endpoint": "https://db-agent.example.com/api",
        "version": "1.3.0",
        "owner": "DataOpsTeam",
        "status": "online",
        "last_seen": "2026-03-21T08:24:00Z",
        "registered_at": "2026-01-15T15:00:00Z",
        "queries": 3214,
        "rating": 4.4,
        "tags": ["infrastructure", "multi-db", "enterprise"],
    },
    "pdf-extractor-agent": {
        "id": "pdf-extractor-agent",
        "name": "PDF & Document Extraction Agent",
        "capabilities": ["pdf-parsing", "ocr", "table-extraction", "text-extraction", "document-analysis"],
        "description": "Extract text, tables, and structured data from PDFs and scanned documents. OCR for images and handwriting.",
        "endpoint": "https://pdf-agent.example.com/api",
        "version": "1.1.0",
        "owner": "DocParseAI",
        "status": "online",
        "last_seen": "2026-03-21T08:20:00Z",
        "registered_at": "2026-02-10T09:00:00Z",
        "queries": 2543,
        "rating": 4.3,
        "tags": ["document", "ocr", "enterprise"],
    },
    "notification-agent": {
        "id": "notification-agent",
        "name": "Multi-Channel Notification Agent",
        "capabilities": ["notifications", "slack", "discord", "telegram", "webhook", "alerts"],
        "description": "Send notifications across Slack, Discord, Telegram, email, and webhooks. Smart alerting and escalation.",
        "endpoint": "https://notify-agent.example.com/api",
        "version": "1.5.0",
        "owner": "AlertHub",
        "status": "online",
        "last_seen": "2026-03-21T08:16:00Z",
        "registered_at": "2026-02-08T14:00:00Z",
        "queries": 4567,
        "rating": 4.1,
        "tags": ["multi-channel", "real-time", "essential"],
    },
    "legal-agent": {
        "id": "legal-agent",
        "name": "Legal Research & Analysis Agent",
        "capabilities": ["legal-research", "court-rulings", "contract-analysis", "gdpr", "ip-law", "compliance"],
        "description": "Legal research across court databases, contract analysis, IP law guidance, and regulatory compliance checking.",
        "endpoint": "https://legal-agent.example.com/api",
        "version": "1.0.0",
        "owner": "LexAI",
        "status": "online",
        "last_seen": "2026-03-21T08:12:00Z",
        "registered_at": "2026-02-15T10:00:00Z",
        "queries": 987,
        "rating": 4.5,
        "tags": ["enterprise", "specialized", "eu-law"],
    },
    "devops-agent": {
        "id": "devops-agent",
        "name": "DevOps & CI/CD Agent",
        "capabilities": ["ci-cd", "docker", "kubernetes", "terraform", "github-actions", "deployment", "monitoring"],
        "description": "CI/CD pipeline management, container orchestration, infrastructure-as-code, and deployment automation.",
        "endpoint": "https://devops-agent.example.com/api",
        "version": "2.0.0",
        "owner": "InfraAutomation",
        "status": "online",
        "last_seen": "2026-03-21T08:08:00Z",
        "registered_at": "2026-01-20T11:00:00Z",
        "queries": 2876,
        "rating": 4.4,
        "tags": ["infrastructure", "automation", "cloud"],
    },
    "testing-agent": {
        "id": "testing-agent",
        "name": "QA & Testing Agent",
        "capabilities": ["testing", "unit-tests", "integration-tests", "e2e", "test-generation", "coverage"],
        "description": "Automated test generation, test execution, coverage analysis, and bug regression detection.",
        "endpoint": "https://testing-agent.example.com/api",
        "version": "1.2.0",
        "owner": "QualityFirst",
        "status": "online",
        "last_seen": "2026-03-21T08:04:00Z",
        "registered_at": "2026-02-12T16:00:00Z",
        "queries": 1543,
        "rating": 4.2,
        "tags": ["quality", "automation", "ci-cd"],
    },
    "finance-agent": {
        "id": "finance-agent",
        "name": "Financial Data & Analysis Agent",
        "capabilities": ["stock-market", "forex", "commodities", "financial-analysis", "risk-assessment", "portfolio"],
        "description": "Financial market data, stock analysis, forex rates, commodities, and portfolio risk assessment.",
        "endpoint": "https://finance-agent.example.com/api",
        "version": "1.3.0",
        "owner": "FinDataPro",
        "status": "online",
        "last_seen": "2026-03-21T08:00:00Z",
        "registered_at": "2026-01-10T14:00:00Z",
        "queries": 5432,
        "rating": 4.6,
        "tags": ["financial", "real-time", "premium"],
    },
    "scraping-agent": {
        "id": "scraping-agent",
        "name": "Web Scraping & Extraction Agent",
        "capabilities": ["web-scraping", "html-parsing", "data-extraction", "screenshot", "headless-browser"],
        "description": "Extract structured data from any website. Handles JavaScript-rendered content, pagination, and anti-bot measures.",
        "endpoint": "https://scrape-agent.example.com/api",
        "version": "2.1.0",
        "owner": "WebDataInc",
        "status": "offline",
        "last_seen": "2026-03-20T22:15:00Z",
        "registered_at": "2026-01-18T09:00:00Z",
        "queries": 6789,
        "rating": 4.3,
        "tags": ["data-collection", "headless", "robust"],
    },
    "monitoring-agent": {
        "id": "monitoring-agent",
        "name": "Infrastructure Monitoring Agent",
        "capabilities": ["uptime-monitoring", "performance", "alerting", "latency", "error-tracking"],
        "description": "Monitor uptime, performance, latency, and errors across services. Smart alerting with escalation policies.",
        "endpoint": "https://monitor-agent.example.com/api",
        "version": "1.4.0",
        "owner": "UptimeAI",
        "status": "online",
        "last_seen": "2026-03-21T07:56:00Z",
        "registered_at": "2026-02-01T08:00:00Z",
        "queries": 3456,
        "rating": 4.5,
        "tags": ["infrastructure", "24-7", "enterprise"],
    },
}

# Laufende ID fuer neue Agents
_next_id = len(AGENTS_DB) + 1


def _cors_headers():
    """CORS-Header fuer Cross-Origin-Zugriff."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json",
    }


def _is_online(agent):
    """Prueft ob ein Agent als online gilt (letzte Stunde gepingt)."""
    return agent.get("status") == "online"


def _generate_id(name):
    """Generiert eine deterministische ID aus dem Agent-Namen."""
    clean = name.lower().strip().replace(" ", "-")
    # Nur alphanumerisch und Bindestriche
    clean = "".join(c for c in clean if c.isalnum() or c == "-")
    return clean


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS Preflight."""
        self.send_response(200)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        """
        GET /api/agents?q=weather — Agents nach Capability suchen
        GET /api/agents?capability=translation — Nach spezifischer Capability filtern
        GET /api/agents?top=10 — Populaerste Agents
        GET /api/agents?id=weather-agent — Agent-Details
        GET /api/agents?owner=AiAgentKarl — Agents eines Owners
        GET /api/agents — Uebersicht
        """
        try:
            params = parse_qs(urlparse(self.path).query)

            # Einzelner Agent per ID
            if "id" in params:
                agent_id = params["id"][0].strip().lower()
                agent = AGENTS_DB.get(agent_id)
                if not agent:
                    self._respond(404, {"error": f"Agent '{agent_id}' not found"})
                    return
                # Query-Zaehler erhoehen (simuliert Popularitaet)
                agent["queries"] = agent.get("queries", 0) + 1
                self._respond(200, {
                    "agent": agent,
                    "ecosystem_tip": "Use /api/recommend?agent=" + agent_id + " to find complementary agents.",
                })
                return

            # Suche nach Capability
            if "capability" in params:
                cap = params["capability"][0].strip().lower()
                matches = [
                    a for a in AGENTS_DB.values()
                    if any(cap in c.lower() for c in a.get("capabilities", []))
                ]
                matches.sort(key=lambda x: (-x.get("queries", 0), -x.get("rating", 0)))
                self._respond(200, {
                    "capability": cap,
                    "agents": matches,
                    "count": len(matches),
                    "total_agents": len(AGENTS_DB),
                })
                return

            # Volltextsuche
            if "q" in params:
                q = params["q"][0].strip().lower()
                matches = []
                for a in AGENTS_DB.values():
                    score = 0
                    # Capabilities matchen
                    for cap in a.get("capabilities", []):
                        if q in cap.lower():
                            score += 10
                    # Name matchen
                    if q in a.get("name", "").lower():
                        score += 8
                    # Description matchen
                    if q in a.get("description", "").lower():
                        score += 5
                    # Tags matchen
                    for tag in a.get("tags", []):
                        if q in tag.lower():
                            score += 3
                    if score > 0:
                        matches.append((score, a))

                matches.sort(key=lambda x: (-x[0], -x[1].get("queries", 0)))
                agents = [m[1] for m in matches]

                self._respond(200, {
                    "query": q,
                    "agents": agents,
                    "count": len(agents),
                    "total_agents": len(AGENTS_DB),
                })
                return

            # Top Agents nach Popularitaet
            if "top" in params:
                try:
                    n = min(int(params["top"][0]), 50)
                except ValueError:
                    n = 10
                sorted_agents = sorted(AGENTS_DB.values(), key=lambda x: -x.get("queries", 0))
                self._respond(200, {
                    "top_agents": sorted_agents[:n],
                    "total_agents": len(AGENTS_DB),
                })
                return

            # Agents nach Owner filtern
            if "owner" in params:
                owner = params["owner"][0].strip()
                matches = [a for a in AGENTS_DB.values() if a.get("owner", "").lower() == owner.lower()]
                matches.sort(key=lambda x: -x.get("queries", 0))
                self._respond(200, {
                    "owner": owner,
                    "agents": matches,
                    "count": len(matches),
                })
                return

            # Kein Parameter — Uebersicht
            online_count = sum(1 for a in AGENTS_DB.values() if _is_online(a))
            all_capabilities = set()
            all_owners = set()
            for a in AGENTS_DB.values():
                all_capabilities.update(a.get("capabilities", []))
                all_owners.add(a.get("owner", "unknown"))

            overview = {
                "total_agents": len(AGENTS_DB),
                "agents_online": online_count,
                "agents_offline": len(AGENTS_DB) - online_count,
                "unique_capabilities": len(all_capabilities),
                "unique_owners": len(all_owners),
                "top_capabilities": sorted(list(all_capabilities))[:20],
                "endpoints": {
                    "search": "GET /api/agents?q=weather",
                    "by_capability": "GET /api/agents?capability=translation",
                    "top_agents": "GET /api/agents?top=10",
                    "agent_details": "GET /api/agents?id=weather-agent",
                    "by_owner": "GET /api/agents?owner=AiAgentKarl",
                    "register": "POST /api/agents {name, capabilities, description, endpoint, version, owner}",
                    "heartbeat": "PATCH /api/agents?id=weather-agent&action=ping",
                },
                "description": "Agent registry — the network effect engine. More agents = better discovery = more value for everyone.",
                "network_effect": f"{len(AGENTS_DB)} agents registered. Each new agent makes the registry more valuable for all.",
            }
            self._respond(200, overview)

        except Exception as e:
            self._respond(500, {"error": str(e)})

    def do_POST(self):
        """Neuen Agent registrieren."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._respond(400, {"error": "Request body required"})
                return

            body = json.loads(self.rfile.read(content_length))

            name = body.get("name", "").strip()
            capabilities = body.get("capabilities", [])
            description = body.get("description", "").strip()
            endpoint = body.get("endpoint", "").strip()
            version = body.get("version", "1.0.0")
            owner = body.get("owner", "anonymous")

            if not name:
                self._respond(400, {"error": "Field 'name' is required"})
                return

            if not isinstance(capabilities, list) or len(capabilities) == 0:
                self._respond(400, {"error": "Field 'capabilities' must be a non-empty list"})
                return

            agent_id = _generate_id(name)

            # Pruefen ob Agent schon existiert
            if agent_id in AGENTS_DB:
                self._respond(409, {
                    "error": f"Agent '{agent_id}' already exists. Use PATCH to update.",
                    "existing_agent": AGENTS_DB[agent_id],
                })
                return

            now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            agent = {
                "id": agent_id,
                "name": str(name)[:100],
                "capabilities": [str(c).lower().strip() for c in capabilities[:20]],
                "description": str(description)[:500],
                "endpoint": str(endpoint)[:200],
                "version": str(version),
                "owner": str(owner),
                "status": "online",
                "last_seen": now,
                "registered_at": now,
                "queries": 0,
                "rating": 0.0,
                "tags": [],
            }

            AGENTS_DB[agent_id] = agent

            self._respond(201, {
                "status": "agent_registered",
                "agent": agent,
                "total_agents": len(AGENTS_DB),
                "network_effect": f"Your agent is now discoverable by {len(AGENTS_DB) - 1} other agents in the ecosystem.",
                "next_steps": {
                    "keep_alive": f"PATCH /api/agents?id={agent_id}&action=ping",
                    "find_complementary": f"GET /api/recommend?agent={agent_id}",
                    "browse_tasks": "GET /api/tasks?status=open",
                },
            })

        except json.JSONDecodeError:
            self._respond(400, {"error": "Invalid JSON body"})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def do_PATCH(self):
        """Agent-Heartbeat oder Status-Update."""
        try:
            params = parse_qs(urlparse(self.path).query)

            agent_id = params.get("id", [None])[0]
            action = params.get("action", [None])[0]

            if not agent_id:
                self._respond(400, {"error": "Parameter 'id' is required"})
                return

            agent = AGENTS_DB.get(agent_id)
            if not agent:
                self._respond(404, {"error": f"Agent '{agent_id}' not found"})
                return

            now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

            if action == "ping":
                agent["last_seen"] = now
                agent["status"] = "online"
                self._respond(200, {
                    "status": "heartbeat_received",
                    "agent_id": agent_id,
                    "last_seen": now,
                    "message": "Agent is online and healthy.",
                })
            elif action == "offline":
                agent["status"] = "offline"
                agent["last_seen"] = now
                self._respond(200, {
                    "status": "agent_offline",
                    "agent_id": agent_id,
                    "message": "Agent marked as offline.",
                })
            else:
                self._respond(400, {
                    "error": f"Unknown action '{action}'. Use 'ping' or 'offline'.",
                })

        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _respond(self, status, data):
        """JSON-Response senden."""
        self.send_response(status)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
