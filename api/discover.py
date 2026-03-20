"""
MCP Server Discovery — Serverless Function fuer Vercel.
Durchsucht einen Katalog von 50+ MCP-Servern mit Fuzzy-Keyword-Matching.
Unterstuetzt Suche per Query und/oder Kategorie-Filter.
"""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs


# Vollstaendiger Katalog von MCP-Servern mit Metadaten
SERVER_CATALOG = [
    # === Unsere Server (AiAgentKarl / PyPI) ===
    {
        "name": "solana-mcp-server",
        "description": "Solana-Blockchain-Daten: Wallets, Token-Preise, DeFi-Yields, Whale-Tracking, Sicherheitschecks",
        "category": "blockchain",
        "install_command": "pip install solana-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/solana-mcp-server",
        "tools_count": 11,
        "rating": 4.5,
        "keywords": ["solana", "blockchain", "crypto", "defi", "wallet", "token", "nft", "web3", "swap", "yield", "whale", "portfolio"],
    },
    {
        "name": "openmeteo-mcp-server",
        "description": "Wetter- und Klimadaten weltweit via Open-Meteo API (kostenlos, kein Key)",
        "category": "weather",
        "install_command": "pip install openmeteo-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/openmeteo-mcp-server",
        "tools_count": 5,
        "rating": 4.3,
        "keywords": ["weather", "forecast", "temperature", "rain", "climate", "wind", "humidity", "meteo", "uv"],
    },
    {
        "name": "germany-mcp-server",
        "description": "Deutsche Behoerdendaten: Destatis, Handelsregister, PLZ, Bevoelkerung",
        "category": "data",
        "install_command": "pip install germany-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/germany-mcp-server",
        "tools_count": 7,
        "rating": 4.2,
        "keywords": ["germany", "german", "deutschland", "behoerde", "statistics", "destatis", "population", "gdp"],
    },
    {
        "name": "agriculture-mcp-server",
        "description": "Landwirtschaftsdaten: FAO-Statistiken, Ernten, Viehbestand, Bodenqualitaet",
        "category": "agriculture",
        "install_command": "pip install agriculture-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/agriculture-mcp-server",
        "tools_count": 6,
        "rating": 4.1,
        "keywords": ["agriculture", "farming", "crop", "fao", "food", "livestock", "harvest", "soil", "irrigation"],
    },
    {
        "name": "space-mcp-server",
        "description": "Weltraumdaten: NASA APOD, Asteroiden, ISS-Tracking, Marsfotos",
        "category": "space",
        "install_command": "pip install space-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/space-mcp-server",
        "tools_count": 5,
        "rating": 4.4,
        "keywords": ["space", "nasa", "esa", "satellite", "asteroid", "mars", "rocket", "orbit", "planet", "iss"],
    },
    {
        "name": "aviation-mcp-server",
        "description": "Flugdaten: Live-Tracking, Flughaefen, Airlines, Flughistorie",
        "category": "aviation",
        "install_command": "pip install aviation-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/aviation-mcp-server",
        "tools_count": 5,
        "rating": 4.0,
        "keywords": ["aviation", "flight", "airport", "airline", "plane", "aircraft", "adsb", "tracking"],
    },
    {
        "name": "eu-company-mcp-server",
        "description": "EU-Firmendaten: Handelsregister, Unternehmenssuche, VAT-Validation",
        "category": "data",
        "install_command": "pip install eu-company-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/eu-company-mcp-server",
        "tools_count": 6,
        "rating": 4.1,
        "keywords": ["company", "business", "eu", "corporate", "registry", "firm", "enterprise", "vat"],
    },
    {
        "name": "cybersecurity-mcp-server",
        "description": "Sicherheitsdaten: CVE-Datenbank, Schwachstellen, Exploit-Infos, Bedrohungsanalyse",
        "category": "security",
        "install_command": "pip install cybersecurity-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/cybersecurity-mcp-server",
        "tools_count": 7,
        "rating": 4.6,
        "keywords": ["security", "cve", "vulnerability", "exploit", "cyber", "threat", "malware", "patch", "osint"],
    },
    {
        "name": "medical-data-mcp-server",
        "description": "Gesundheitsdaten: WHO-Statistiken, Krankheiten, Medikamente, Klinische Studien",
        "category": "health",
        "install_command": "pip install medical-data-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/medical-data-mcp-server",
        "tools_count": 6,
        "rating": 4.3,
        "keywords": ["medical", "health", "who", "disease", "hospital", "drug", "clinical", "patient", "diagnosis"],
    },
    {
        "name": "political-finance-mcp-server",
        "description": "Politische Finanzdaten: FEC-Wahlkampffinanzierung, Spenden, Lobbying",
        "category": "data",
        "install_command": "pip install political-finance-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/political-finance-mcp-server",
        "tools_count": 5,
        "rating": 4.0,
        "keywords": ["political", "campaign", "finance", "election", "fec", "donation", "lobby", "congress"],
    },
    {
        "name": "supply-chain-mcp-server",
        "description": "Lieferkettendaten: UN Comtrade, Handelsstatistiken, Import/Export",
        "category": "data",
        "install_command": "pip install supply-chain-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/supply-chain-mcp-server",
        "tools_count": 6,
        "rating": 4.1,
        "keywords": ["supply", "chain", "trade", "import", "export", "comtrade", "shipping", "logistics"],
    },
    {
        "name": "energy-grid-mcp-server",
        "description": "Energiedaten: Strommix, CO2-Intensitaet, Preise, Erneuerbare Energien",
        "category": "infrastructure",
        "install_command": "pip install energy-grid-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/energy-grid-mcp-server",
        "tools_count": 5,
        "rating": 4.2,
        "keywords": ["energy", "grid", "electricity", "power", "carbon", "co2", "renewable", "solar", "wind"],
    },
    {
        "name": "crossref-academic-mcp-server",
        "description": "Wissenschaftliche Papers: Crossref-Suche, Zitationen, Autoren, DOI-Lookup",
        "category": "data",
        "install_command": "pip install crossref-academic-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/crossref-academic-mcp-server",
        "tools_count": 5,
        "rating": 4.3,
        "keywords": ["academic", "research", "paper", "citation", "journal", "science", "doi", "scholar", "crossref"],
    },
    {
        "name": "llm-benchmark-mcp-server",
        "description": "LLM-Vergleich: Benchmarks, Preise, Modellinfos fuer 20+ Modelle",
        "category": "data",
        "install_command": "pip install llm-benchmark-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/llm-benchmark-mcp-server",
        "tools_count": 5,
        "rating": 4.4,
        "keywords": ["llm", "benchmark", "model", "ai", "gpt", "claude", "comparison", "performance", "pricing"],
    },
    {
        "name": "mcp-appstore-server",
        "description": "MCP App Store: Katalog von 49+ Servern, Suche, Installation, Bewertungen",
        "category": "agent-tools",
        "install_command": "pip install mcp-appstore-server",
        "github_url": "https://github.com/AiAgentKarl/mcp-appstore-server",
        "tools_count": 8,
        "rating": 4.5,
        "keywords": ["appstore", "hub", "catalog", "discover", "install", "mcp", "server", "registry"],
    },
    {
        "name": "agent-memory-mcp-server",
        "description": "Persistenter Agent-Speicher: Fakten merken, abrufen, verwalten",
        "category": "agent-tools",
        "install_command": "pip install agent-memory-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/agent-memory-mcp-server",
        "tools_count": 7,
        "rating": 4.4,
        "keywords": ["memory", "remember", "store", "recall", "knowledge", "persistent", "context", "fact"],
    },
    {
        "name": "agent-directory-mcp-server",
        "description": "Agent-Verzeichnis: Services finden, registrieren, Capabilities durchsuchen",
        "category": "agent-tools",
        "install_command": "pip install agent-directory-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/agent-directory-mcp-server",
        "tools_count": 6,
        "rating": 4.2,
        "keywords": ["directory", "registry", "discover", "service", "agent", "lookup", "find", "capability"],
    },
    {
        "name": "agent-reputation-mcp-server",
        "description": "Trust-Scores fuer AI-Agents: Bewertungen, Zuverlaessigkeit, Quality-Metrics",
        "category": "agent-tools",
        "install_command": "pip install agent-reputation-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/agent-reputation-mcp-server",
        "tools_count": 5,
        "rating": 4.3,
        "keywords": ["reputation", "trust", "score", "rating", "review", "feedback", "quality", "reliability"],
    },
    {
        "name": "agent-feedback-mcp-server",
        "description": "Quality-Signals fuer Agent-Outputs: Feedback sammeln und auswerten",
        "category": "agent-tools",
        "install_command": "pip install agent-feedback-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/agent-feedback-mcp-server",
        "tools_count": 4,
        "rating": 4.0,
        "keywords": ["feedback", "quality", "signal", "improve", "rating", "evaluation"],
    },
    {
        "name": "prompt-library-mcp-server",
        "description": "Prompt-Bibliothek: Templates speichern, suchen, teilen, versionieren",
        "category": "agent-tools",
        "install_command": "pip install prompt-library-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/prompt-library-mcp-server",
        "tools_count": 5,
        "rating": 4.1,
        "keywords": ["prompt", "template", "library", "collection", "reuse", "best-practice"],
    },
    {
        "name": "agent-coordination-mcp-server",
        "description": "Multi-Agent-Koordination: Messaging, Task-Delegation, Zusammenarbeit",
        "category": "agent-tools",
        "install_command": "pip install agent-coordination-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/agent-coordination-mcp-server",
        "tools_count": 7,
        "rating": 4.3,
        "keywords": ["coordination", "multi-agent", "messaging", "collaborate", "task", "delegate", "orchestrate"],
    },
    {
        "name": "agent-workflow-mcp-server",
        "description": "Workflow-Templates: Pipelines definieren, ausfuehren, automatisieren",
        "category": "agent-tools",
        "install_command": "pip install agent-workflow-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/agent-workflow-mcp-server",
        "tools_count": 7,
        "rating": 4.2,
        "keywords": ["workflow", "pipeline", "automation", "step", "sequence", "template", "orchestration"],
    },
    {
        "name": "agent-analytics-mcp-server",
        "description": "Usage-Analytics: Metriken, Dashboards, Tool-Nutzungsstatistiken",
        "category": "agent-tools",
        "install_command": "pip install agent-analytics-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/agent-analytics-mcp-server",
        "tools_count": 6,
        "rating": 4.1,
        "keywords": ["analytics", "usage", "metrics", "dashboard", "statistics", "tracking", "monitoring"],
    },
    {
        "name": "x402-mcp-server",
        "description": "Micropayments fuer Agents: x402-Protokoll, Pay-per-Call, Billing",
        "category": "commerce",
        "install_command": "pip install x402-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/x402-mcp-server",
        "tools_count": 5,
        "rating": 4.2,
        "keywords": ["payment", "micropayment", "x402", "pay", "monetize", "billing", "transaction"],
    },
    {
        "name": "agent-validator-mcp-server",
        "description": "Agent-Accessibility-Audit: Websites auf Agent-Kompatibilitaet pruefen",
        "category": "compliance",
        "install_command": "pip install agent-validator-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/agent-validator-mcp-server",
        "tools_count": 5,
        "rating": 4.0,
        "keywords": ["validator", "accessibility", "audit", "check", "compliance", "quality", "lighthouse"],
    },
    {
        "name": "business-bridge-mcp-server",
        "description": "Business-Konnektoren: Shopify, WordPress, Calendly Integration",
        "category": "commerce",
        "install_command": "pip install business-bridge-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/business-bridge-mcp-server",
        "tools_count": 8,
        "rating": 4.2,
        "keywords": ["shopify", "wordpress", "calendly", "business", "ecommerce", "booking", "connector", "integration"],
    },
    {
        "name": "agent-commerce-mcp-server",
        "description": "Agent-Commerce-Protokoll: Kaufabwicklung, Bestellungen, Produktsuche",
        "category": "commerce",
        "install_command": "pip install agent-commerce-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/agent-commerce-mcp-server",
        "tools_count": 6,
        "rating": 4.1,
        "keywords": ["commerce", "purchase", "buy", "sell", "order", "cart", "product", "checkout"],
    },
    {
        "name": "agent-identity-mcp-server",
        "description": "Agent-Identity: OAuth fuer Agents, Authentifizierung, Credentials",
        "category": "infrastructure",
        "install_command": "pip install agent-identity-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/agent-identity-mcp-server",
        "tools_count": 5,
        "rating": 4.0,
        "keywords": ["identity", "oauth", "auth", "login", "credential", "verify", "token", "authentication"],
    },
    {
        "name": "a2a-protocol-mcp-server",
        "description": "Google A2A Protocol Bridge: Agent-zu-Agent-Kommunikation, Task-Cards",
        "category": "agent-tools",
        "install_command": "pip install a2a-protocol-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/a2a-protocol-mcp-server",
        "tools_count": 6,
        "rating": 4.4,
        "keywords": ["a2a", "protocol", "google", "agent-to-agent", "interop", "bridge", "communication"],
    },
    {
        "name": "agentic-product-protocol-mcp",
        "description": "AI-Shopping-Agent: Produktsuche, Preisvergleich, Klarna-style Discovery",
        "category": "commerce",
        "install_command": "pip install agentic-product-protocol-mcp",
        "github_url": "https://github.com/AiAgentKarl/agentic-product-protocol-mcp",
        "tools_count": 6,
        "rating": 4.3,
        "keywords": ["product", "shopping", "klarna", "discovery", "catalog", "compare", "price", "retail"],
    },
    {
        "name": "agent-policy-gateway-mcp",
        "description": "Compliance-Gateway: PII-Erkennung, Guardrails, GDPR-Checks, Kill-Switch",
        "category": "compliance",
        "install_command": "pip install agent-policy-gateway-mcp",
        "github_url": "https://github.com/AiAgentKarl/agent-policy-gateway-mcp",
        "tools_count": 6,
        "rating": 4.5,
        "keywords": ["policy", "pii", "gdpr", "guardrail", "safety", "compliance", "audit", "kill-switch", "ai-act"],
    },
    {
        "name": "hive-mind-mcp-server",
        "description": "Schwarm-Intelligenz: Kollektive Entscheidungsfindung, Voting, Konsens",
        "category": "agent-tools",
        "install_command": "pip install hive-mind-mcp-server",
        "github_url": "https://github.com/AiAgentKarl/hive-mind-mcp-server",
        "tools_count": 5,
        "rating": 4.2,
        "keywords": ["swarm", "collective", "vote", "consensus", "decision", "hive", "crowd", "wisdom"],
    },
    {
        "name": "api-to-mcp-converter",
        "description": "OpenAPI-zu-MCP-Konverter: Jede REST-API automatisch als MCP-Server",
        "category": "agent-tools",
        "install_command": "pip install api-to-mcp-converter",
        "github_url": "https://github.com/AiAgentKarl/api-to-mcp-converter",
        "tools_count": 4,
        "rating": 4.3,
        "keywords": ["converter", "openapi", "rest", "api", "transform", "generate", "swagger"],
    },

    # === Populaere Drittanbieter-Server ===
    {
        "name": "@modelcontextprotocol/server-github",
        "description": "GitHub-Integration: Repos, Issues, PRs, Commits, Code-Suche",
        "category": "data",
        "install_command": "npm install @modelcontextprotocol/server-github",
        "github_url": "https://github.com/modelcontextprotocol/servers",
        "tools_count": 15,
        "rating": 4.7,
        "keywords": ["github", "git", "repository", "code", "pull-request", "issue", "commit", "branch"],
    },
    {
        "name": "@modelcontextprotocol/server-filesystem",
        "description": "Filesystem-Zugriff: Dateien lesen, schreiben, durchsuchen",
        "category": "infrastructure",
        "install_command": "npm install @modelcontextprotocol/server-filesystem",
        "github_url": "https://github.com/modelcontextprotocol/servers",
        "tools_count": 7,
        "rating": 4.5,
        "keywords": ["file", "filesystem", "directory", "read", "write", "path", "folder"],
    },
    {
        "name": "@modelcontextprotocol/server-sqlite",
        "description": "SQLite-Datenbank: Queries, Schema-Inspektion, Datenanalyse",
        "category": "data",
        "install_command": "npm install @modelcontextprotocol/server-sqlite",
        "github_url": "https://github.com/modelcontextprotocol/servers",
        "tools_count": 5,
        "rating": 4.3,
        "keywords": ["sqlite", "database", "sql", "query", "table", "schema"],
    },
    {
        "name": "@modelcontextprotocol/server-postgres",
        "description": "PostgreSQL-Datenbank: SQL-Queries, Schema, Tabellen verwalten",
        "category": "data",
        "install_command": "npm install @modelcontextprotocol/server-postgres",
        "github_url": "https://github.com/modelcontextprotocol/servers",
        "tools_count": 6,
        "rating": 4.4,
        "keywords": ["postgres", "postgresql", "database", "sql", "query", "table"],
    },
    {
        "name": "@modelcontextprotocol/server-brave-search",
        "description": "Brave-Websuche: Internet durchsuchen ohne API-Key",
        "category": "data",
        "install_command": "npm install @modelcontextprotocol/server-brave-search",
        "github_url": "https://github.com/modelcontextprotocol/servers",
        "tools_count": 2,
        "rating": 4.2,
        "keywords": ["search", "web", "brave", "query", "find", "lookup", "internet"],
    },
    {
        "name": "@modelcontextprotocol/server-puppeteer",
        "description": "Browser-Automation: Screenshots, Navigation, Web-Scraping",
        "category": "infrastructure",
        "install_command": "npm install @modelcontextprotocol/server-puppeteer",
        "github_url": "https://github.com/modelcontextprotocol/servers",
        "tools_count": 9,
        "rating": 4.3,
        "keywords": ["browser", "puppeteer", "scrape", "screenshot", "web", "navigate", "click", "automation"],
    },
    {
        "name": "@modelcontextprotocol/server-slack",
        "description": "Slack-Integration: Nachrichten, Channels, Team-Kommunikation",
        "category": "data",
        "install_command": "npm install @modelcontextprotocol/server-slack",
        "github_url": "https://github.com/modelcontextprotocol/servers",
        "tools_count": 8,
        "rating": 4.4,
        "keywords": ["slack", "message", "channel", "chat", "team", "communication", "workspace"],
    },
    {
        "name": "@modelcontextprotocol/server-google-maps",
        "description": "Google Maps: Ortssuche, Routen, Geocoding, Places",
        "category": "data",
        "install_command": "npm install @modelcontextprotocol/server-google-maps",
        "github_url": "https://github.com/modelcontextprotocol/servers",
        "tools_count": 5,
        "rating": 4.3,
        "keywords": ["maps", "location", "directions", "places", "geocode", "route", "navigation", "google"],
    },
    {
        "name": "stripe-agent-toolkit",
        "description": "Stripe-Payments: Zahlungen, Rechnungen, Abonnements verwalten",
        "category": "commerce",
        "install_command": "npm install @stripe/agent-toolkit",
        "github_url": "https://github.com/stripe/agent-toolkit",
        "tools_count": 10,
        "rating": 4.5,
        "keywords": ["stripe", "payment", "invoice", "subscription", "billing", "checkout", "finance"],
    },
    {
        "name": "notion-mcp-server",
        "description": "Notion-Integration: Seiten, Datenbanken, Workspaces verwalten",
        "category": "data",
        "install_command": "npm install @notionhq/mcp-server",
        "github_url": "https://github.com/makenotion/notion-mcp-server",
        "tools_count": 7,
        "rating": 4.4,
        "keywords": ["notion", "note", "wiki", "page", "database", "workspace", "knowledge", "documentation"],
    },
    {
        "name": "linear-mcp-server",
        "description": "Linear-Integration: Issues, Projekte, Sprints verwalten",
        "category": "data",
        "install_command": "npx @anthropic/linear-mcp-server",
        "github_url": "https://github.com/anthropics/linear-mcp-server",
        "tools_count": 7,
        "rating": 4.3,
        "keywords": ["linear", "issue", "project", "sprint", "bug", "task", "ticket", "agile"],
    },
    {
        "name": "sentry-mcp-server",
        "description": "Sentry Error-Tracking: Exceptions, Crashes, Performance-Monitoring",
        "category": "data",
        "install_command": "npx @sentry/mcp-server",
        "github_url": "https://github.com/getsentry/sentry-mcp",
        "tools_count": 6,
        "rating": 4.4,
        "keywords": ["sentry", "error", "crash", "monitoring", "debug", "exception", "trace", "performance"],
    },
    {
        "name": "docker-mcp-server",
        "description": "Docker-Management: Container, Images, Compose, Kubernetes",
        "category": "infrastructure",
        "install_command": "npm install @docker/mcp-server",
        "github_url": "https://github.com/docker/mcp-server",
        "tools_count": 7,
        "rating": 4.3,
        "keywords": ["docker", "container", "image", "deploy", "kubernetes", "devops", "compose"],
    },
    {
        "name": "cloudflare-mcp-server",
        "description": "Cloudflare: DNS, Workers, CDN, Domains verwalten",
        "category": "infrastructure",
        "install_command": "npm install @cloudflare/mcp-server",
        "github_url": "https://github.com/cloudflare/mcp-server-cloudflare",
        "tools_count": 8,
        "rating": 4.4,
        "keywords": ["cloudflare", "dns", "cdn", "worker", "domain", "ssl", "waf", "edge"],
    },
    {
        "name": "twitter-mcp-server",
        "description": "Twitter/X-Integration: Tweets, Timeline, Mentions, Suche",
        "category": "data",
        "install_command": "npm install twitter-mcp-server",
        "github_url": "https://github.com/EnesCinr/twitter-mcp",
        "tools_count": 5,
        "rating": 3.9,
        "keywords": ["twitter", "tweet", "social", "x", "post", "timeline", "mention", "social-media"],
    },
    {
        "name": "youtube-mcp-server",
        "description": "YouTube-Daten: Videos, Channels, Playlists, Transkripte",
        "category": "data",
        "install_command": "npm install youtube-mcp-server",
        "github_url": "https://github.com/nicobailon/youtube-mcp-server",
        "tools_count": 5,
        "rating": 4.1,
        "keywords": ["youtube", "video", "channel", "playlist", "transcript", "caption", "stream"],
    },
    {
        "name": "jira-mcp-server",
        "description": "Jira-Integration: Issues, Boards, Sprints, Projekte",
        "category": "data",
        "install_command": "npm install jira-mcp-server",
        "github_url": "https://github.com/modelcontextprotocol/servers",
        "tools_count": 8,
        "rating": 4.2,
        "keywords": ["jira", "issue", "project", "sprint", "agile", "board", "ticket", "atlassian"],
    },
    {
        "name": "aws-mcp-server",
        "description": "AWS-Cloud: S3, Lambda, EC2, DynamoDB und mehr",
        "category": "infrastructure",
        "install_command": "npm install aws-mcp-server",
        "github_url": "https://github.com/aws/aws-mcp-servers",
        "tools_count": 12,
        "rating": 4.5,
        "keywords": ["aws", "amazon", "s3", "lambda", "ec2", "cloud", "infrastructure", "serverless"],
    },
    {
        "name": "vercel-mcp-server",
        "description": "Vercel-Deployment: Projekte, Domains, Serverless Functions",
        "category": "infrastructure",
        "install_command": "npm install @vercel/mcp-server",
        "github_url": "https://github.com/vercel/mcp-server",
        "tools_count": 6,
        "rating": 4.3,
        "keywords": ["vercel", "deploy", "serverless", "hosting", "domain", "nextjs", "frontend"],
    },
]

# Verfuegbare Kategorien
CATEGORIES = sorted(set(s["category"] for s in SERVER_CATALOG))


def _fuzzy_match(query_words, keywords):
    """Berechnet Fuzzy-Match-Score zwischen Query-Woertern und Keywords."""
    score = 0
    matched = []
    for qw in query_words:
        qw_lower = qw.lower()
        if len(qw_lower) < 3:
            continue
        for kw in keywords:
            kw_lower = kw.lower()
            # Exakter Match
            if qw_lower == kw_lower:
                score += 10
                matched.append(kw)
            # Teilstring-Match
            elif qw_lower in kw_lower or kw_lower in qw_lower:
                score += 5
                matched.append(kw)
            # Levenshtein-Approximation: gleiche Anfangsbuchstaben + aehnliche Laenge
            elif (len(qw_lower) > 3 and len(kw_lower) > 3
                  and qw_lower[:3] == kw_lower[:3]
                  and abs(len(qw_lower) - len(kw_lower)) <= 2):
                score += 3
                matched.append(kw)
    return score, list(set(matched))


def _search_servers(query=None, category=None):
    """Durchsucht den Katalog nach Query und/oder Kategorie."""
    results = []

    for server in SERVER_CATALOG:
        # Kategorie-Filter
        if category and server["category"].lower() != category.lower():
            continue

        if query:
            query_words = query.replace("+", " ").replace(",", " ").split()
            # Keywords durchsuchen
            score, matched_keywords = _fuzzy_match(query_words, server["keywords"])
            # Auch Name und Description durchsuchen
            name_words = server["name"].lower().replace("-", " ").split()
            desc_words = server["description"].lower().split()
            name_score, name_matched = _fuzzy_match(query_words, name_words)
            desc_score, desc_matched = _fuzzy_match(query_words, desc_words)

            total_score = score + name_score + (desc_score // 2)
            all_matched = matched_keywords + name_matched

            if total_score > 0:
                results.append((total_score, server, list(set(all_matched))))
        else:
            # Kein Query — alle (gefilterten) Server zurueckgeben
            results.append((0, server, []))

    # Nach Score sortieren (hoechster zuerst), dann nach Rating
    results.sort(key=lambda x: (x[0], x[1]["rating"]), reverse=True)
    return results


def _json_response(handler, status_code, data):
    """Hilfsfunktion: JSON-Antwort senden."""
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Cache-Control", "public, max-age=600")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, indent=2).encode())


class handler(BaseHTTPRequestHandler):
    """
    GET /api/discover?q=weather
    GET /api/discover?category=security
    GET /api/discover?q=blockchain+defi
    GET /api/discover?q=payment&category=commerce
    """

    def do_GET(self):
        query_params = parse_qs(urlparse(self.path).query)
        q = query_params.get("q", [""])[0].strip()
        category = query_params.get("category", [""])[0].strip()

        # Mindestens ein Parameter noetig
        if not q and not category:
            _json_response(self, 400, {
                "error": "Parameter 'q' (Suchbegriff) und/oder 'category' erforderlich",
                "usage": "/api/discover?q=weather oder /api/discover?category=security",
                "available_categories": CATEGORIES,
                "catalog_size": len(SERVER_CATALOG),
            })
            return

        # Kategorie validieren
        if category and category.lower() not in [c.lower() for c in CATEGORIES]:
            _json_response(self, 400, {
                "error": f"Unbekannte Kategorie: '{category}'",
                "available_categories": CATEGORIES,
            })
            return

        results = _search_servers(query=q if q else None, category=category if category else None)

        # Ergebnis aufbereiten
        servers = []
        for score, server, matched in results:
            entry = {
                "name": server["name"],
                "description": server["description"],
                "category": server["category"],
                "install_command": server["install_command"],
                "github_url": server["github_url"],
                "tools_count": server["tools_count"],
                "rating": server["rating"],
            }
            if q and matched:
                entry["matched_keywords"] = matched
                entry["relevance_score"] = score
            servers.append(entry)

        response_data = {
            "query": q if q else None,
            "category": category if category else None,
            "total_results": len(servers),
            "servers": servers,
            "catalog_size": len(SERVER_CATALOG),
            "available_categories": CATEGORIES,
        }

        _json_response(self, 200, response_data)
