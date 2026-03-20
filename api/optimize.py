"""
Context Optimizer — Serverless Function fuer Vercel.
Empfiehlt optimale MCP-Server-Kombination fuer eine Aufgabe
und berechnet Token-Einsparungen.
"""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs


# Katalog von 55+ MCP-Servern mit Keywords und Token-Schaetzung
# Token-Schaetzung basiert auf Anzahl der Tools * ~400-800 Tokens pro Tool-Schema
SERVER_CATALOG = [
    # === Unsere Server (AiAgentKarl) ===
    {"name": "solana-mcp-server", "category": "blockchain", "estimated_tokens": 5500, "tools_count": 11,
     "keywords": ["solana", "blockchain", "crypto", "defi", "wallet", "token", "nft", "web3", "swap", "yield", "whale"]},
    {"name": "openmeteo-mcp-server", "category": "weather", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["weather", "forecast", "temperature", "rain", "climate", "wind", "humidity", "meteo"]},
    {"name": "germany-mcp-server", "category": "data", "estimated_tokens": 4000, "tools_count": 7,
     "keywords": ["germany", "german", "deutschland", "behoerde", "statistics", "destatis", "population", "gdp"]},
    {"name": "agriculture-mcp-server", "category": "agriculture", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["agriculture", "farming", "crop", "fao", "food", "livestock", "harvest", "soil"]},
    {"name": "space-mcp-server", "category": "space", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["space", "nasa", "esa", "satellite", "asteroid", "mars", "rocket", "orbit", "planet"]},
    {"name": "aviation-mcp-server", "category": "aviation", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["aviation", "flight", "airport", "airline", "plane", "aircraft", "adsb", "tracking"]},
    {"name": "eu-company-mcp-server", "category": "data", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["company", "business", "eu", "corporate", "registry", "firm", "enterprise", "vat"]},
    {"name": "cybersecurity-mcp-server", "category": "security", "estimated_tokens": 4000, "tools_count": 7,
     "keywords": ["security", "cve", "vulnerability", "exploit", "cyber", "threat", "malware", "patch"]},
    {"name": "medical-data-mcp-server", "category": "health", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["medical", "health", "who", "disease", "hospital", "drug", "clinical", "patient"]},
    {"name": "political-finance-mcp-server", "category": "data", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["political", "campaign", "finance", "election", "fec", "donation", "lobby", "congress"]},
    {"name": "supply-chain-mcp-server", "category": "data", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["supply", "chain", "trade", "import", "export", "comtrade", "shipping", "logistics"]},
    {"name": "energy-grid-mcp-server", "category": "infrastructure", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["energy", "grid", "electricity", "power", "carbon", "co2", "renewable", "solar", "wind"]},
    {"name": "crossref-academic-mcp-server", "category": "data", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["academic", "research", "paper", "citation", "journal", "science", "doi", "scholar"]},
    {"name": "llm-benchmark-mcp-server", "category": "data", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["llm", "benchmark", "model", "ai", "gpt", "claude", "comparison", "performance"]},
    {"name": "mcp-appstore-server", "category": "agent-tools", "estimated_tokens": 5000, "tools_count": 8,
     "keywords": ["appstore", "hub", "catalog", "discover", "install", "mcp", "server", "registry"]},
    {"name": "agent-memory-mcp-server", "category": "agent-tools", "estimated_tokens": 4000, "tools_count": 7,
     "keywords": ["memory", "remember", "store", "recall", "knowledge", "persistent", "context"]},
    {"name": "agent-directory-mcp-server", "category": "agent-tools", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["directory", "registry", "discover", "service", "agent", "lookup", "find"]},
    {"name": "agent-reputation-mcp-server", "category": "agent-tools", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["reputation", "trust", "score", "rating", "review", "feedback", "quality"]},
    {"name": "agent-feedback-mcp-server", "category": "agent-tools", "estimated_tokens": 2500, "tools_count": 4,
     "keywords": ["feedback", "quality", "signal", "improve", "rating"]},
    {"name": "prompt-library-mcp-server", "category": "agent-tools", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["prompt", "template", "library", "collection", "reuse", "best-practice"]},
    {"name": "agent-coordination-mcp-server", "category": "agent-tools", "estimated_tokens": 4000, "tools_count": 7,
     "keywords": ["coordination", "multi-agent", "messaging", "collaborate", "task", "delegate"]},
    {"name": "agent-workflow-mcp-server", "category": "agent-tools", "estimated_tokens": 4000, "tools_count": 7,
     "keywords": ["workflow", "pipeline", "automation", "step", "sequence", "template"]},
    {"name": "agent-analytics-mcp-server", "category": "agent-tools", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["analytics", "usage", "metrics", "dashboard", "statistics", "tracking"]},
    {"name": "x402-mcp-server", "category": "commerce", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["payment", "micropayment", "x402", "pay", "monetize", "billing", "transaction"]},
    {"name": "agent-interface-standard", "category": "infrastructure", "estimated_tokens": 2500, "tools_count": 4,
     "keywords": ["interface", "schema", "standard", "api", "specification", "definition"]},
    {"name": "agent-validator-mcp-server", "category": "compliance", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["validator", "accessibility", "audit", "check", "compliance", "quality"]},
    {"name": "business-bridge-mcp-server", "category": "commerce", "estimated_tokens": 4500, "tools_count": 8,
     "keywords": ["shopify", "wordpress", "calendly", "business", "ecommerce", "booking", "connector"]},
    {"name": "agent-commerce-mcp-server", "category": "commerce", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["commerce", "purchase", "buy", "sell", "order", "cart", "product"]},
    {"name": "agent-identity-mcp-server", "category": "infrastructure", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["identity", "oauth", "auth", "login", "credential", "verify", "token"]},
    {"name": "a2a-protocol-mcp-server", "category": "agent-tools", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["a2a", "protocol", "google", "agent-to-agent", "interop", "bridge"]},
    {"name": "agentic-product-protocol-mcp", "category": "commerce", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["product", "shopping", "klarna", "discovery", "catalog", "compare", "price"]},
    {"name": "agent-policy-gateway-mcp", "category": "compliance", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["policy", "pii", "gdpr", "guardrail", "safety", "compliance", "audit", "kill-switch"]},
    {"name": "hive-mind-mcp-server", "category": "agent-tools", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["swarm", "collective", "vote", "consensus", "decision", "hive", "crowd"]},

    # === Populaere Drittanbieter-Server ===
    {"name": "github-mcp-server", "category": "data", "estimated_tokens": 8000, "tools_count": 15,
     "keywords": ["github", "git", "repository", "code", "pull-request", "issue", "commit", "branch"]},
    {"name": "filesystem-mcp-server", "category": "infrastructure", "estimated_tokens": 4000, "tools_count": 7,
     "keywords": ["file", "filesystem", "directory", "read", "write", "path", "folder"]},
    {"name": "sqlite-mcp-server", "category": "data", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["sqlite", "database", "sql", "query", "table", "schema"]},
    {"name": "postgres-mcp-server", "category": "data", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["postgres", "postgresql", "database", "sql", "query", "table"]},
    {"name": "brave-search-mcp-server", "category": "data", "estimated_tokens": 2000, "tools_count": 2,
     "keywords": ["search", "web", "brave", "query", "find", "lookup", "internet"]},
    {"name": "puppeteer-mcp-server", "category": "infrastructure", "estimated_tokens": 5000, "tools_count": 9,
     "keywords": ["browser", "puppeteer", "scrape", "screenshot", "web", "navigate", "click"]},
    {"name": "slack-mcp-server", "category": "data", "estimated_tokens": 4500, "tools_count": 8,
     "keywords": ["slack", "message", "channel", "chat", "team", "communication"]},
    {"name": "google-drive-mcp-server", "category": "data", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["google", "drive", "document", "spreadsheet", "file", "share"]},
    {"name": "google-maps-mcp-server", "category": "data", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["maps", "location", "directions", "places", "geocode", "route", "navigation"]},
    {"name": "stripe-mcp-server", "category": "commerce", "estimated_tokens": 5500, "tools_count": 10,
     "keywords": ["stripe", "payment", "invoice", "subscription", "billing", "checkout"]},
    {"name": "notion-mcp-server", "category": "data", "estimated_tokens": 4000, "tools_count": 7,
     "keywords": ["notion", "note", "wiki", "page", "database", "workspace", "knowledge"]},
    {"name": "linear-mcp-server", "category": "data", "estimated_tokens": 4000, "tools_count": 7,
     "keywords": ["linear", "issue", "project", "sprint", "bug", "task", "ticket"]},
    {"name": "sentry-mcp-server", "category": "data", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["sentry", "error", "crash", "monitoring", "debug", "exception", "trace"]},
    {"name": "docker-mcp-server", "category": "infrastructure", "estimated_tokens": 4000, "tools_count": 7,
     "keywords": ["docker", "container", "image", "deploy", "kubernetes", "devops"]},
    {"name": "cloudflare-mcp-server", "category": "infrastructure", "estimated_tokens": 4500, "tools_count": 8,
     "keywords": ["cloudflare", "dns", "cdn", "worker", "domain", "ssl", "waf"]},
    {"name": "twitter-mcp-server", "category": "data", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["twitter", "tweet", "social", "x", "post", "timeline", "mention"]},
    {"name": "youtube-mcp-server", "category": "data", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["youtube", "video", "channel", "playlist", "transcript", "caption"]},
    {"name": "email-mcp-server", "category": "data", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["email", "mail", "inbox", "send", "smtp", "imap", "newsletter"]},
    {"name": "calendar-mcp-server", "category": "data", "estimated_tokens": 3000, "tools_count": 5,
     "keywords": ["calendar", "event", "schedule", "meeting", "appointment", "booking"]},
    {"name": "jira-mcp-server", "category": "data", "estimated_tokens": 4500, "tools_count": 8,
     "keywords": ["jira", "issue", "project", "sprint", "agile", "board", "ticket"]},
    {"name": "confluence-mcp-server", "category": "data", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["confluence", "wiki", "documentation", "page", "space", "knowledge"]},
    {"name": "aws-mcp-server", "category": "infrastructure", "estimated_tokens": 7000, "tools_count": 12,
     "keywords": ["aws", "amazon", "s3", "lambda", "ec2", "cloud", "infrastructure"]},
    {"name": "vercel-mcp-server", "category": "infrastructure", "estimated_tokens": 3500, "tools_count": 6,
     "keywords": ["vercel", "deploy", "serverless", "hosting", "domain", "nextjs"]},
]

# Typisches Context-Window Budget
TYPICAL_CONTEXT_WINDOW = 128000  # Tokens
TYPICAL_SYSTEM_PROMPT = 2000  # Basis-System-Prompt
TYPICAL_CONVERSATION = 20000  # Durchschnittliche Konversation


def _score_server(server, task_words):
    """Berechnet Relevanz-Score eines Servers fuer die gegebene Aufgabe."""
    score = 0
    task_lower = set(w.lower() for w in task_words if len(w) > 2)

    for keyword in server["keywords"]:
        kw_lower = keyword.lower()
        # Exakter Match mit Task-Wort
        if kw_lower in task_lower:
            score += 10
        # Teilstring-Match
        for tw in task_lower:
            if kw_lower in tw or tw in kw_lower:
                score += 5
    return score


def _recommend_servers(task, max_servers=5):
    """Empfiehlt optimale Server-Kombination fuer eine Aufgabe."""
    task_words = task.replace("+", " ").replace(",", " ").split()

    # Alle Server scoren
    scored = []
    for server in SERVER_CATALOG:
        score = _score_server(server, task_words)
        if score > 0:
            scored.append((score, server))

    # Nach Score sortieren, Top-N nehmen
    scored.sort(key=lambda x: x[0], reverse=True)
    recommended = scored[:max_servers]

    return recommended


def _analyze_current_servers(server_names, task):
    """Analysiert aktuelle Server-Auswahl und empfiehlt Optimierung."""
    task_words = task.replace("+", " ").replace(",", " ").split()

    # Aktuelle Server im Katalog finden
    current = []
    unknown = []
    for name in server_names:
        name_clean = name.strip().lower()
        found = None
        for s in SERVER_CATALOG:
            # Flexibler Match: Name oder Teil des Namens
            s_name = s["name"].lower()
            if name_clean == s_name or name_clean in s_name or s_name.startswith(name_clean):
                found = s
                break
        if found:
            current.append(found)
        else:
            unknown.append(name.strip())

    # Alle aktuellen Server scoren
    keep = []
    remove = []
    for server in current:
        score = _score_server(server, task_words)
        if score > 0:
            keep.append({"name": server["name"], "score": score, "tokens": server["estimated_tokens"], "action": "keep"})
        else:
            remove.append({"name": server["name"], "score": score, "tokens": server["estimated_tokens"], "action": "remove"})

    # Fehlende Server empfehlen (die nicht in current sind)
    current_names = set(s["name"] for s in current)
    missing_scored = []
    for server in SERVER_CATALOG:
        if server["name"] not in current_names:
            score = _score_server(server, task_words)
            if score > 0:
                missing_scored.append((score, server))
    missing_scored.sort(key=lambda x: x[0], reverse=True)
    add = [{"name": s["name"], "score": sc, "tokens": s["estimated_tokens"], "action": "add"} for sc, s in missing_scored[:3]]

    return keep, remove, add, unknown


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
    GET /api/optimize?task=analyze+weather+data+for+farming
    GET /api/optimize?servers=weather,crypto,memory,security&task=check+berlin+weather
    """

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        task = query.get("task", [""])[0].strip()
        servers_str = query.get("servers", [""])[0].strip()

        if not task:
            _json_response(self, 400, {
                "error": "Parameter 'task' ist erforderlich",
                "usage": "/api/optimize?task=analyze+weather+data+for+farming",
                "usage_with_servers": "/api/optimize?servers=weather,crypto,memory&task=check+berlin+weather",
                "catalog_size": len(SERVER_CATALOG),
            })
            return

        if servers_str:
            # Modus 2: Aktuelle Server analysieren und optimieren
            server_names = [s.strip() for s in servers_str.split(",") if s.strip()]
            keep, remove, add, unknown = _analyze_current_servers(server_names, task)

            current_tokens = sum(s["tokens"] for s in keep) + sum(s["tokens"] for s in remove)
            optimized_tokens = sum(s["tokens"] for s in keep) + sum(s["tokens"] for s in add)
            saved_tokens = sum(s["tokens"] for s in remove)
            savings_pct = round((saved_tokens / current_tokens * 100), 1) if current_tokens > 0 else 0

            # Context-Auslastung berechnen
            available_context = TYPICAL_CONTEXT_WINDOW - TYPICAL_SYSTEM_PROMPT - TYPICAL_CONVERSATION
            current_usage_pct = round(current_tokens / available_context * 100, 1)
            optimized_usage_pct = round(optimized_tokens / available_context * 100, 1)

            response_data = {
                "mode": "optimize_existing",
                "task": task,
                "current_servers": len(server_names),
                "keep": sorted(keep, key=lambda x: x["score"], reverse=True),
                "remove": remove,
                "add": add,
                "current_tokens": current_tokens,
                "optimized_tokens": optimized_tokens,
                "saved_tokens": saved_tokens,
                "savings_pct": savings_pct,
                "context_budget": {
                    "total": TYPICAL_CONTEXT_WINDOW,
                    "available_for_tools": available_context,
                    "current_usage_pct": current_usage_pct,
                    "optimized_usage_pct": optimized_usage_pct,
                },
                "reasoning": f"Von {len(server_names)} Servern: {len(keep)} behalten, {len(remove)} entfernen, {len(add)} hinzufuegen. Einsparung: ~{saved_tokens} Tokens ({savings_pct}%).",
            }

            if unknown:
                response_data["unknown_servers"] = unknown
                response_data["note"] = f"{len(unknown)} Server nicht im Katalog gefunden — werden bei der Berechnung ignoriert."

            _json_response(self, 200, response_data)
        else:
            # Modus 1: Optimale Server-Kombination empfehlen
            recommended = _recommend_servers(task, max_servers=5)

            if not recommended:
                _json_response(self, 200, {
                    "mode": "recommend",
                    "task": task,
                    "recommended_servers": [],
                    "estimated_tokens": 0,
                    "reasoning": "Keine passenden Server fuer diese Aufgabe gefunden. Versuche spezifischere Suchbegriffe.",
                    "catalog_size": len(SERVER_CATALOG),
                })
                return

            servers_list = []
            total_tokens = 0
            for score, server in recommended:
                servers_list.append({
                    "name": server["name"],
                    "category": server["category"],
                    "relevance_score": score,
                    "estimated_tokens": server["estimated_tokens"],
                    "tools_count": server["tools_count"],
                    "matched_keywords": [kw for kw in server["keywords"]
                                         if any(kw.lower() in w.lower() or w.lower() in kw.lower()
                                                for w in task.replace("+", " ").split() if len(w) > 2)],
                })
                total_tokens += server["estimated_tokens"]

            # Context-Auslastung
            available_context = TYPICAL_CONTEXT_WINDOW - TYPICAL_SYSTEM_PROMPT - TYPICAL_CONVERSATION
            usage_pct = round(total_tokens / available_context * 100, 1)

            _json_response(self, 200, {
                "mode": "recommend",
                "task": task,
                "recommended_servers": servers_list,
                "total_servers": len(servers_list),
                "estimated_tokens": total_tokens,
                "context_budget": {
                    "total": TYPICAL_CONTEXT_WINDOW,
                    "available_for_tools": available_context,
                    "usage_pct": usage_pct,
                },
                "reasoning": f"{len(servers_list)} Server empfohlen fuer '{task}'. Geschaetzter Token-Verbrauch: ~{total_tokens} ({usage_pct}% des verfuegbaren Context).",
                "catalog_size": len(SERVER_CATALOG),
            })
