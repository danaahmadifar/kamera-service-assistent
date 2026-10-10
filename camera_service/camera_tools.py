"""Simulierter Kamera-Statusabruf mit festen, erfundenen Beispieldaten."""

import json
import math
from pathlib import Path


# Manuell aus reference_docs/cam03/cam-03.txt, Abschnitt 2, übernommen.
BOARD_MIN_C = 0.0
BOARD_MAX_C = 80.0
STATUS_PATH = Path(__file__).resolve().parents[1] / "data" / "cam-03-status.json"


def get_camera_status(camera_id):
    """Simulierte Beispielmessung aus einer Datei lesen; keine Kamera kontaktieren."""
    if camera_id != "CAM-03":
        raise ValueError(f"Unbekannte Kamera-ID: {camera_id}")

    status_text = STATUS_PATH.read_text(encoding="utf-8")
    camera_status = json.loads(status_text)
    if not isinstance(camera_status, dict):
        raise ValueError("Die Statusdatei muss ein JSON-Objekt enthalten.")
    if camera_status.get("camera_id") != camera_id:
        raise ValueError("Die Kamera-ID in der Statusdatei passt nicht zur Anfrage.")
    if camera_status.get("simulated") is not True:
        raise ValueError("Die Beispieldaten müssen mit simulated: true gekennzeichnet sein.")
    for field in ("sensor", "measured_at"):
        if not isinstance(camera_status.get(field), str) or not camera_status[field].strip():
            raise ValueError(f"Die Statusdatei benötigt eine nichtleere Angabe für {field}.")
    return camera_status


def evaluate_temperature(camera_status):
    """Die Beispielmessung anhand der Regel für CAM-03/board_temperature prüfen."""
    if camera_status.get("camera_id") != "CAM-03":
        raise ValueError("Die Temperaturregel gilt nur für CAM-03.")
    if camera_status.get("sensor") != "board_temperature":
        raise ValueError("Die Temperaturregel gilt nur für den Sensor board_temperature.")

    temperature = camera_status.get("temperature_c")
    if type(temperature) not in (int, float) or not math.isfinite(temperature):
        raise ValueError("Die Temperatur muss eine endliche Zahl sein.")

    return {
        "camera_id": camera_status["camera_id"],
        "sensor": camera_status["sensor"],
        "temperature_c": temperature,
        "minimum_c": BOARD_MIN_C,
        "maximum_c": BOARD_MAX_C,
        "within_range": BOARD_MIN_C <= temperature <= BOARD_MAX_C,
        "reference": "cam-03.txt, Abschnitt 2",
    }
