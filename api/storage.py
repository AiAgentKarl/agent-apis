"""
Persistenter Storage via /tmp/ Verzeichnis fuer Vercel Serverless Functions.

Dateien in /tmp/ ueberleben fuer die Lebensdauer der Function-Instanz
(Minuten bis Stunden bei warmen Invocations). Kombiniert mit den
vorbereiteten Default-Daten als Fallback ergibt das eine einfache
aber effektive Persistenz-Loesung.

Alle Netzwerkeffekt-APIs nutzen dieses Modul.
"""

import json
import os


def load_data(name, default=None):
    """
    Daten aus /tmp/ laden. Falls nicht vorhanden, default zurueckgeben.

    Args:
        name: Eindeutiger Name fuer die Datendatei (z.B. 'social_reviews')
        default: Fallback-Daten wenn keine persistenten Daten existieren
    Returns:
        Die geladenen Daten oder den Default-Wert
    """
    filepath = f"/tmp/agent_data_{name}.json"
    try:
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        # Bei Lesefehlern einfach Default zurueckgeben
        pass
    return default


def save_data(name, data):
    """
    Daten nach /tmp/ speichern. Persistent ueber warme Invocations.

    Args:
        name: Eindeutiger Name fuer die Datendatei (z.B. 'social_reviews')
        data: Zu speichernde Daten (muss JSON-serialisierbar sein)
    Returns:
        True bei Erfolg, False bei Fehler
    """
    filepath = f"/tmp/agent_data_{name}.json"
    try:
        with open(filepath, "w") as f:
            json.dump(data, f)
        return True
    except (IOError, OSError, TypeError):
        # Bei Schreibfehlern leise fehlschlagen — In-Memory funktioniert weiterhin
        return False


def has_data(name):
    """
    Pruefen ob persistente Daten existieren.

    Args:
        name: Eindeutiger Name fuer die Datendatei
    Returns:
        True wenn Datei existiert
    """
    filepath = f"/tmp/agent_data_{name}.json"
    return os.path.exists(filepath)
