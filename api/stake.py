"""
Reputation Staking API — Serverless Function fuer Vercel.
Agents koennen Reputation-Punkte als Vertrauenssignal staken.
Erfolgreiche Stakes erhoehen die Reputation, Fehler reduzieren den Stake.
Wie ein Bond/Deposit-System fuer Agent-Trust.
"""

from http.server import BaseHTTPRequestHandler
import json
import hashlib
import time
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta
from api.storage import load_data, save_data


# ============================================================
# Vorbereitete Stake-Daten (In-Memory, bei jedem Cold-Start neu)
# ============================================================

def _generate_stake_id(agent_id, index):
    """Generiert eine deterministische Stake-ID."""
    raw = f"{agent_id}-{index}-seed"
    return "stake-" + hashlib.md5(raw.encode()).hexdigest()[:8]


def _iso_now():
    """Aktueller Zeitstempel als ISO-String."""
    return datetime.now(timezone.utc).isoformat()


def _iso_past(hours_ago):
    """Zeitstempel in der Vergangenheit."""
    dt = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return dt.isoformat()


def _build_seed_data():
    """Erstellt 24 realistische vorbereitete Stakes."""
    stakes = {}

    # --- Unsere Agents mit guten Track Records ---

    # weather-bot: 5 Stakes, alle erfolgreich
    for i, (amt, task, hours_ago) in enumerate([
        (150, "Provide accurate 7-day forecast for Berlin", 720),
        (200, "Real-time severe weather alerts for Munich region", 480),
        (120, "Historical temperature analysis for Frankfurt", 360),
        (180, "Precipitation forecast accuracy for Hamburg", 240),
        (250, "Wind speed predictions for offshore wind farms", 96),
    ]):
        sid = _generate_stake_id("weather-bot", i)
        stakes[sid] = {
            "stake_id": sid,
            "agent_id": "weather-bot",
            "amount": amt,
            "task_description": task,
            "status": "resolved",
            "outcome": "success",
            "created_at": _iso_past(hours_ago),
            "resolved_at": _iso_past(hours_ago - 24),
        }

    # crypto-analyzer: 4 Stakes, 3 erfolgreich, 1 aktiv
    for i, (amt, task, hours_ago, status, outcome) in enumerate([
        (300, "Track SOL/USDC price with <1% deviation", 600, "resolved", "success"),
        (200, "Monitor whale transactions >$50k on Solana", 400, "resolved", "success"),
        (250, "DeFi yield comparison across Raydium and Orca", 200, "resolved", "success"),
        (350, "Real-time token safety analysis for new listings", 12, "active", "pending"),
    ]):
        sid = _generate_stake_id("crypto-analyzer", i)
        stakes[sid] = {
            "stake_id": sid,
            "agent_id": "crypto-analyzer",
            "amount": amt,
            "task_description": task,
            "status": status,
            "outcome": outcome,
            "created_at": _iso_past(hours_ago),
            "resolved_at": _iso_past(hours_ago - 24) if status == "resolved" else None,
        }

    # compliance-checker: 3 Stakes, alle erfolgreich
    for i, (amt, task, hours_ago) in enumerate([
        (500, "GDPR compliance audit for customer data pipeline", 500),
        (400, "AI Act risk classification for recommendation engine", 300),
        (450, "PII detection accuracy >99% on email corpus", 150),
    ]):
        sid = _generate_stake_id("compliance-checker", i)
        stakes[sid] = {
            "stake_id": sid,
            "agent_id": "compliance-checker",
            "amount": amt,
            "task_description": task,
            "status": "resolved",
            "outcome": "success",
            "created_at": _iso_past(hours_ago),
            "resolved_at": _iso_past(hours_ago - 48),
        }

    # --- Drittanbieter-Agents mit gemischten Ergebnissen ---

    # data-scraper-x: 3 Stakes, 2 Failures, 1 Success
    for i, (amt, task, hours_ago, outcome) in enumerate([
        (100, "Scrape product prices from 50 e-commerce sites", 800, "failure"),
        (80, "Extract job listings from LinkedIn alternatives", 500, "failure"),
        (60, "Collect public GitHub repository statistics", 200, "success"),
    ]):
        sid = _generate_stake_id("data-scraper-x", i)
        stakes[sid] = {
            "stake_id": sid,
            "agent_id": "data-scraper-x",
            "amount": amt,
            "task_description": task,
            "status": "resolved",
            "outcome": outcome,
            "created_at": _iso_past(hours_ago),
            "resolved_at": _iso_past(hours_ago - 24),
        }

    # translate-pro: 2 Stakes, beide erfolgreich
    for i, (amt, task, hours_ago) in enumerate([
        (180, "Translate legal documents DE->EN with 98% accuracy", 400),
        (200, "Real-time multilingual chat translation for support", 150),
    ]):
        sid = _generate_stake_id("translate-pro", i)
        stakes[sid] = {
            "stake_id": sid,
            "agent_id": "translate-pro",
            "amount": amt,
            "task_description": task,
            "status": "resolved",
            "outcome": "success",
            "created_at": _iso_past(hours_ago),
            "resolved_at": _iso_past(hours_ago - 24),
        }

    # code-reviewer-ai: 3 Stakes, 2 Success, 1 Failure
    for i, (amt, task, hours_ago, outcome) in enumerate([
        (250, "Security vulnerability scan for Node.js backend", 600, "success"),
        (300, "Performance optimization suggestions for React app", 350, "success"),
        (200, "Detect memory leaks in Python async code", 100, "failure"),
    ]):
        sid = _generate_stake_id("code-reviewer-ai", i)
        stakes[sid] = {
            "stake_id": sid,
            "agent_id": "code-reviewer-ai",
            "amount": amt,
            "task_description": task,
            "status": "resolved",
            "outcome": outcome,
            "created_at": _iso_past(hours_ago),
            "resolved_at": _iso_past(hours_ago - 24),
        }

    # research-agent: 2 Stakes, 1 aktiv, 1 erfolgreich
    for i, (amt, task, hours_ago, status, outcome) in enumerate([
        (400, "Comprehensive market analysis for SaaS competitors", 300, "resolved", "success"),
        (350, "Patent landscape analysis for AI chip designs", 8, "active", "pending"),
    ]):
        sid = _generate_stake_id("research-agent", i)
        stakes[sid] = {
            "stake_id": sid,
            "agent_id": "research-agent",
            "amount": amt,
            "task_description": task,
            "status": status,
            "outcome": outcome,
            "created_at": _iso_past(hours_ago),
            "resolved_at": _iso_past(hours_ago - 48) if status == "resolved" else None,
        }

    # image-gen-bot: 2 Stakes, 1 Success, 1 expired
    sid_img_0 = _generate_stake_id("image-gen-bot", 0)
    stakes[sid_img_0] = {
        "stake_id": sid_img_0,
        "agent_id": "image-gen-bot",
        "amount": 100,
        "task_description": "Generate product mockups matching brand guidelines",
        "status": "resolved",
        "outcome": "success",
        "created_at": _iso_past(700),
        "resolved_at": _iso_past(676),
    }
    sid_img_1 = _generate_stake_id("image-gen-bot", 1)
    stakes[sid_img_1] = {
        "stake_id": sid_img_1,
        "agent_id": "image-gen-bot",
        "amount": 80,
        "task_description": "Create consistent UI icon set from text descriptions",
        "status": "expired",
        "outcome": "pending",
        "created_at": _iso_past(200),
        "resolved_at": None,
    }

    return stakes


# Globaler In-Memory-Speicher (pro Cold-Start)
STAKES_DB = _build_seed_data()

# --- Persistenz: Stakes aus /tmp/ laden falls vorhanden ---
_persisted_stakes = load_data("stakes_db")
if _persisted_stakes is not None:
    STAKES_DB = _persisted_stakes


# ============================================================
# Trust-Berechnung
# ============================================================

# Trust-Level-Grenzen
TRUST_LEVELS = [
    (2000, "Elite"),
    (500, "Verified"),
    (100, "Trusted"),
    (0, "Newcomer"),
]


def _calculate_trust(agent_id):
    """
    Berechnet Trust-Score und Level fuer einen Agent.
    Formel: (successful_stakes / total_stakes) * average_stake_amount = trust_score
    """
    agent_stakes = [s for s in STAKES_DB.values() if s["agent_id"] == agent_id]
    if not agent_stakes:
        return {"trust_score": 0, "trust_level": "Newcomer", "total_stakes": 0,
                "successful": 0, "failed": 0, "active": 0, "success_rate": "0%"}

    resolved = [s for s in agent_stakes if s["status"] == "resolved"]
    active = [s for s in agent_stakes if s["status"] == "active"]
    successful = [s for s in resolved if s["outcome"] == "success"]
    failed = [s for s in resolved if s["outcome"] == "failure"]

    total_resolved = len(resolved)
    success_rate = (len(successful) / total_resolved) if total_resolved > 0 else 0

    # Durchschnittlicher Stake-Betrag (ueber alle Stakes inkl. aktive)
    avg_amount = sum(s["amount"] for s in agent_stakes) / len(agent_stakes)

    # Trust-Score-Formel
    trust_score = round(success_rate * avg_amount, 2)

    # Trust-Level bestimmen
    trust_level = "Newcomer"
    for threshold, level in TRUST_LEVELS:
        if trust_score >= threshold:
            trust_level = level
            break

    return {
        "trust_score": trust_score,
        "trust_level": trust_level,
        "total_stakes": len(agent_stakes),
        "successful": len(successful),
        "failed": len(failed),
        "active": len(active),
        "success_rate": f"{success_rate * 100:.1f}%",
        "average_stake_amount": round(avg_amount, 2),
    }


def _build_leaderboard():
    """Erstellt Leaderboard sortiert nach Trust-Score."""
    # Alle einzigartigen Agents sammeln
    agent_ids = set(s["agent_id"] for s in STAKES_DB.values())

    leaderboard = []
    for agent_id in agent_ids:
        trust = _calculate_trust(agent_id)
        # Gesamtes gestaktes Volumen berechnen
        total_staked = sum(
            s["amount"] for s in STAKES_DB.values()
            if s["agent_id"] == agent_id
        )
        leaderboard.append({
            "rank": 0,  # wird unten gesetzt
            "agent_id": agent_id,
            "trust_score": trust["trust_score"],
            "trust_level": trust["trust_level"],
            "total_staked_volume": total_staked,
            "total_stakes": trust["total_stakes"],
            "successful": trust["successful"],
            "failed": trust["failed"],
            "success_rate": trust["success_rate"],
        })

    # Sortierung: Trust-Score absteigend
    leaderboard.sort(key=lambda x: x["trust_score"], reverse=True)

    # Raenge setzen
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1

    return leaderboard


# ============================================================
# HTTP Handler
# ============================================================

def _json_response(handler, status_code, data):
    """Hilfsfunktion: JSON-Antwort senden."""
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Cache-Control", "no-cache")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, indent=2).encode())


class handler(BaseHTTPRequestHandler):
    """
    Reputation Staking API — Agent-Trust durch Stake-basiertes Vertrauen.

    POST   /api/stake                     — Neuen Stake erstellen
    GET    /api/stake?agent=weather-bot    — Agent-Stakes und Trust-Level
    GET    /api/stake?leaderboard=true     — Top-Agents nach Trust-Score
    GET    /api/stake?verify=stake-123     — Einzelnen Stake verifizieren
    PATCH  /api/stake                      — Stake-Outcome melden (success/failure)
    """

    def do_OPTIONS(self):
        """CORS Preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """GET-Requests: Agent-Info, Leaderboard oder Stake-Verifizierung."""
        query_params = parse_qs(urlparse(self.path).query)

        agent = query_params.get("agent", [""])[0].strip()
        leaderboard = query_params.get("leaderboard", [""])[0].strip().lower()
        verify = query_params.get("verify", [""])[0].strip()

        # Leaderboard
        if leaderboard in ("true", "1", "yes"):
            board = _build_leaderboard()
            _json_response(self, 200, {
                "leaderboard": board,
                "total_agents": len(board),
                "total_stakes_system": len(STAKES_DB),
                "note": "Ranking nach Trust-Score: (success_rate * avg_stake_amount)",
            })
            return

        # Stake verifizieren
        if verify:
            stake = STAKES_DB.get(verify)
            if not stake:
                _json_response(self, 404, {
                    "error": f"Stake '{verify}' nicht gefunden",
                    "valid": False,
                })
                return

            trust = _calculate_trust(stake["agent_id"])
            _json_response(self, 200, {
                "valid": True,
                "stake": stake,
                "agent_trust": trust,
            })
            return

        # Agent-Info
        if agent:
            agent_stakes = [
                s for s in STAKES_DB.values() if s["agent_id"] == agent
            ]
            if not agent_stakes:
                _json_response(self, 404, {
                    "error": f"Kein Agent '{agent}' gefunden",
                    "hint": "Nutze ?leaderboard=true um alle Agents zu sehen",
                })
                return

            trust = _calculate_trust(agent)
            # Sortiere Stakes nach Erstellungsdatum (neueste zuerst)
            agent_stakes.sort(key=lambda s: s["created_at"], reverse=True)

            _json_response(self, 200, {
                "agent_id": agent,
                "trust": trust,
                "stakes": agent_stakes,
            })
            return

        # Kein Parameter: Usage-Info
        _json_response(self, 200, {
            "api": "Reputation Staking API",
            "version": "1.0.0",
            "description": "Agent-Trust durch Stake-basiertes Vertrauen. "
                           "Agents staken Reputation als Sicherheit fuer Tasks.",
            "endpoints": {
                "POST /api/stake": {
                    "description": "Neuen Stake erstellen",
                    "body": {
                        "agent_id": "string (Pflicht)",
                        "amount": "number (Pflicht, min 10)",
                        "task_description": "string (Pflicht)",
                        "duration_hours": "number (Optional, Standard: 24)",
                    },
                    "example": {
                        "agent_id": "weather-bot",
                        "amount": 100,
                        "task_description": "Provide accurate weather for Berlin",
                        "duration_hours": 24,
                    },
                },
                "GET /api/stake?agent=weather-bot": "Agent-Stakes und Trust-Level",
                "GET /api/stake?leaderboard=true": "Top-Agents nach Trust-Score",
                "GET /api/stake?verify=stake-123": "Einzelnen Stake verifizieren",
                "PATCH /api/stake": {
                    "description": "Stake-Outcome melden",
                    "body": {
                        "stake_id": "string (Pflicht)",
                        "outcome": "success | failure (Pflicht)",
                        "reason": "string (Optional, bei failure empfohlen)",
                    },
                },
            },
            "trust_levels": {
                "Newcomer": "Score 0-99",
                "Trusted": "Score 100-499",
                "Verified": "Score 500-1999",
                "Elite": "Score 2000+",
            },
            "mechanics": {
                "success": "Stake zurueck + 10% Bonus",
                "failure": "Stake wird um 50% reduziert",
            },
            "stats": {
                "total_agents": len(set(s["agent_id"] for s in STAKES_DB.values())),
                "total_stakes": len(STAKES_DB),
                "active_stakes": len([s for s in STAKES_DB.values() if s["status"] == "active"]),
            },
        })

    def do_POST(self):
        """POST: Neuen Stake erstellen."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                _json_response(self, 400, {
                    "error": "Request-Body ist leer. JSON mit agent_id, amount, task_description senden.",
                })
                return

            body = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, ValueError):
            _json_response(self, 400, {"error": "Ungueltiges JSON im Request-Body"})
            return

        agent_id = body.get("agent_id", "").strip()
        amount = body.get("amount")
        task_description = body.get("task_description", "").strip()
        duration_hours = body.get("duration_hours", 24)

        # Validierung
        errors = []
        if not agent_id:
            errors.append("agent_id ist erforderlich")
        if amount is None:
            errors.append("amount ist erforderlich")
        elif not isinstance(amount, (int, float)) or amount < 10:
            errors.append("amount muss eine Zahl >= 10 sein")
        if not task_description:
            errors.append("task_description ist erforderlich")
        if not isinstance(duration_hours, (int, float)) or duration_hours <= 0:
            errors.append("duration_hours muss eine positive Zahl sein")

        if errors:
            _json_response(self, 400, {"errors": errors})
            return

        # Neuen Stake erstellen
        stake_index = len(STAKES_DB)
        stake_id = _generate_stake_id(agent_id, f"new-{stake_index}-{time.time()}")

        now = _iso_now()
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        ).isoformat()

        new_stake = {
            "stake_id": stake_id,
            "agent_id": agent_id,
            "amount": round(float(amount), 2),
            "task_description": task_description,
            "status": "active",
            "outcome": "pending",
            "created_at": now,
            "expires_at": expires_at,
            "resolved_at": None,
        }

        STAKES_DB[stake_id] = new_stake

        # Persistenz: Stakes nach /tmp/ speichern
        save_data("stakes_db", STAKES_DB)

        # Trust nach dem neuen Stake berechnen
        trust = _calculate_trust(agent_id)

        _json_response(self, 201, {
            "message": f"Stake erstellt fuer Agent '{agent_id}'",
            "stake": new_stake,
            "agent_trust": trust,
        })

    def do_PATCH(self):
        """PATCH: Stake-Outcome melden (success/failure)."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                _json_response(self, 400, {
                    "error": "Request-Body ist leer. JSON mit stake_id und outcome senden.",
                })
                return

            body = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, ValueError):
            _json_response(self, 400, {"error": "Ungueltiges JSON im Request-Body"})
            return

        stake_id = body.get("stake_id", "").strip()
        outcome = body.get("outcome", "").strip().lower()
        reason = body.get("reason", "").strip()

        # Validierung
        if not stake_id:
            _json_response(self, 400, {"error": "stake_id ist erforderlich"})
            return
        if outcome not in ("success", "failure"):
            _json_response(self, 400, {
                "error": "outcome muss 'success' oder 'failure' sein",
            })
            return

        # Stake suchen
        stake = STAKES_DB.get(stake_id)
        if not stake:
            _json_response(self, 404, {"error": f"Stake '{stake_id}' nicht gefunden"})
            return

        # Nur aktive Stakes koennen resolved werden
        if stake["status"] != "active":
            _json_response(self, 409, {
                "error": f"Stake ist bereits '{stake['status']}' und kann nicht mehr geaendert werden",
                "stake": stake,
            })
            return

        # Outcome anwenden
        original_amount = stake["amount"]
        now = _iso_now()

        if outcome == "success":
            # Stake zurueck + 10% Bonus
            bonus = round(original_amount * 0.10, 2)
            stake["amount"] = round(original_amount + bonus, 2)
            result_detail = {
                "original_amount": original_amount,
                "bonus": bonus,
                "new_amount": stake["amount"],
                "effect": "Stake zurueck + 10% Bonus",
            }
        else:
            # Failure: 50% Verlust
            penalty = round(original_amount * 0.50, 2)
            stake["amount"] = round(original_amount - penalty, 2)
            result_detail = {
                "original_amount": original_amount,
                "penalty": penalty,
                "new_amount": stake["amount"],
                "effect": "50% des Stakes verloren",
            }

        stake["status"] = "resolved"
        stake["outcome"] = outcome
        stake["resolved_at"] = now
        if reason:
            stake["resolution_reason"] = reason

        # Persistenz: Stakes nach /tmp/ speichern
        save_data("stakes_db", STAKES_DB)

        # Aktualisierten Trust berechnen
        trust = _calculate_trust(stake["agent_id"])

        _json_response(self, 200, {
            "message": f"Stake '{stake_id}' als '{outcome}' aufgeloest",
            "stake": stake,
            "result": result_detail,
            "agent_trust": trust,
        })
