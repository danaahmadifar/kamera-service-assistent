"""Drei lokale Servicefälle simulieren; keine Netzwerkprüfung ausführen."""

import argparse
import json
from pathlib import Path

from camera_service.axis_device import load_simulated_device_info


SCENARIOS_PATH = Path(__file__).resolve().parents[1] / "data" / "axis" / "scenarios.json"
SCENARIO_IDS = ("unreachable", "access_denied", "no_video")


def load_scenario(scenario_id):
    """Einen gekennzeichneten Testfall aus der Datei auswählen."""
    if scenario_id not in SCENARIO_IDS:
        raise ValueError(f"Unbekanntes Szenario: {scenario_id}")
    fixture = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    if not isinstance(fixture, dict) or fixture.get("simulated") is not True:
        raise ValueError("Die Szenariodatei benötigt simulated: true.")
    scenarios = fixture.get("scenarios")
    scenario = scenarios.get(scenario_id) if isinstance(scenarios, dict) else None
    if not isinstance(scenario, dict):
        raise ValueError("Das gewählte Szenario fehlt in der Datei.")
    device_info = scenario.get("device_info")
    if not isinstance(device_info, dict) or device_info.get("outcome") not in (
        "timeout", "access_denied", "success"
    ):
        raise ValueError("Ungültiges Ergebnis des Geräteinformationsabrufs.")
    video = scenario.get("video")
    if not isinstance(video, dict) or video.get("observation") not in (
        "not_checked", "reported_missing"
    ):
        raise ValueError("Ungültige Videobeobachtung.")
    if "transport" not in video or video["transport"] is not None:
        raise ValueError("In diesen Testfällen muss der Übertragungsmodus unbekannt sein.")
    return {**scenario, "simulated": True, "scenario_id": scenario_id}


def simulate_service_case(scenario_id):
    """Nur beim erfolgreichen Abruf simulierte Geräteinformationen ergänzen."""
    case = load_scenario(scenario_id)
    if case["device_info"]["outcome"] == "success":
        case["device_info"]["response"] = load_simulated_device_info()["response"]
    return case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=SCENARIO_IDS)
    args = parser.parse_args()
    try:
        case = simulate_service_case(args.scenario)
    except (OSError, ValueError) as error:
        print(f"Servicefall konnte nicht simuliert werden: {error}")
        return 1

    print("Servicefall aus lokalen Beispieldateien (Simulation):")
    print(json.dumps(case, ensure_ascii=False, indent=2))
    print("reported_missing ist eine simulierte Benutzerangabe, keine Stream-Prüfung.")
    print("Ein Timeout belegt keine Ursache; der Übertragungsmodus ist unbekannt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
