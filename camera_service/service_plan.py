"""P2: Optik-Prüfplan für CAM-03 mit simuliertem Status und Python-Prüfung."""

import json
import argparse

from camera_service.camera_tools import evaluate_temperature, get_camera_status
from camera_service.document_chat import answer_from_context, build_document_context, select_context_chunks
from camera_service.plan_validation import print_validated_plan
from camera_service.semantic_search import retrieve_sections


# Dieses Lernbeispiel behandelt ausdrücklich nur CAM-03 und ein unscharfes Bild.
QUESTION = (
    "Erstelle einen kurzen Prüfplan für ein unscharfes Bild von CAM-03 im fiktiven "
    "Wartungsszenario. Erkläre zuerst die mitgelieferte Python-Temperaturprüfung "
    "mit ihren Quellen und Grenzen. Nenne danach noch fehlende Angaben zur Bildstörung. "
    "Gib anschließend 3 bis 5 nummerierte, noch durchzuführende Optik-Prüfschritte "
    "mit Tätigkeit, Zweck und Quelle an. Es liegen keine Sichtbefunde vor. "
    "Erfinde keine Ursachen, Reparaturen oder Grenzwerte."
)
REQUIRED_SECTIONS = {
    ("cam-03.txt", "Abschnitt 2: Temperaturbereiche"),
    ("wartung-optik.txt", "Abschnitt 3: Abgrenzung zur Temperaturprüfung"),
}
JSON_QUESTION = (
    "Erstelle einen Optik-Prüfplan für ein unscharfes Bild von CAM-03 im fiktiven "
    "Wartungsszenario. Kamera-ID und Bildstörung sind bekannt, es liegen keine Sichtbefunde vor. "
    "Antworte ausschließlich mit einem JSON-Objekt mit genau dem Feld steps. "
    "steps enthält 3 bis 5 Objekte, jedes mit genau den Textfeldern activity, purpose, "
    "source, section und status. status ist immer pending. source ist ein mitgesendeter "
    "Dateiname; section ist die vollständige mitgesendete Abschnittsüberschrift einschließlich "
    "Abschnittsnummer und Titel. Alle Tätigkeiten sind noch durchzuführen. "
    "Nutze nur dokumentierte Optik-Prüfschritte. Keine Markdown-Codeblöcke, keine Einleitung, "
    "keine weiteren Felder. Erfinde keine Ursachen, Reparaturen oder Grenzwerte."
)


def prepare_plan_context(chunks, ranked, structured=False):
    """Dieselben Fundstellen und Pflichtquellen für Terminal und HTTP auswählen."""
    matches = [chunk for score, chunk in ranked[:3]]
    required_sections = REQUIRED_SECTIONS.copy()
    if structured:
        required_sections.add(("wartung-optik.txt", "Abschnitt 2: Sichtprüfung bei unscharfem Bild"))
    found = {(chunk["source"], chunk["section"]) for chunk in chunks}
    if not required_sections <= found:
        raise ValueError("Eine benötigte Grenzwert-, Optik- oder Abgrenzungsquelle fehlt. Kein Gemma-Aufruf.")
    matches += [chunk for chunk in chunks if (chunk["source"], chunk["section"]) in required_sections]
    return build_document_context(chunks, matches), select_context_chunks(chunks, matches)


def main(structured=False):
    print("Szenario: CAM-03, unscharfes Bild; keine Sichtprüfung durchgeführt.")
    try:
        status = get_camera_status("CAM-03")
        temperature_check = evaluate_temperature(status)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Status oder Temperaturprüfung fehlgeschlagen: {error}")
        print("Es wurde keine API-Anfrage gesendet.")
        return 1
    evidence = {"status": status, "temperature_check": temperature_check}
    print("\nVon Python abgerufene Simulation und ausgeführte Temperaturprüfung:")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))

    result = retrieve_sections("CAM-03 unscharfes Bild Sichtscheibe Sichtprüfung")
    if result is None:
        return 1
    chunks, ranked = result
    try:
        context, selected = prepare_plan_context(chunks, ranked, structured)
    except ValueError as error:
        print(error)
        return 1
    print("\nAn Gemma gesendete Dokumentfundstellen und ergänzte Pflichtquellen:")
    print(context)
    if structured:
        allowed_sources = {(chunk["source"], chunk["section"]) for chunk in selected}

        def handle_answer(answer):
            print_validated_plan(answer, allowed_sources)

        return answer_from_context(JSON_QUESTION, context, evidence=evidence, answer_handler=handle_answer)
    return answer_from_context(QUESTION, context, evidence=evidence)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optik-Prüfplan für das fiktive CAM-03-Szenario.")
    parser.add_argument("--json", action="store_true", help="Gemmas JSON-Plan vor der Planausgabe prüfen.")
    arguments = parser.parse_args()
    raise SystemExit(main(structured=arguments.json))
