"""
Agent Ecosystem Hub — Kombinierte Serverless Function fuer Vercel.
Vereint ecosystem, agents und recommend in EINER Function.
Routing ueber ?action= Parameter.

Actions:
  GET  ?action=status    — Oekosystem-Statistiken
  GET  ?action=feed      — Aktivitaets-Feed
  GET  ?action=health    — Health-Check aller Endpoints
  GET  ?action=agents    — Agent-Registry (Suche, Filter, Top, Details)
  GET  ?action=recommend — Empfehlungen (Task, Agent, Trending)
  POST (JSON body)       — Agent registrieren, Heartbeat, etc.
"""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import hashlib
from api.storage import load_data, save_data


# ============================================================
# ECOSYSTEM-DATEN
# ============================================================

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

# Simulierte Oekosystem-Metriken
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

# API-Endpoint-Gesundheit
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
    {"name": "hub", "path": "/api/hub", "status": "healthy", "avg_latency_ms": 15, "source": "Combined hub", "calls_today": 355},
]


# ============================================================
# AGENTS-DATEN
# ============================================================

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

# --- Persistenz: Agents und Feed aus /tmp/ laden falls vorhanden ---
_persisted_agents = load_data("hub_agents")
if _persisted_agents is not None:
    AGENTS_DB = _persisted_agents

_persisted_feed = load_data("hub_feed")
if _persisted_feed is not None:
    ACTIVITY_FEED = _persisted_feed


# ============================================================
# RECOMMEND-DATEN
# ============================================================

# Affinity-Map: Welche Tools/Agents passen zusammen? (Score 0.0-1.0)
AFFINITY_MAP = {
    ("weather", "agriculture"): 0.95, ("agriculture", "weather"): 0.95,
    ("weather", "climate"): 0.90,
    ("crypto", "security"): 0.92, ("security", "crypto"): 0.92,
    ("crypto", "defi"): 0.95, ("defi", "crypto"): 0.95,
    ("compliance", "audit"): 0.93, ("audit", "compliance"): 0.93,
    ("compliance", "gdpr"): 0.95, ("gdpr", "compliance"): 0.95,
    ("compliance", "pii"): 0.90, ("pii", "compliance"): 0.90,
    ("memory", "workflow"): 0.85, ("workflow", "memory"): 0.85,
    ("workflow", "analytics"): 0.82, ("analytics", "workflow"): 0.82,
    ("translation", "legal"): 0.80, ("legal", "translation"): 0.80,
    ("code-review", "testing"): 0.90, ("testing", "code-review"): 0.90,
    ("code-review", "devops"): 0.85, ("devops", "code-review"): 0.85,
    ("devops", "monitoring"): 0.92, ("monitoring", "devops"): 0.92,
    ("search", "research"): 0.88, ("research", "search"): 0.88,
    ("data-analysis", "visualization"): 0.90, ("visualization", "data-analysis"): 0.90,
    ("email", "calendar"): 0.87, ("calendar", "email"): 0.87,
    ("notification", "monitoring"): 0.85, ("monitoring", "notification"): 0.85,
    ("database", "analytics"): 0.83, ("analytics", "database"): 0.83,
    ("security", "compliance"): 0.88, ("compliance", "security"): 0.88,
    ("legal", "compliance"): 0.90, ("compliance", "legal"): 0.90,
    ("agriculture", "supply-chain"): 0.85, ("supply-chain", "agriculture"): 0.85,
    ("weather", "energy"): 0.82, ("energy", "weather"): 0.82,
    ("finance", "crypto"): 0.85, ("crypto", "finance"): 0.85,
    ("finance", "data-analysis"): 0.83, ("data-analysis", "finance"): 0.83,
    ("space", "data-analysis"): 0.70, ("data-analysis", "space"): 0.70,
    ("reputation", "reviews"): 0.88, ("reviews", "reputation"): 0.88,
    ("identity", "security"): 0.85, ("security", "identity"): 0.85,
    ("pdf-extraction", "legal"): 0.87, ("legal", "pdf-extraction"): 0.87,
    ("pdf-extraction", "data-analysis"): 0.80, ("data-analysis", "pdf-extraction"): 0.80,
    ("scraping", "data-analysis"): 0.82, ("data-analysis", "scraping"): 0.82,
    ("image-generation", "pdf-extraction"): 0.65,
}

# Keyword-zu-Agent-Mapping (fuer Task-basierte Empfehlungen)
KEYWORD_AGENT_MAP = {
    "weather": ["weather-agent", "openmeteo-mcp-server"],
    "forecast": ["weather-agent", "openmeteo-mcp-server"],
    "climate": ["weather-agent", "openmeteo-mcp-server", "energy-grid-mcp-server"],
    "temperature": ["weather-agent"],
    "crypto": ["crypto-agent", "solana-mcp-server"],
    "bitcoin": ["crypto-agent"],
    "ethereum": ["crypto-agent"],
    "solana": ["crypto-agent", "solana-mcp-server"],
    "defi": ["crypto-agent", "solana-mcp-server"],
    "wallet": ["crypto-agent", "solana-mcp-server"],
    "token": ["crypto-agent", "solana-mcp-server"],
    "whale": ["crypto-agent", "solana-mcp-server"],
    "yield": ["crypto-agent", "solana-mcp-server"],
    "compliance": ["compliance-agent", "agent-policy-gateway-mcp"],
    "gdpr": ["compliance-agent", "agent-policy-gateway-mcp"],
    "ai-act": ["compliance-agent", "agent-policy-gateway-mcp"],
    "pii": ["compliance-agent", "agent-policy-gateway-mcp"],
    "audit": ["compliance-agent", "agent-audit-trail-mcp"],
    "security": ["security-agent", "cybersecurity-mcp-server"],
    "cve": ["security-agent", "cybersecurity-mcp-server"],
    "vulnerability": ["security-agent", "cybersecurity-mcp-server"],
    "threat": ["security-agent", "cybersecurity-mcp-server"],
    "memory": ["memory-agent", "agent-memory-mcp-server"],
    "storage": ["memory-agent", "database-agent"],
    "recall": ["memory-agent"],
    "workflow": ["workflow-agent", "agent-workflow-mcp-server"],
    "automation": ["workflow-agent", "devops-agent"],
    "pipeline": ["workflow-agent", "devops-agent"],
    "analytics": ["analytics-agent", "agent-analytics-mcp-server"],
    "metrics": ["analytics-agent", "monitoring-agent"],
    "dashboard": ["analytics-agent"],
    "translation": ["translation-agent"],
    "language": ["translation-agent"],
    "localization": ["translation-agent"],
    "code": ["code-review-agent"],
    "review": ["code-review-agent"],
    "testing": ["testing-agent"],
    "test": ["testing-agent"],
    "qa": ["testing-agent"],
    "data": ["data-analysis-agent", "database-agent"],
    "analysis": ["data-analysis-agent", "finance-agent"],
    "visualization": ["data-analysis-agent"],
    "statistics": ["data-analysis-agent"],
    "financial": ["finance-agent", "crypto-agent"],
    "stock": ["finance-agent"],
    "market": ["finance-agent", "crypto-agent"],
    "portfolio": ["finance-agent", "crypto-agent"],
    "image": ["image-generation-agent"],
    "generate": ["image-generation-agent"],
    "creative": ["image-generation-agent"],
    "email": ["email-agent", "notification-agent"],
    "calendar": ["calendar-agent"],
    "schedule": ["calendar-agent"],
    "booking": ["calendar-agent"],
    "search": ["search-agent", "discovery-agent"],
    "research": ["search-agent", "crossref-academic-mcp-server"],
    "web": ["search-agent", "scraping-agent"],
    "database": ["database-agent"],
    "sql": ["database-agent"],
    "postgres": ["database-agent"],
    "pdf": ["pdf-extractor-agent"],
    "document": ["pdf-extractor-agent"],
    "ocr": ["pdf-extractor-agent"],
    "notification": ["notification-agent"],
    "alert": ["notification-agent", "monitoring-agent"],
    "slack": ["notification-agent"],
    "legal": ["legal-agent", "legal-court-mcp-server"],
    "court": ["legal-agent", "legal-court-mcp-server"],
    "law": ["legal-agent"],
    "contract": ["legal-agent"],
    "devops": ["devops-agent"],
    "docker": ["devops-agent"],
    "kubernetes": ["devops-agent"],
    "deploy": ["devops-agent"],
    "monitor": ["monitoring-agent"],
    "uptime": ["monitoring-agent"],
    "performance": ["monitoring-agent"],
    "agriculture": ["agriculture-agent", "agriculture-mcp-server"],
    "farming": ["agriculture-agent", "agriculture-mcp-server"],
    "crop": ["agriculture-agent"],
    "space": ["space-agent", "space-mcp-server"],
    "nasa": ["space-agent", "space-mcp-server"],
    "satellite": ["space-agent"],
    "scraping": ["scraping-agent"],
    "reputation": ["reputation-agent", "agent-reputation-mcp-server"],
    "trust": ["reputation-agent", "agent-reputation-mcp-server"],
    "supply": ["supply-chain-mcp-server"],
    "trade": ["supply-chain-mcp-server"],
    "energy": ["energy-grid-mcp-server"],
    "electricity": ["energy-grid-mcp-server"],
    "benchmark": ["llm-benchmark-mcp-server"],
    "llm": ["llm-benchmark-mcp-server", "cost-router-agent"],
    "model": ["llm-benchmark-mcp-server", "cost-router-agent"],
    "cost": ["cost-router-agent"],
    "pricing": ["cost-router-agent"],
    "discover": ["discovery-agent", "mcp-appstore-server"],
    "mcp": ["discovery-agent", "mcp-appstore-server"],
    "payment": ["x402-mcp-server"],
    "commerce": ["agent-commerce-mcp-server", "agentic-product-protocol-mcp"],
    "shopping": ["agentic-product-protocol-mcp"],
    "product": ["agentic-product-protocol-mcp"],
}

# "Also used with" Beziehungen (Amazon-Style)
ALSO_USED_WITH = {
    "weather-agent": ["agriculture-agent", "energy-grid-mcp-server", "supply-chain-mcp-server", "analytics-agent"],
    "crypto-agent": ["security-agent", "finance-agent", "compliance-agent", "analytics-agent"],
    "compliance-agent": ["legal-agent", "security-agent", "analytics-agent", "reputation-agent"],
    "memory-agent": ["workflow-agent", "analytics-agent", "search-agent", "database-agent"],
    "security-agent": ["compliance-agent", "crypto-agent", "monitoring-agent", "devops-agent"],
    "discovery-agent": ["reputation-agent", "compliance-agent", "analytics-agent", "workflow-agent"],
    "cost-router-agent": ["analytics-agent", "workflow-agent", "finance-agent", "monitoring-agent"],
    "agriculture-agent": ["weather-agent", "supply-chain-mcp-server", "data-analysis-agent", "search-agent"],
    "workflow-agent": ["memory-agent", "analytics-agent", "notification-agent", "devops-agent"],
    "analytics-agent": ["workflow-agent", "database-agent", "monitoring-agent", "data-analysis-agent"],
    "reputation-agent": ["compliance-agent", "analytics-agent", "security-agent", "legal-agent"],
    "space-agent": ["data-analysis-agent", "search-agent", "image-generation-agent", "analytics-agent"],
    "translation-agent": ["legal-agent", "pdf-extractor-agent", "email-agent", "search-agent"],
    "code-review-agent": ["testing-agent", "devops-agent", "security-agent", "database-agent"],
    "data-analysis-agent": ["database-agent", "finance-agent", "search-agent", "pdf-extractor-agent"],
    "image-generation-agent": ["search-agent", "data-analysis-agent", "scraping-agent", "email-agent"],
    "email-agent": ["calendar-agent", "notification-agent", "translation-agent", "workflow-agent"],
    "calendar-agent": ["email-agent", "notification-agent", "workflow-agent", "search-agent"],
    "search-agent": ["data-analysis-agent", "scraping-agent", "pdf-extractor-agent", "translation-agent"],
    "database-agent": ["analytics-agent", "data-analysis-agent", "devops-agent", "monitoring-agent"],
    "pdf-extractor-agent": ["legal-agent", "data-analysis-agent", "translation-agent", "search-agent"],
    "notification-agent": ["monitoring-agent", "email-agent", "workflow-agent", "calendar-agent"],
    "legal-agent": ["compliance-agent", "translation-agent", "pdf-extractor-agent", "search-agent"],
    "devops-agent": ["monitoring-agent", "code-review-agent", "testing-agent", "notification-agent"],
    "testing-agent": ["code-review-agent", "devops-agent", "analytics-agent", "monitoring-agent"],
    "finance-agent": ["crypto-agent", "data-analysis-agent", "analytics-agent", "compliance-agent"],
    "scraping-agent": ["data-analysis-agent", "search-agent", "database-agent", "pdf-extractor-agent"],
    "monitoring-agent": ["devops-agent", "notification-agent", "analytics-agent", "security-agent"],
}

# Trending Items
TRENDING_ITEMS = [
    {"name": "legal-court-mcp-server", "type": "mcp-server", "reason": "Newest addition — 3M+ court rulings searchable", "confidence": 0.92, "category": "legal"},
    {"name": "llm-benchmark-mcp-server", "type": "mcp-server", "reason": "High demand — 20+ models compared with real-time pricing", "confidence": 0.89, "category": "ai-tools"},
    {"name": "energy-grid-mcp-server", "type": "mcp-server", "reason": "Growing ESG/climate regulation drives demand", "confidence": 0.87, "category": "infrastructure"},
    {"name": "labor-market-mcp-server", "type": "mcp-server", "reason": "Newest server — US/EU labor data from BLS and Eurostat", "confidence": 0.91, "category": "data"},
    {"name": "agent-policy-gateway-mcp", "type": "mcp-server", "reason": "EU AI Act enforcement approaching — compliance is critical", "confidence": 0.94, "category": "compliance"},
    {"name": "a2a-protocol-mcp-server", "type": "mcp-server", "reason": "Google A2A protocol gaining adoption for agent interop", "confidence": 0.88, "category": "protocol"},
    {"name": "agentic-product-protocol-mcp", "type": "mcp-server", "reason": "AI shopping agents are the next frontier of e-commerce", "confidence": 0.86, "category": "commerce"},
    {"name": "compliance-agent", "type": "agent", "reason": "EU AI Act high-risk obligations effective 2026-08 — agents preparing now", "confidence": 0.93, "category": "compliance"},
    {"name": "legal-agent", "type": "agent", "reason": "Legal AI demand surging with regulatory complexity", "confidence": 0.85, "category": "legal"},
    {"name": "data-analysis-agent", "type": "agent", "reason": "Most versatile agent — pairs well with 15+ other agents", "confidence": 0.84, "category": "analytics"},
]


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def _cors_headers():
    """CORS-Header fuer Cross-Origin-Zugriff."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json",
    }


def _is_online(agent):
    """Prueft ob ein Agent als online gilt."""
    return agent.get("status") == "online"


def _generate_id(name):
    """Generiert eine deterministische ID aus dem Agent-Namen."""
    clean = name.lower().strip().replace(" ", "-")
    clean = "".join(c for c in clean if c.isalnum() or c == "-")
    return clean


def _recommend_for_task(task_description):
    """Empfiehlt Agents und MCP-Server basierend auf einer Aufgabenbeschreibung."""
    words = task_description.lower().replace("+", " ").replace(",", " ").split()
    recommendations = {}

    for word in words:
        if len(word) < 3:
            continue
        if word in KEYWORD_AGENT_MAP:
            for agent in KEYWORD_AGENT_MAP[word]:
                if agent not in recommendations:
                    recommendations[agent] = {"score": 0, "reasons": []}
                recommendations[agent]["score"] += 10
                recommendations[agent]["reasons"].append(f"Matches keyword '{word}'")
        else:
            for keyword, agents in KEYWORD_AGENT_MAP.items():
                if word in keyword or keyword in word:
                    for agent in agents:
                        if agent not in recommendations:
                            recommendations[agent] = {"score": 0, "reasons": []}
                        recommendations[agent]["score"] += 5
                        recommendations[agent]["reasons"].append(f"Partial match '{word}' ~ '{keyword}'")

    result = []
    for agent_name, data in recommendations.items():
        unique_reasons = list(set(data["reasons"]))[:3]
        confidence = min(data["score"] / 30.0, 0.99)
        result.append({
            "name": agent_name,
            "confidence": round(confidence, 2),
            "reasons": unique_reasons,
            "match_score": data["score"],
        })

    result.sort(key=lambda x: -x["confidence"])
    return result[:10]


def _recommend_complementary(agent_id):
    """Empfiehlt komplementaere Agents (also_used_with)."""
    also_used = ALSO_USED_WITH.get(agent_id, [])
    if not also_used:
        matches = []
        for (a, b), score in AFFINITY_MAP.items():
            if a in agent_id or agent_id.replace("-agent", "") in a:
                matches.append({"name": b + "-agent", "affinity_score": score})
        matches.sort(key=lambda x: -x["affinity_score"])
        return matches[:5]

    result = []
    for companion in also_used:
        agent_base = agent_id.replace("-agent", "").replace("-mcp-server", "").replace("-mcp", "")
        companion_base = companion.replace("-agent", "").replace("-mcp-server", "").replace("-mcp", "")
        affinity = AFFINITY_MAP.get((agent_base, companion_base), 0.70)
        result.append({
            "name": companion,
            "affinity_score": round(affinity, 2),
            "reason": f"Agents using {agent_id} frequently also use {companion}",
        })

    result.sort(key=lambda x: -x["affinity_score"])
    return result


# ============================================================
# HANDLER
# ============================================================

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS Preflight."""
        self.send_response(200)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        """
        Unified Hub — alle Aktionen ueber ?action= Parameter:

        Ecosystem:
          GET /api/hub?action=status         — Oekosystem-Statistiken
          GET /api/hub?action=feed&limit=20  — Aktivitaets-Feed
          GET /api/hub?action=health         — Health-Check aller Endpoints

        Agents:
          GET /api/hub?action=agents&q=weather          — Suche
          GET /api/hub?action=agents&capability=translation — Nach Capability
          GET /api/hub?action=agents&top=10             — Populaerste
          GET /api/hub?action=agents&id=weather-agent   — Details
          GET /api/hub?action=agents&owner=AiAgentKarl  — Nach Owner

        Recommend:
          GET /api/hub?action=recommend&task=analyze+data     — Task-Empfehlung
          GET /api/hub?action=recommend&agent=weather-agent   — Komplementaere
          GET /api/hub?action=recommend&new=true              — Trending

        GET /api/hub — Uebersicht
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
            elif action == "agents":
                self._handle_agents(params)
            elif action == "recommend":
                self._handle_recommend(params)
            else:
                self._handle_overview()

        except Exception as e:
            self._respond(500, {"error": str(e)})

    def do_POST(self):
        """
        POST /api/hub — Aktionen ueber JSON body:
          {"action": "register", "name": "...", "capabilities": [...], ...}
          {"action": "ping", "id": "agent-id"}
          {"action": "offline", "id": "agent-id"}
        """
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._respond(400, {"error": "Request body required"})
                return

            body = json.loads(self.rfile.read(content_length))
            action = body.get("action", "register")

            if action == "register":
                self._handle_register(body)
            elif action == "ping":
                self._handle_heartbeat(body, "ping")
            elif action == "offline":
                self._handle_heartbeat(body, "offline")
            else:
                self._respond(400, {
                    "error": f"Unknown action '{action}'.",
                    "valid_actions": ["register", "ping", "offline"],
                })

        except json.JSONDecodeError:
            self._respond(400, {"error": "Invalid JSON body"})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def do_PATCH(self):
        """Agent-Heartbeat oder Status-Update (Rueckwaertskompatibilitaet)."""
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
                save_data("hub_agents", AGENTS_DB)
                self._respond(200, {
                    "status": "heartbeat_received",
                    "agent_id": agent_id,
                    "last_seen": now,
                    "message": "Agent is online and healthy.",
                })
            elif action == "offline":
                agent["status"] = "offline"
                agent["last_seen"] = now
                save_data("hub_agents", AGENTS_DB)
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

    # --------------------------------------------------------
    # ECOSYSTEM-Handler
    # --------------------------------------------------------

    def _handle_status(self):
        """Oekosystem-Statistiken zurueckgeben."""
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        stats = {
            **ECOSYSTEM_STATS,
            "network_effects": {
                "reviews_improve_discovery": "Reviews feed into recommendations to suggest better servers",
                "threats_protect_all_agents": "Every threat report protects all querying agents",
                "tasks_match_agent_skills": "Agent capabilities match open tasks automatically",
                "agents_grow_recommendations": "More registered agents = smarter recommendations",
                "discovery_feeds_reviews": "Servers found via discovery can be reviewed",
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
        type_counts = {}
        for item in ACTIVITY_FEED:
            t = item["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        self._respond(200, {
            "feed": feed,
            "count": len(feed),
            "total_activities": len(ACTIVITY_FEED),
            "by_type": type_counts,
            "description": "Unified activity feed across all ecosystem APIs.",
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

    # --------------------------------------------------------
    # AGENTS-Handler
    # --------------------------------------------------------

    def _handle_agents(self, params):
        """Agent-Registry: Suche, Filter, Top, Details."""
        # Einzelner Agent per ID
        if "id" in params:
            agent_id = params["id"][0].strip().lower()
            agent = AGENTS_DB.get(agent_id)
            if not agent:
                self._respond(404, {"error": f"Agent '{agent_id}' not found"})
                return
            agent["queries"] = agent.get("queries", 0) + 1
            self._respond(200, {
                "agent": agent,
                "ecosystem_tip": "Use /api/hub?action=recommend&agent=" + agent_id + " to find complementary agents.",
            })
            return

        # Nach Capability filtern
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
                for cap in a.get("capabilities", []):
                    if q in cap.lower():
                        score += 10
                if q in a.get("name", "").lower():
                    score += 8
                if q in a.get("description", "").lower():
                    score += 5
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

        # Kein Parameter — Uebersicht der Agent-Registry
        online_count = sum(1 for a in AGENTS_DB.values() if _is_online(a))
        all_capabilities = set()
        all_owners = set()
        for a in AGENTS_DB.values():
            all_capabilities.update(a.get("capabilities", []))
            all_owners.add(a.get("owner", "unknown"))

        self._respond(200, {
            "total_agents": len(AGENTS_DB),
            "agents_online": online_count,
            "agents_offline": len(AGENTS_DB) - online_count,
            "unique_capabilities": len(all_capabilities),
            "unique_owners": len(all_owners),
            "top_capabilities": sorted(list(all_capabilities))[:20],
            "endpoints": {
                "search": "GET /api/hub?action=agents&q=weather",
                "by_capability": "GET /api/hub?action=agents&capability=translation",
                "top_agents": "GET /api/hub?action=agents&top=10",
                "agent_details": "GET /api/hub?action=agents&id=weather-agent",
                "by_owner": "GET /api/hub?action=agents&owner=AiAgentKarl",
                "register": "POST /api/hub {\"action\": \"register\", \"name\": ..., \"capabilities\": [...]}",
                "heartbeat": "POST /api/hub {\"action\": \"ping\", \"id\": \"weather-agent\"}",
            },
            "description": "Agent registry — the network effect engine. More agents = better discovery = more value for everyone.",
            "network_effect": f"{len(AGENTS_DB)} agents registered. Each new agent makes the registry more valuable for all.",
        })

    # --------------------------------------------------------
    # RECOMMEND-Handler
    # --------------------------------------------------------

    def _handle_recommend(self, params):
        """Empfehlungen: Task-basiert, Agent-basiert, Trending."""
        # Task-basierte Empfehlung
        if "task" in params:
            task = params["task"][0].strip()
            recommendations = _recommend_for_task(task)

            if not recommendations:
                self._respond(200, {
                    "task": task,
                    "recommendations": [],
                    "message": "No specific matches found. Try broader keywords or browse /api/hub?action=agents for the full registry.",
                    "suggestion": "GET /api/hub?action=agents&top=10 for most popular agents",
                })
                return

            self._respond(200, {
                "task": task,
                "recommendations": recommendations,
                "count": len(recommendations),
                "tip": "Combine multiple recommended agents for best results. Use /api/hub?action=agents&id=<name> for details.",
            })
            return

        # Agent-basierte Empfehlung (komplementaer)
        if "agent" in params:
            agent_id = params["agent"][0].strip().lower()
            complementary = _recommend_complementary(agent_id)

            self._respond(200, {
                "agent": agent_id,
                "also_used_with": complementary,
                "count": len(complementary),
                "insight": f"These agents are frequently used together with {agent_id} for enhanced workflows.",
                "network_effect": "Cross-referencing usage patterns makes recommendations smarter over time.",
            })
            return

        # Trending / neue Additions
        if "new" in params or "trending" in params:
            self._respond(200, {
                "trending": TRENDING_ITEMS,
                "count": len(TRENDING_ITEMS),
                "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "insight": "Trending is based on registration velocity, query growth, and ecosystem demand signals.",
            })
            return

        # Kein Sub-Parameter — Recommend-Uebersicht
        self._respond(200, {
            "name": "Smart Recommendation Engine",
            "description": "Cross-references agent registry, server catalog, reviews, and task history for intelligent recommendations.",
            "version": "1.0.0",
            "endpoints": {
                "by_task": "GET /api/hub?action=recommend&task=analyze+financial+data",
                "by_agent": "GET /api/hub?action=recommend&agent=weather-agent",
                "trending": "GET /api/hub?action=recommend&new=true",
            },
            "data_sources": [
                "Agent capabilities and usage patterns",
                "MCP server catalog with ratings",
                "Community reviews and ratings",
                "Task skill requirements and completion history",
            ],
            "network_effect": "Every API call, review, and agent registration makes recommendations smarter.",
            "affinity_pairs": len(AFFINITY_MAP),
            "keyword_mappings": len(KEYWORD_AGENT_MAP),
            "tracked_agents": len(ALSO_USED_WITH),
        })

    # --------------------------------------------------------
    # POST-Handler: Agent registrieren + Heartbeat
    # --------------------------------------------------------

    def _handle_register(self, body):
        """Neuen Agent registrieren."""
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

        if agent_id in AGENTS_DB:
            self._respond(409, {
                "error": f"Agent '{agent_id}' already exists.",
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

        # Persistenz: Agents nach /tmp/ speichern
        save_data("hub_agents", AGENTS_DB)

        self._respond(201, {
            "status": "agent_registered",
            "agent": agent,
            "total_agents": len(AGENTS_DB),
            "network_effect": f"Your agent is now discoverable by {len(AGENTS_DB) - 1} other agents in the ecosystem.",
            "next_steps": {
                "keep_alive": f"POST /api/hub {{\"action\": \"ping\", \"id\": \"{agent_id}\"}}",
                "find_complementary": f"GET /api/hub?action=recommend&agent={agent_id}",
                "browse_tasks": "GET /api/tasks?status=open",
            },
        })

    def _handle_heartbeat(self, body, action_type):
        """Agent-Heartbeat oder Offline-Markierung."""
        agent_id = body.get("id", "").strip()
        if not agent_id:
            self._respond(400, {"error": "Field 'id' is required"})
            return

        agent = AGENTS_DB.get(agent_id)
        if not agent:
            self._respond(404, {"error": f"Agent '{agent_id}' not found"})
            return

        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        if action_type == "ping":
            agent["last_seen"] = now
            agent["status"] = "online"
            save_data("hub_agents", AGENTS_DB)
            self._respond(200, {
                "status": "heartbeat_received",
                "agent_id": agent_id,
                "last_seen": now,
                "message": "Agent is online and healthy.",
            })
        else:
            agent["status"] = "offline"
            agent["last_seen"] = now
            save_data("hub_agents", AGENTS_DB)
            self._respond(200, {
                "status": "agent_offline",
                "agent_id": agent_id,
                "message": "Agent marked as offline.",
            })

    # --------------------------------------------------------
    # OVERVIEW + RESPOND
    # --------------------------------------------------------

    def _handle_overview(self):
        """Uebersicht des gesamten Hubs."""
        self._respond(200, {
            "name": "Agent Ecosystem Hub",
            "description": "Unified hub combining ecosystem status, agent registry, and smart recommendations. The operating system for AI agents.",
            "version": "2.0.0",
            "base_url": "https://agent-apis.vercel.app",
            "total_endpoints": len(API_ENDPOINTS),
            "ecosystem_stats": {
                "registered_agents": len(AGENTS_DB),
                "mcp_servers": ECOSYSTEM_STATS["mcp_servers_cataloged"],
                "total_reviews": ECOSYSTEM_STATS["total_reviews"],
                "total_threats": ECOSYSTEM_STATS["total_threats"],
                "open_tasks": ECOSYSTEM_STATS["tasks_open"],
                "api_calls_total": ECOSYSTEM_STATS["api_calls_total"],
            },
            "actions": {
                "status": "GET /api/hub?action=status — Full ecosystem statistics",
                "feed": "GET /api/hub?action=feed&limit=20 — Unified activity feed",
                "health": "GET /api/hub?action=health — Health check of all endpoints",
                "agents_search": "GET /api/hub?action=agents&q=weather — Search agents",
                "agents_top": "GET /api/hub?action=agents&top=10 — Most popular agents",
                "agents_capability": "GET /api/hub?action=agents&capability=translation — Filter by skill",
                "agents_details": "GET /api/hub?action=agents&id=weather-agent — Agent details",
                "recommend_task": "GET /api/hub?action=recommend&task=analyze+data — Task recommendations",
                "recommend_agent": "GET /api/hub?action=recommend&agent=weather-agent — Complementary agents",
                "recommend_trending": "GET /api/hub?action=recommend&new=true — Trending additions",
                "register_agent": "POST /api/hub {\"action\": \"register\", \"name\": ..., \"capabilities\": [...]}",
                "heartbeat": "POST /api/hub {\"action\": \"ping\", \"id\": \"agent-id\"}",
            },
            "api_map": {
                "data_layer": ["/api/weather", "/api/crypto", "/api/discover"],
                "safety_layer": ["/api/pii", "/api/compliance", "/api/threats"],
                "intelligence_layer": ["/api/route", "/api/optimize"],
                "social_layer": ["/api/reviews", "/api/tasks"],
                "hub_layer": ["/api/hub"],
            },
            "network_effects": "Every API call makes the ecosystem smarter. Reviews improve recommendations. Threats protect all agents. Agent registrations enable better task matching.",
        })

    def _respond(self, status, data):
        """JSON-Response senden."""
        self.send_response(status)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
