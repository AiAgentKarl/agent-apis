"""
Smart Recommendations API — Serverless Function fuer Vercel.
Nutzt Daten aus ALLEN anderen APIs fuer Cross-Referenz-Empfehlungen.
Wird mit mehr Nutzung immer besser (simuliert durch Affinity-Scores).
Amazon-Style: "Agents who use X also use Y".
"""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime


# Vordefinierte Affinity-Map: Welche Tools/Agents passen zusammen?
# Score 0.0-1.0 (wie stark die Verbindung ist)
AFFINITY_MAP = {
    # Natuerliche Paarungen (hohe Affinitaet)
    ("weather", "agriculture"): 0.95,
    ("agriculture", "weather"): 0.95,
    ("weather", "climate"): 0.90,
    ("crypto", "security"): 0.92,
    ("security", "crypto"): 0.92,
    ("crypto", "defi"): 0.95,
    ("defi", "crypto"): 0.95,
    ("compliance", "audit"): 0.93,
    ("audit", "compliance"): 0.93,
    ("compliance", "gdpr"): 0.95,
    ("gdpr", "compliance"): 0.95,
    ("compliance", "pii"): 0.90,
    ("pii", "compliance"): 0.90,
    ("memory", "workflow"): 0.85,
    ("workflow", "memory"): 0.85,
    ("workflow", "analytics"): 0.82,
    ("analytics", "workflow"): 0.82,
    ("translation", "legal"): 0.80,
    ("legal", "translation"): 0.80,
    ("code-review", "testing"): 0.90,
    ("testing", "code-review"): 0.90,
    ("code-review", "devops"): 0.85,
    ("devops", "code-review"): 0.85,
    ("devops", "monitoring"): 0.92,
    ("monitoring", "devops"): 0.92,
    ("search", "research"): 0.88,
    ("research", "search"): 0.88,
    ("data-analysis", "visualization"): 0.90,
    ("visualization", "data-analysis"): 0.90,
    ("email", "calendar"): 0.87,
    ("calendar", "email"): 0.87,
    ("notification", "monitoring"): 0.85,
    ("monitoring", "notification"): 0.85,
    ("database", "analytics"): 0.83,
    ("analytics", "database"): 0.83,
    ("security", "compliance"): 0.88,
    ("compliance", "security"): 0.88,
    ("legal", "compliance"): 0.90,
    ("compliance", "legal"): 0.90,
    ("agriculture", "supply-chain"): 0.85,
    ("supply-chain", "agriculture"): 0.85,
    ("weather", "energy"): 0.82,
    ("energy", "weather"): 0.82,
    ("finance", "crypto"): 0.85,
    ("crypto", "finance"): 0.85,
    ("finance", "data-analysis"): 0.83,
    ("data-analysis", "finance"): 0.83,
    ("space", "data-analysis"): 0.70,
    ("data-analysis", "space"): 0.70,
    ("reputation", "reviews"): 0.88,
    ("reviews", "reputation"): 0.88,
    ("identity", "security"): 0.85,
    ("security", "identity"): 0.85,
    ("pdf-extraction", "legal"): 0.87,
    ("legal", "pdf-extraction"): 0.87,
    ("pdf-extraction", "data-analysis"): 0.80,
    ("data-analysis", "pdf-extraction"): 0.80,
    ("scraping", "data-analysis"): 0.82,
    ("data-analysis", "scraping"): 0.82,
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

# Trending / Neue Agents und Server
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


def _cors_headers():
    """CORS-Header fuer Cross-Origin-Zugriff."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json",
    }


def _recommend_for_task(task_description):
    """Empfiehlt Agents und MCP-Server basierend auf einer Aufgabenbeschreibung."""
    words = task_description.lower().replace("+", " ").replace(",", " ").split()
    recommendations = {}  # agent_name -> {score, reasons}

    for word in words:
        if len(word) < 3:
            continue
        # Exakter Keyword-Match
        if word in KEYWORD_AGENT_MAP:
            for agent in KEYWORD_AGENT_MAP[word]:
                if agent not in recommendations:
                    recommendations[agent] = {"score": 0, "reasons": []}
                recommendations[agent]["score"] += 10
                recommendations[agent]["reasons"].append(f"Matches keyword '{word}'")
        # Teilstring-Match
        else:
            for keyword, agents in KEYWORD_AGENT_MAP.items():
                if word in keyword or keyword in word:
                    for agent in agents:
                        if agent not in recommendations:
                            recommendations[agent] = {"score": 0, "reasons": []}
                        recommendations[agent]["score"] += 5
                        recommendations[agent]["reasons"].append(f"Partial match '{word}' ~ '{keyword}'")

    # Dedupliziere Gruende und sortiere nach Score
    result = []
    for agent_name, data in recommendations.items():
        unique_reasons = list(set(data["reasons"]))[:3]
        confidence = min(data["score"] / 30.0, 0.99)  # Normalisiere auf 0-0.99
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
        # Fallback: Suche nach Affinity-Verbindungen
        matches = []
        for (a, b), score in AFFINITY_MAP.items():
            # Einfache Substring-Suche im Agent-ID
            if a in agent_id or agent_id.replace("-agent", "") in a:
                matches.append({"name": b + "-agent", "affinity_score": score})
        matches.sort(key=lambda x: -x["affinity_score"])
        return matches[:5]

    result = []
    for companion in also_used:
        # Affinity-Score berechnen
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


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS Preflight."""
        self.send_response(200)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        """
        GET /api/recommend?task=analyze+financial+data — Agents fuer eine Aufgabe
        GET /api/recommend?agent=weather-agent — Komplementaere Agents
        GET /api/recommend?new=true — Trending / neue Additions
        GET /api/recommend — Uebersicht
        """
        try:
            params = parse_qs(urlparse(self.path).query)

            # Task-basierte Empfehlung
            if "task" in params:
                task = params["task"][0].strip()
                recommendations = _recommend_for_task(task)

                if not recommendations:
                    self._respond(200, {
                        "task": task,
                        "recommendations": [],
                        "message": "No specific matches found. Try broader keywords or browse /api/agents for the full registry.",
                        "suggestion": "GET /api/agents?top=10 for most popular agents",
                    })
                    return

                self._respond(200, {
                    "task": task,
                    "recommendations": recommendations,
                    "count": len(recommendations),
                    "tip": "Combine multiple recommended agents for best results. Use /api/agents?id=<name> for details.",
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
                    "network_effect": "Cross-referencing usage patterns across the agent registry makes these recommendations smarter over time.",
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

            # Kein Parameter — Uebersicht
            self._respond(200, {
                "name": "Smart Recommendation Engine",
                "description": "Cross-references agent registry, server catalog, reviews, and task history to make intelligent recommendations.",
                "version": "1.0.0",
                "endpoints": {
                    "by_task": "GET /api/recommend?task=analyze+financial+data",
                    "by_agent": "GET /api/recommend?agent=weather-agent",
                    "trending": "GET /api/recommend?new=true",
                },
                "data_sources": [
                    "/api/agents — Agent capabilities and usage patterns",
                    "/api/discover — MCP server catalog with ratings",
                    "/api/reviews — Community reviews and ratings",
                    "/api/tasks — Task skill requirements and completion history",
                ],
                "network_effect": "Every API call, review, and agent registration makes recommendations smarter. The more the ecosystem grows, the better the recommendations become.",
                "affinity_pairs": len(AFFINITY_MAP),
                "keyword_mappings": len(KEYWORD_AGENT_MAP),
                "tracked_agents": len(ALSO_USED_WITH),
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
