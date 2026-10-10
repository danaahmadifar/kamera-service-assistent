"""Planstruktur und Quellenzuordnung prüfen, ohne Modellaufruf."""

import json
from copy import deepcopy

from camera_service.documents import DOCS_DIR, load_documents, split_documents


EXAMPLE_JSON = """
{
  "steps": [
    {
      "activity": "Sichtscheibe auf Schmutz, Fettspuren und Kondenswasser prüfen.",
      "purpose": "Mögliche Hinweise dokumentieren.",
      "source": "wartung-optik.txt",
      "section": "Abschnitt 2: Sichtprüfung bei unscharfem Bild",
      "status": "pending"
    },
    {
      "activity": "Beispielbilder bei Tageslicht und Nachtbetrieb vergleichen.",
      "purpose": "Unterschiede unter verschiedenen Bedingungen erfassen.",
      "source": "wartung-optik.txt",
      "section": "Abschnitt 2: Sichtprüfung bei unscharfem Bild",
      "status": "pending"
    },
    {
      "activity": "Festhalten, wann die Unschärfe auftritt.",
      "purpose": "Ständiges Auftreten von bestimmten Bedingungen unterscheiden.",
      "source": "wartung-optik.txt",
      "section": "Abschnitt 2: Sichtprüfung bei unscharfem Bild",
      "status": "pending"
    }
  ]
}
"""


def validate_plan(plan, allowed_sources):
    """Struktur und erlaubte Quellenpaare prüfen; keine inhaltliche Belegprüfung."""
    if not isinstance(plan, dict) or set(plan) != {"steps"}:
        raise ValueError("Der Plan muss ein Objekt mit ausschließlich dem Feld steps sein.")
    steps = plan["steps"]
    if not isinstance(steps, list) or not 3 <= len(steps) <= 5:
        raise ValueError("steps muss eine Liste mit 3 bis 5 Schritten sein.")
    required = {"activity", "purpose", "source", "section", "status"}
    for number, step in enumerate(steps, start=1):
        if not isinstance(step, dict) or set(step) != required:
            raise ValueError(f"Schritt {number}: Erwartet werden genau {sorted(required)}.")
        if not all(isinstance(value, str) and value.strip() for value in step.values()):
            raise ValueError(f"Schritt {number}: Alle Felder müssen nichtleere Texte sein.")
        if step["status"] != "pending":
            raise ValueError(f"Schritt {number}: status muss pending (noch durchzuführen) sein.")
        if (step["source"], step["section"]) not in allowed_sources:
            raise ValueError(f"Schritt {number}: Quelle und Abschnitt sind nicht freigegeben.")
    return plan


def print_validated_plan(answer, allowed_sources):
    """Modelltext als JSON lesen und erst nach erfolgreicher Prüfung als Plan ausgeben."""
    try:
        plan = json.loads(answer)
    except json.JSONDecodeError as error:
        raise ValueError("Die Modellantwort ist kein gültiges JSON-Planobjekt.") from error
    validate_plan(plan, allowed_sources)
    print("\nPlanformat und Quellenpaare geprüft; Inhalt weiterhin zu prüfen:")
    for number, step in enumerate(plan["steps"], start=1):
        print(f"{number}. Noch durchzuführen: {step['activity']}")
        print(f"   Zweck: {step['purpose']}")
        print(f"   Quelle: {step['source']} | {step['section']}")


def main():
    print("Offline-Beispiel: Dieser Plan wurde vorgegeben, nicht von Gemma erzeugt.")
    try:
        chunks = split_documents(load_documents(DOCS_DIR))
        # In diesem Versuch geben wir nur den Optik-Prüfabschnitt frei.
        allowed_sources = {
            (chunk["source"], chunk["section"]) for chunk in chunks
            if chunk["source"] == "wartung-optik.txt"
            and chunk["section"] == "Abschnitt 2: Sichtprüfung bei unscharfem Bild"
        }
        plan = validate_plan(json.loads(EXAMPLE_JSON), allowed_sources)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Beispielplan abgewiesen: {error}")
        return 1
    print("\nFormat und Quellenzuordnung akzeptiert:")
    for number, step in enumerate(plan["steps"], start=1):
        print(f"{number}. Noch durchzuführen: {step['activity']}")
        print(f"   Zweck: {step['purpose']}")
        print(f"   Quelle: {step['source']} | {step['section']}")

    invalid_plan = deepcopy(plan)
    invalid_plan["steps"][0]["source"] = "erfundene-anleitung.txt"
    print("\nAbsichtlicher Fehlversuch mit einer nicht freigegebenen Quelle:")
    try:
        validate_plan(invalid_plan, allowed_sources)
    except ValueError as error:
        print(f"Wie erwartet abgewiesen: {error}")
    else:
        print("Fehler: Die ungültige Quelle wurde nicht abgewiesen.")
        return 1
    print("\nAkzeptiertes Format beweist nicht, dass die Quelle die Tätigkeit inhaltlich belegt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
