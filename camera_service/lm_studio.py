"""Gemeinsamer HTTP-Client für die lokale LM-Studio-API."""

import os
from pathlib import Path

import requests

BASE_URL = os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234/v1").rstrip("/")
MODEL_ID = "google/gemma-4-12b-qat"
EMBEDDING_MODEL_ID = "text-embedding-nomic-embed-text-v1.5"
REFERENCE_PATH = Path(__file__).resolve().parents[1] / "reference_docs" / "cam03" / "cam-03.txt"


def request_json(method, path, payload=None, read_timeout=30):
    """Eine HTTP-Anfrage senden und ihre JSON-Antwort lesen."""
    url = f"{BASE_URL}{path}"
    print(f"Sende {method} {url}")
    try:
        response = requests.request(
            method, url, json=payload, timeout=(5, read_timeout)
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("Zeitüberschreitung: Der Server antwortet nicht rechtzeitig.")
        print("Prüfe Serverstatus und Modell-Ladevorgang in LM Studio.")
        print("Eine bereits gestartete Generierung kann trotz Timeout im Server weiterlaufen.")
    except requests.exceptions.ConnectionError:
        print("Keine Verbindung zu LM Studio möglich.")
        print("Prüfe Serverstatus, Adresse und Port. Starte dieses Skript auf deinem Windows-PC.")
    except requests.exceptions.HTTPError as error:
        status = error.response.status_code
        print(f"Der Server hat mit HTTP-Fehler {status} geantwortet.")
        if status in (401, 403):
            print("Prüfe die Authentifizierung bzw. Token-Berechtigungen in LM Studio.")
            print("Teile keinen Token im Chat; die lokale Konfiguration ergänzen wir bei Bedarf.")
        elif status == 404:
            print("Prüfe die Basisadresse und ob das gewünschte Modell verfügbar ist.")
        else:
            print("Prüfe die Server-Logs in LM Studio.")
    except requests.exceptions.JSONDecodeError:
        print("Der Server hat keine gültige JSON-Antwort geliefert. Prüfe Adresse und Server-Logs.")
    except requests.exceptions.RequestException:
        print("Die HTTP-Anfrage ist fehlgeschlagen. Prüfe Adresse und Servereinstellungen.")
    return None
