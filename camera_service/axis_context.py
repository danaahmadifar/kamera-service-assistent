"""Simulierten Servicefall und ausgewählte Axis-Quellen offline zusammenstellen."""

import argparse
import json
from pathlib import Path

from camera_service.axis_scenarios import SCENARIO_IDS, simulate_service_case
from camera_service.documents import load_documents, split_documents


AXIS_DOCS_DIR = Path(__file__).resolve().parents[1] / "reference_docs" / "axis"
SOURCE_FILE = "zugriff-und-videobild.txt"


def prepare_axis_context(scenario_id):
    """Quellen anhand des Abruf-Ergebnisses auswählen, ohne eine Ursache festzulegen."""
    case = simulate_service_case(scenario_id)
    chunks = split_documents(load_documents(AXIS_DOCS_DIR))
    section = (
        "Abschnitt 3: Zusätzliche Videostreams"
        if case["device_info"]["outcome"] == "success"
        else "Abschnitt 1: Gerätezugriff"
    )
    selected = [
        chunk for chunk in chunks
        if chunk["source"] == SOURCE_FILE and chunk["section"] == section
    ]
    if len(selected) != 1:
        raise ValueError(f"Die benötigte Quelle fehlt oder ist mehrdeutig: {section}")
    context = "\n\n".join(
        f"Quelle: {chunk['source']} | {chunk['section']}\n"
        f"{chunk['document_header']}\n{chunk['text']}"
        for chunk in selected
    )
    return {
        "case": case,
        "context": context,
        "sources": [
            {"source": chunk["source"], "section": chunk["section"]}
            for chunk in selected
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=SCENARIO_IDS)
    args = parser.parse_args()
    try:
        prepared = prepare_axis_context(args.scenario)
    except (OSError, ValueError) as error:
        print(f"Dokumentkontext konnte nicht vorbereitet werden: {error}")
        return 1

    print("Simulierter Servicefall:")
    print(json.dumps(prepared["case"], ensure_ascii=False, indent=2))
    print("\nAusgewählter Dokumentkontext:")
    print(prepared["context"])
    print("\nAuswahlregel des Projekts: Gerätezugriff bei Abruffehlern; sonst zusätzliche Streams.")
    print("Der Multicast-Abschnitt bleibt bei unbekanntem Übertragungsmodus ausgeschlossen.")
    print("Auswahl bedeutet möglichen Prüfhinweis, keine nachgewiesene Ursache.")
    print("Es wurde keine Anfrage an Gemma oder eine Kamera gesendet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
