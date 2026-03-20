"""
AI Cost Router — Serverless Function fuer Vercel.
Empfiehlt das guenstigste/beste AI-Modell basierend auf Task, Budget und Prioritaet.
Aktuelle Preise Stand Maerz 2026.
"""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs


# Modelldatenbank mit aktuellen Preisen (Maerz 2026, pro 1M Tokens)
MODEL_DATABASE = [
    {
        "name": "GPT-4o",
        "provider": "OpenAI",
        "input_cost": 2.50,
        "output_cost": 10.00,
        "tier": "complex",
        "strengths": ["Guter Allrounder", "Multimodal", "Schnell"],
        "speed": "fast",
    },
    {
        "name": "GPT-4o-mini",
        "provider": "OpenAI",
        "input_cost": 0.15,
        "output_cost": 0.60,
        "tier": "medium",
        "strengths": ["Sehr guenstig", "Schnell", "Gut fuer einfache Aufgaben"],
        "speed": "very_fast",
    },
    {
        "name": "GPT-4.1",
        "provider": "OpenAI",
        "input_cost": 2.00,
        "output_cost": 8.00,
        "tier": "complex",
        "strengths": ["Neuestes OpenAI Flagship", "Starkes Coding", "Instruction-Following"],
        "speed": "fast",
    },
    {
        "name": "GPT-4.1-mini",
        "provider": "OpenAI",
        "input_cost": 0.40,
        "output_cost": 1.60,
        "tier": "medium",
        "strengths": ["Gutes Preis-Leistungs-Verhaeltnis", "Solide Qualitaet"],
        "speed": "fast",
    },
    {
        "name": "GPT-4.1-nano",
        "provider": "OpenAI",
        "input_cost": 0.10,
        "output_cost": 0.40,
        "tier": "simple",
        "strengths": ["Guenstigstes OpenAI-Modell", "Ultra-schnell", "Perfekt fuer Batch"],
        "speed": "very_fast",
    },
    {
        "name": "Claude 3.5 Sonnet",
        "provider": "Anthropic",
        "input_cost": 3.00,
        "output_cost": 15.00,
        "tier": "complex",
        "strengths": ["Bestes Coding-Modell", "Starke Analyse", "Zuverlaessig"],
        "speed": "fast",
    },
    {
        "name": "Claude 3.5 Haiku",
        "provider": "Anthropic",
        "input_cost": 0.80,
        "output_cost": 4.00,
        "tier": "medium",
        "strengths": ["Schnell und guenstig", "Gute Qualitaet", "Niedrige Latenz"],
        "speed": "very_fast",
    },
    {
        "name": "Claude Opus 4",
        "provider": "Anthropic",
        "input_cost": 15.00,
        "output_cost": 75.00,
        "tier": "expert",
        "strengths": ["Faehigstes Modell", "Komplexes Reasoning", "Forschung"],
        "speed": "slow",
    },
    {
        "name": "Gemini 2.0 Flash",
        "provider": "Google",
        "input_cost": 0.10,
        "output_cost": 0.40,
        "tier": "simple",
        "strengths": ["Guenstigstes Major-Modell", "Extrem schnell", "Multimodal"],
        "speed": "very_fast",
    },
    {
        "name": "Gemini 2.5 Pro",
        "provider": "Google",
        "input_cost": 1.25,
        "output_cost": 10.00,
        "tier": "complex",
        "strengths": ["Langer Kontext", "Gutes Reasoning", "Multimodal"],
        "speed": "fast",
    },
    {
        "name": "Llama 3.3 70B",
        "provider": "Together AI",
        "input_cost": 0.88,
        "output_cost": 0.88,
        "tier": "medium",
        "strengths": ["Open Source", "Selbst-hostbar", "Keine Vendor-Abhaengigkeit"],
        "speed": "fast",
    },
    {
        "name": "DeepSeek R1",
        "provider": "DeepSeek",
        "input_cost": 0.55,
        "output_cost": 2.19,
        "tier": "complex",
        "strengths": ["Bestes Reasoning pro Dollar", "Chain-of-Thought", "Mathematik"],
        "speed": "moderate",
    },
    {
        "name": "Mistral Large",
        "provider": "Mistral AI",
        "input_cost": 2.00,
        "output_cost": 6.00,
        "tier": "complex",
        "strengths": ["EU-basiert", "GDPR-konform", "Mehrsprachig"],
        "speed": "fast",
    },
    {
        "name": "Qwen 2.5 72B",
        "provider": "Alibaba Cloud",
        "input_cost": 0.90,
        "output_cost": 0.90,
        "tier": "medium",
        "strengths": ["Stark multilingual", "Chinesisch/Englisch", "Open Source"],
        "speed": "fast",
    },
]

# Keywords fuer Task-Komplexitaetsklassifikation
COMPLEXITY_KEYWORDS = {
    "simple": [
        "translate", "format", "classify", "label", "convert", "extract email",
        "simple", "basic", "short", "tag", "detect language", "spell check",
        "capitalize", "lowercase", "uppercase", "count words", "validate",
    ],
    "medium": [
        "summarize", "write", "draft", "email", "blog", "describe", "explain",
        "list", "paraphrase", "rewrite", "outline", "generate text", "caption",
        "product description", "social media", "newsletter",
    ],
    "complex": [
        "code", "program", "analyze", "legal", "financial", "debug", "architect",
        "review", "compare", "refactor", "optimize", "design", "security audit",
        "data analysis", "sql", "api", "algorithm", "test", "migrate",
    ],
    "expert": [
        "research", "novel", "breakthrough", "critical", "strategic", "multi-step",
        "prove", "theorem", "dissertation", "peer review", "patent", "clinical",
        "scientific", "philosophical", "complex reasoning", "agent", "autonomous",
    ],
}

# Tier-Reihenfolge fuer Vergleiche
TIER_ORDER = {"simple": 0, "medium": 1, "complex": 2, "expert": 3}

# Budget-Mapping auf maximale Kosten (Input + Output gemittelt pro 1K Tokens)
BUDGET_LIMITS = {
    "low": 2.0,       # Max ~$2/1M Tokens gemittelt
    "medium": 10.0,    # Max ~$10/1M Tokens gemittelt
    "high": 100.0,     # Kein echtes Limit
}

# Premium-Referenzmodell fuer Savings-Berechnung
PREMIUM_REFERENCE = {
    "name": "Claude Opus 4",
    "avg_cost": (15.00 + 75.00) / 2,
}


def _classify_complexity(task):
    """Klassifiziert die Task-Komplexitaet anhand von Keyword-Matching."""
    task_lower = task.lower().replace("+", " ").replace("-", " ")
    scores = {"simple": 0, "medium": 0, "complex": 0, "expert": 0}

    for level, keywords in COMPLEXITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in task_lower:
                scores[level] += 1

    # Hoechster Score gewinnt, bei Gleichstand die hoehere Komplexitaet
    if max(scores.values()) == 0:
        return "medium"  # Default bei keinem Match

    # Sortiere nach Score (absteigend), dann nach Tier (absteigend)
    ranked = sorted(
        scores.items(),
        key=lambda x: (x[1], TIER_ORDER[x[0]]),
        reverse=True,
    )
    return ranked[0][0]


def _avg_cost(model):
    """Berechnet durchschnittliche Kosten pro 1M Tokens (Input + Output)."""
    return (model["input_cost"] + model["output_cost"]) / 2


def _cost_per_1k(model):
    """Berechnet Kosten pro 1K Tokens."""
    return {
        "input": round(model["input_cost"] / 1000, 6),
        "output": round(model["output_cost"] / 1000, 6),
    }


def _find_optimal_model(complexity, budget, priority):
    """Findet das optimale Modell basierend auf Komplexitaet, Budget und Prioritaet."""
    budget_limit = BUDGET_LIMITS.get(budget, BUDGET_LIMITS["medium"])

    # Kandidaten filtern: Modell-Tier muss zur Komplexitaet passen
    # Bei niedrigem Budget auch niedrigere Tiers akzeptieren
    complexity_idx = TIER_ORDER[complexity]

    candidates = []
    for model in MODEL_DATABASE:
        model_tier_idx = TIER_ORDER[model["tier"]]
        avg = _avg_cost(model)

        # Budget-Filter
        if avg > budget_limit:
            continue

        # Tier-Kompatibilitaet: Modell sollte mindestens so faehig sein
        # wie die Task-Komplexitaet verlangt (oder ein Tier darunter bei low budget)
        if budget == "low":
            # Bei Low-Budget darf man ein Tier runtergehen
            if model_tier_idx < max(0, complexity_idx - 1):
                continue
        else:
            if model_tier_idx < complexity_idx:
                continue

        candidates.append(model)

    if not candidates:
        # Fallback: Guenstigstes Modell das ins Budget passt
        budget_models = [m for m in MODEL_DATABASE if _avg_cost(m) <= budget_limit]
        if budget_models:
            candidates = budget_models
        else:
            # Absoluter Fallback: Guenstigstes Modell ueberhaupt
            candidates = sorted(MODEL_DATABASE, key=_avg_cost)[:3]

    # Sortierung nach Prioritaet
    if priority == "cost":
        candidates.sort(key=lambda m: _avg_cost(m))
    elif priority == "quality":
        candidates.sort(key=lambda m: (-TIER_ORDER[m["tier"]], _avg_cost(m)))
    elif priority == "speed":
        speed_order = {"very_fast": 0, "fast": 1, "moderate": 2, "slow": 3}
        candidates.sort(key=lambda m: (speed_order.get(m["speed"], 2), _avg_cost(m)))

    return candidates


def _calculate_savings(model):
    """Berechnet Einsparung gegenueber Premium-Modell."""
    model_avg = _avg_cost(model)
    premium_avg = PREMIUM_REFERENCE["avg_cost"]
    if premium_avg == 0:
        return "0%"
    savings = ((premium_avg - model_avg) / premium_avg) * 100
    return f"{savings:.1f}%"


def _build_reasoning(model, complexity, budget, priority):
    """Generiert eine Begruendung fuer die Empfehlung."""
    parts = []
    parts.append(f"Task-Komplexitaet: {complexity}")
    parts.append(f"Budget: {budget}")
    parts.append(f"Prioritaet: {priority}")

    if priority == "cost":
        parts.append(
            f"{model['name']} bietet das beste Preis-Leistungs-Verhaeltnis "
            f"fuer {complexity}-Tasks bei ${_avg_cost(model):.2f}/1M Tokens Durchschnitt"
        )
    elif priority == "quality":
        parts.append(
            f"{model['name']} liefert die hoechste Qualitaet "
            f"fuer {complexity}-Tasks innerhalb des {budget}-Budgets"
        )
    elif priority == "speed":
        parts.append(
            f"{model['name']} bietet die niedrigste Latenz "
            f"fuer {complexity}-Tasks ({model['speed']})"
        )

    return ". ".join(parts)


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
    AI Cost Router — Empfiehlt das optimale AI-Modell fuer eine Aufgabe.

    GET /api/route?task=translate+a+sentence&budget=low
    GET /api/route?task=complex+legal+analysis&budget=high
    GET /api/route?task=summarize+an+article
    GET /api/route?task=write+code&priority=quality
    """

    def do_GET(self):
        query_params = parse_qs(urlparse(self.path).query)

        # Parameter parsen
        task = query_params.get("task", [""])[0].strip()
        budget = query_params.get("budget", ["medium"])[0].strip().lower()
        priority = query_params.get("priority", ["cost"])[0].strip().lower()

        # Validierung: task ist Pflicht
        if not task:
            _json_response(self, 400, {
                "error": "Parameter 'task' ist erforderlich",
                "usage": "/api/route?task=translate+a+sentence&budget=low&priority=cost",
                "parameters": {
                    "task": "Beschreibung der Aufgabe (Pflicht)",
                    "budget": "low | medium | high (Standard: medium)",
                    "priority": "cost | quality | speed (Standard: cost)",
                },
                "examples": [
                    "/api/route?task=translate+a+sentence&budget=low",
                    "/api/route?task=complex+legal+analysis&budget=high",
                    "/api/route?task=summarize+an+article",
                    "/api/route?task=write+python+code&priority=quality",
                    "/api/route?task=classify+sentiment&priority=speed",
                ],
            })
            return

        # Budget validieren
        if budget not in BUDGET_LIMITS:
            _json_response(self, 400, {
                "error": f"Ungueltiges Budget: '{budget}'. Erlaubt: low, medium, high",
            })
            return

        # Prioritaet validieren
        if priority not in ("cost", "quality", "speed"):
            _json_response(self, 400, {
                "error": f"Ungueltige Prioritaet: '{priority}'. Erlaubt: cost, quality, speed",
            })
            return

        # Komplexitaet analysieren
        complexity = _classify_complexity(task)

        # Optimale Modelle finden
        candidates = _find_optimal_model(complexity, budget, priority)

        if not candidates:
            _json_response(self, 404, {
                "error": "Kein passendes Modell gefunden",
                "task": task,
                "budget": budget,
                "priority": priority,
            })
            return

        # Bestes Modell
        best = candidates[0]
        # Alternativen (2-3, ohne das Beste)
        alternatives = candidates[1:4]

        response_data = {
            "task": task.replace("+", " "),
            "task_complexity": complexity,
            "budget": budget,
            "priority": priority,
            "recommendation": {
                "model": best["name"],
                "provider": best["provider"],
                "estimated_cost_per_1k_tokens": _cost_per_1k(best),
                "cost_per_1m_tokens": {
                    "input": best["input_cost"],
                    "output": best["output_cost"],
                },
                "strengths": best["strengths"],
                "speed": best["speed"],
                "reasoning": _build_reasoning(best, complexity, budget, priority),
                "estimated_savings_vs_premium": _calculate_savings(best),
            },
            "alternatives": [
                {
                    "model": m["name"],
                    "provider": m["provider"],
                    "estimated_cost_per_1k_tokens": _cost_per_1k(m),
                    "cost_per_1m_tokens": {
                        "input": m["input_cost"],
                        "output": m["output_cost"],
                    },
                    "strengths": m["strengths"],
                    "speed": m["speed"],
                    "estimated_savings_vs_premium": _calculate_savings(m),
                }
                for m in alternatives
            ],
            "models_evaluated": len(MODEL_DATABASE),
            "pricing_date": "2026-03",
        }

        _json_response(self, 200, response_data)
