"""
PII-Scanner API — Serverless Function für Vercel.
Erkennt personenbezogene Daten in Text und schwärzt sie.
Unterstützt: E-Mail, Telefon, Kreditkarten, SSN, IBAN, IP-Adressen.
Kein API-Key nötig, rein Regex-basiert.
"""

from http.server import BaseHTTPRequestHandler
import json
import re
from urllib.parse import urlparse, parse_qs


# PII-Muster mit Regex
PII_PATTERNS = {
    "email": {
        "pattern": re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ),
        "label": "[EMAIL]",
        "description": "E-Mail-Adresse",
    },
    "phone": {
        "pattern": re.compile(
            r'(?<!\d)'                          # Kein Digit davor
            r'(?:'
            r'\+?\d{1,3}[\s.-]?'                # Ländervorwahl (optional)
            r')?'
            r'(?:'
            r'\(?\d{2,4}\)?[\s.-]?'             # Vorwahl
            r')'
            r'\d{3,4}[\s.-]?'                   # Mittelteil
            r'\d{3,4}'                           # Endteil
            r'(?!\d)',                           # Kein Digit danach
            re.VERBOSE
        ),
        "label": "[PHONE]",
        "description": "Telefonnummer",
    },
    "credit_card": {
        "pattern": re.compile(
            r'\b(?:'
            r'4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}'     # Visa
            r'|5[1-5]\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}' # Mastercard
            r'|3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}'             # Amex
            r'|6(?:011|5\d{2})[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}' # Discover
            r')\b'
        ),
        "label": "[CREDIT_CARD]",
        "description": "Kreditkartennummer",
    },
    "ssn": {
        "pattern": re.compile(
            r'\b\d{3}-\d{2}-\d{4}\b'
        ),
        "label": "[SSN]",
        "description": "US Social Security Number",
    },
    "iban": {
        "pattern": re.compile(
            r'\b[A-Z]{2}\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{0,2}\b'
        ),
        "label": "[IBAN]",
        "description": "Internationale Bankkontonummer",
    },
    "ipv4": {
        "pattern": re.compile(
            r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
            r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
        ),
        "label": "[IP_ADDRESS]",
        "description": "IPv4-Adresse",
    },
}


def _scan_text(text):
    """Text auf PII scannen. Gibt gefundene Typen, geschwärzten Text und Details zurück."""
    found_types = set()
    findings = []
    redacted = text

    for pii_type, config in PII_PATTERNS.items():
        matches = config["pattern"].finditer(text)
        for match in matches:
            found_types.add(pii_type)
            findings.append({
                "type": pii_type,
                "value_preview": _mask_value(match.group(), pii_type),
                "position": {"start": match.start(), "end": match.end()},
            })

    # Schwärzen — längste Matches zuerst (verhindert Teilersetzungen)
    for pii_type, config in PII_PATTERNS.items():
        redacted = config["pattern"].sub(config["label"], redacted)

    return {
        "pii_found": len(findings) > 0,
        "pii_count": len(findings),
        "types_found": sorted(found_types),
        "findings": findings,
        "redacted_text": redacted,
        "original_length": len(text),
    }


def _mask_value(value, pii_type):
    """Wert teilweise maskieren für die Vorschau."""
    if pii_type == "email":
        parts = value.split("@")
        if len(parts) == 2:
            local = parts[0]
            masked_local = local[0] + "***" if len(local) > 1 else "***"
            return f"{masked_local}@{parts[1]}"
    elif pii_type == "credit_card":
        digits = re.sub(r'[\s-]', '', value)
        return f"****-****-****-{digits[-4:]}" if len(digits) >= 4 else "****"
    elif pii_type == "ssn":
        return f"***-**-{value[-4:]}"
    elif pii_type == "phone":
        clean = re.sub(r'[\s.-]', '', value)
        return f"***{clean[-4:]}" if len(clean) >= 4 else "****"
    elif pii_type == "iban":
        return f"{value[:4]}****{value[-4:]}" if len(value) >= 8 else "****"
    elif pii_type == "ipv4":
        parts = value.split(".")
        return f"{parts[0]}.***.***.{parts[-1]}" if len(parts) == 4 else "***"
    return "***"


def _json_response(handler, status_code, data):
    """Hilfsfunktion: JSON-Antwort senden."""
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, indent=2).encode())


class handler(BaseHTTPRequestHandler):
    """
    GET  /api/pii?text=Contact+me+at+john@example.com
    POST /api/pii  (Body: {"text": "..."})
    """

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        text = query.get("text", [""])[0]

        if not text:
            _json_response(self, 400, {
                "error": "Parameter 'text' erforderlich",
                "usage": "/api/pii?text=Contact+me+at+john@example.com"
            })
            return

        result = _scan_text(text)
        _json_response(self, 200, result)

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                _json_response(self, 400, {"error": "Leerer Request-Body"})
                return

            # Maximal 100KB Text
            if content_length > 102400:
                _json_response(self, 413, {
                    "error": "Text zu lang (max. 100KB)"
                })
                return

            body = json.loads(self.rfile.read(content_length))
            text = body.get("text", "")

            if not text:
                _json_response(self, 400, {
                    "error": "Feld 'text' im JSON-Body erforderlich",
                    "usage": "POST /api/pii mit Body: {\"text\": \"...\"}"
                })
                return

            result = _scan_text(text)
            _json_response(self, 200, result)

        except json.JSONDecodeError:
            _json_response(self, 400, {"error": "Ungültiges JSON"})
        except Exception as e:
            _json_response(self, 500, {"error": f"Interner Fehler: {str(e)}"})
