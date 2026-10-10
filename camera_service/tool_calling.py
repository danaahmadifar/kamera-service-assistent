"""Statuswerkzeug auf Modellvorschlag ausführen und das Ergebnis zurückgeben."""

import json

from camera_service.camera_tools import evaluate_temperature, get_camera_status
from camera_service.lm_studio import MODEL_ID, REFERENCE_PATH, request_json


STATUS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_camera_status",
        "description": "Liest simulierte Statusdaten der fiktiven Kamera CAM-03.",
        "parameters": {
            "type": "object",
            "properties": {
                "camera_id": {
                    "type": "string",
                    "enum": ["CAM-03"],
                    "description": "ID der Kamera, deren Beispielstatus benötigt wird.",
                }
            },
            "required": ["camera_id"],
            "additionalProperties": False,
        },
    },
}


def execute_status_tool(tool_calls):
    """Genau einen erlaubten Statusabruf nach Prüfung der Argumente ausführen."""
    if not isinstance(tool_calls, list) or len(tool_calls) != 1:
        raise ValueError("Dieser Client erlaubt genau einen Werkzeugaufruf.")
    tool_call = tool_calls[0]
    if not isinstance(tool_call, dict) or tool_call.get("type") != "function":
        raise ValueError("Der Vorschlag muss ein Funktionsaufruf sein.")
    if not isinstance(tool_call.get("id"), str) or not tool_call["id"].strip():
        raise ValueError("Der Werkzeugaufruf benötigt eine nichtleere id für die Ergebnisrückgabe.")
    function = tool_call.get("function")
    if not isinstance(function, dict) or function.get("name") != "get_camera_status":
        raise ValueError("Erlaubt ist ausschließlich get_camera_status.")

    arguments_text = function.get("arguments")
    if not isinstance(arguments_text, str):
        raise ValueError("Die Argumente müssen als JSON-Zeichenkette vorliegen.")
    try:
        arguments = json.loads(arguments_text)
    except json.JSONDecodeError as error:
        raise ValueError("Die Werkzeugargumente sind kein gültiges JSON.") from error
    if not isinstance(arguments, dict) or set(arguments) != {"camera_id"}:
        raise ValueError("Erwartet wird ausschließlich das Argument camera_id.")
    if arguments["camera_id"] != "CAM-03":
        raise ValueError("Der Werkzeugaufruf unterstützt ausschließlich CAM-03.")

    return get_camera_status(arguments["camera_id"])


def build_followup_messages(messages, assistant_message, result):
    """Den bereits geprüften Aufruf und sein Ergebnis an die Nachrichten anhängen."""
    tool_calls = assistant_message["tool_calls"]
    return messages + [
        {
            "role": "assistant",
            "content": assistant_message.get("content"),
            "tool_calls": tool_calls,
        },
        {
            "role": "tool",
            "tool_call_id": tool_calls[0]["id"],
            "content": json.dumps(result, ensure_ascii=False),
        },
    ]


def main():
    question = input("Deine Frage: ").strip()
    if not question:
        print("Bitte gib eine Frage ein. Es wurde keine Anfrage gesendet.")
        return 1

    try:
        reference_text = REFERENCE_PATH.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        print("Das Referenzdokument reference_docs/cam03/cam-03.txt kann nicht als UTF-8 gelesen werden.")
        return 1
    if not reference_text:
        print("Das Referenzdokument reference_docs/cam03/cam-03.txt ist leer.")
        return 1
    print(f"Referenzdokument geladen: {REFERENCE_PATH.name}")

    models = request_json("GET", "/models")
    if models is None:
        return 1
    if not isinstance(models, dict) or not isinstance(models.get("data"), list):
        print("Unerwartetes Antwortformat der Modellliste.")
        return 1
    model_ids = [model.get("id") for model in models["data"] if isinstance(model, dict)]
    if MODEL_ID not in model_ids:
        print(f"Das Modell {MODEL_ID} ist nicht verfügbar.")
        return 1

    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Du bist ein technischer Service-Assistent. "
                    "Antworte kurz und verständlich auf Deutsch. "
                    "Beantworte allgemeine technische Begriffsfragen ohne Statusabruf. "
                    "Bei gerätespezifischen Angaben verwende das Referenzdokument; "
                    "wenn es keine passende Information enthält, benenne das und erfinde keine Angaben. "
                    "Für angefragte Statusdaten verwende das angebotene Werkzeug. "
                    "Das Programm ergänzt den Statusabruf um eine Temperaturprüfung durch Python. "
                    "Das Ergebnis enthält status (Messdaten) und temperature_check (Prüfung). "
                    "Erkläre nach Erhalt des Ergebnisses die Prüfung kurz auf Deutsch. "
                    "Übernimm within_range für den geprüften Messwert: true heißt innerhalb, false außerhalb. "
                    "Nenne Python als Prüfinstanz und cam-03.txt, Abschnitt 2 als Grenzwertquelle. "
                    "Nenne die Simulation, den Messzeitpunkt und get_camera_status als Quelle. "
                    "Die Beispieldaten belegen keinen aktuellen Live-Zustand. "
                    "Eine Bereichsüberschreitung belegt allein keinen Defekt. "
                    "Frage nicht nach Angaben, die im Ergebnis bereits vorhanden sind. "
                    "Erfinde keine Messwerte oder Grenzwerte.\n\n"
                    f"Referenzdokument: {REFERENCE_PATH.name}\n{reference_text}"
                ),
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        "tools": [STATUS_TOOL],
        "stream": False,
        "max_tokens": 2048,
    }
    completion = request_json("POST", "/chat/completions", payload, read_timeout=180)
    if completion is None:
        return 1

    try:
        choice = completion["choices"][0]
        message = choice["message"]
        tool_calls = message.get("tool_calls")
    except (KeyError, IndexError, TypeError, AttributeError):
        print("Unerwartetes Antwortformat der Chat-Anfrage.")
        return 1

    print(f"Abbruchgrund: {choice.get('finish_reason')}")
    if tool_calls is None or tool_calls == []:
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            print("\nGemmas Antwort ohne Werkzeugaufruf:")
            print(content.strip())
            if choice.get("finish_reason") == "length":
                print("\nHinweis: Die Antwort wurde durch das Tokenlimit begrenzt.")
            return 0
        print("Weder Antworttext noch Werkzeugaufruf erhalten.")
        print("Prüfe die Server-Logs; bei length wurde das Tokenlimit erreicht.")
        return 1

    print("Vom Modell vorgeschlagene Werkzeugaufrufe:")
    print(json.dumps(tool_calls, ensure_ascii=False, indent=2))
    try:
        status = execute_status_tool(tool_calls)
        temperature_check = evaluate_temperature(status)
        result = {"status": status, "temperature_check": temperature_check}
    except ValueError as error:
        print(f"Werkzeugaufruf oder Temperaturprüfung fehlgeschlagen: {error}")
        return 1
    except (OSError, UnicodeError):
        print("Die Statusdatei data/cam-03-status.json kann nicht als UTF-8 gelesen werden.")
        return 1

    print("\nVon Python ausgeführtes Werkzeug: get_camera_status")
    print("Werkzeugergebnis (simulierte Statusdaten und Python-Temperaturprüfung):")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    followup_payload = {
        "model": MODEL_ID,
        "messages": build_followup_messages(payload["messages"], message, result),
        "stream": False,
        "max_tokens": 2048,
    }
    print("\nSende das Werkzeugergebnis an Gemma zurück und warte auf die Textantwort...")
    final_completion = request_json(
        "POST", "/chat/completions", followup_payload, read_timeout=180
    )
    if final_completion is None:
        return 1
    try:
        final_choice = final_completion["choices"][0]
        final_message = final_choice["message"]
        answer = final_message.get("content")
        finish_reason = final_choice.get("finish_reason")
    except (KeyError, IndexError, TypeError, AttributeError):
        print("Unerwartetes Antwortformat der abschließenden Chat-Anfrage.")
        return 1
    if final_message.get("tool_calls"):
        print("Das Modell hat erneut einen Werkzeugaufruf vorgeschlagen.")
        print("Dieser Lernschritt führt nur einen Aufruf aus. Es wurde kein weiteres Werkzeug ausgeführt.")
        return 1
    if not isinstance(answer, str) or not answer.strip():
        print(f"Kein abschließender Antworttext. Abbruchgrund: {finish_reason}")
        if finish_reason == "length":
            print("Das Tokenlimit wurde erreicht. Prüfe die Server-Logs in LM Studio.")
        return 1

    print("\nGemmas Antwort nach dem Werkzeugaufruf:")
    print(answer.strip())
    if finish_reason == "length":
        print("\nHinweis: Die Antwort wurde durch das Tokenlimit begrenzt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
