"""Eine erfundene VAPIX-Antwort aus einer lokalen Datei lesen."""

import json
from pathlib import Path


DEVICE_INFO_PATH = Path(__file__).resolve().parents[1] / "data" / "axis" / "device-info.json"


def load_simulated_device_info():
    """Simulationskennzeichnung und benötigte Gerätefelder prüfen."""
    text = DEVICE_INFO_PATH.read_text(encoding="utf-8")
    fixture = json.loads(text)
    if not isinstance(fixture, dict) or fixture.get("simulated") is not True:
        raise ValueError("Die Beispieldatei benötigt simulated: true.")

    response = fixture.get("response")
    if not isinstance(response, dict) or "error" in response:
        raise ValueError("Eine erfolgreiche Geräteantwort wurde erwartet.")
    data = response.get("data")
    properties = data.get("propertyList") if isinstance(data, dict) else None
    if not isinstance(properties, dict):
        raise ValueError("In der Antwort fehlt data.propertyList.")
    for field in ("Brand", "ProdNbr", "Version"):
        value = properties.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Die Geräteantwort benötigt einen Textwert für {field}.")

    return fixture


def main():
    try:
        fixture = load_simulated_device_info()
    except (OSError, ValueError) as error:
        print(f"Simulierte Geräteinformationen konnten nicht gelesen werden: {error}")
        return 1

    properties = fixture["response"]["data"]["propertyList"]
    print("Datenquelle: data/axis/device-info.json (Simulation)")
    print(f"Marke: {properties['Brand']}")
    print(f"Modellkennung: {properties['ProdNbr']}")
    print(f"Gerätesoftware: {properties['Version']} (erfundener Platzhalter)")
    print("Es wurde keine Kamera kontaktiert und kein Videostream geprüft.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
