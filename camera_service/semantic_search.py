"""Dokumentabschnitte anhand ihrer Embedding-Ähnlichkeit zur Frage sortieren."""

import math

from camera_service.documents import DOCS_DIR, load_documents, split_documents
from camera_service.lm_studio import EMBEDDING_MODEL_ID
from camera_service.lm_studio import request_json


def read_embeddings(response, count):
    """Vektoren anhand der API-Indizes ihren Eingabetexten zuordnen."""
    if not isinstance(response, dict) or not isinstance(response.get("data"), list):
        raise ValueError("Die Embedding-Antwort enthält keine Datenliste.")
    vectors = {}
    for item in response["data"]:
        if not isinstance(item, dict):
            raise ValueError("Ungültiger Eintrag in der Embedding-Antwort.")
        index = item.get("index")
        vector = item.get("embedding")
        if type(index) is not int or not 0 <= index < count or index in vectors:
            raise ValueError("Fehlender, doppelter oder ungültiger Embedding-Index.")
        if not isinstance(vector, list) or not vector or not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) for value in vector
        ):
            raise ValueError("Ein Embedding enthält keine gültige Zahlenliste.")
        vectors[index] = vector
    if len(vectors) != count:
        raise ValueError("Der Server hat nicht für jeden Eingabetext ein Embedding geliefert.")
    return [vectors[index] for index in range(count)]


def cosine_similarity(left, right):
    """Skalarprodukt geteilt durch das Produkt der beiden Vektorlängen."""
    if len(left) != len(right) or not left:
        raise ValueError("Vektoren müssen gleich viele Dimensionen haben und nicht leer sein.")
    left_length = math.sqrt(sum(value * value for value in left))
    right_length = math.sqrt(sum(value * value for value in right))
    if left_length == 0 or right_length == 0:
        raise ValueError("Ein Nullvektor kann nicht mit Kosinusähnlichkeit verglichen werden.")
    dot_product = sum(a * b for a, b in zip(left, right))
    return dot_product / (left_length * right_length)


def retrieve_sections(question):
    """Alle Chunks und ihre sortierte Ähnlichkeit liefern; bei Fehlern None."""
    question = question.strip()
    if not question:
        print("Bitte gib eine Frage ein. Es wurde keine API-Anfrage gesendet.")
        return None
    try:
        chunks = split_documents(load_documents(DOCS_DIR))
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Dokumente konnten nicht geladen werden: {error}")
        return None

    models = request_json("GET", "/models")
    if models is None:
        return None
    if not isinstance(models, dict) or not isinstance(models.get("data"), list):
        print("Unerwartetes Antwortformat der Modellliste.")
        return None
    if EMBEDDING_MODEL_ID not in [
        model.get("id") for model in models["data"] if isinstance(model, dict)
    ]:
        print(f"Das Embedding-Modell {EMBEDDING_MODEL_ID} ist nicht verfügbar.")
        return None

    # Eingabe 0 ist die Frage, danach folgen die Dokumentabschnitte.
    texts = [f"search_query: {question}"] + [
        f"search_document: {chunk['document_header']}\n{chunk['text']}"
        for chunk in chunks
    ]
    print(f"Erzeuge Embeddings für eine Frage und {len(chunks)} Abschnitte ...")
    response = request_json(
        "POST", "/embeddings",
        {"model": EMBEDDING_MODEL_ID, "input": texts}, read_timeout=180,
    )
    if response is None:
        return None
    try:
        vectors = read_embeddings(response, len(texts))
        ranked = [
            (cosine_similarity(vectors[0], vector), chunk)
            for chunk, vector in zip(chunks, vectors[1:])
        ]
        ranked.sort(key=lambda item: item[0], reverse=True)
    except ValueError as error:
        print(f"Ähnlichkeitsvergleich fehlgeschlagen: {error}")
        return None

    return chunks, ranked


def main():
    question = input("Frage für die Ähnlichkeitssuche: ").strip()
    result = retrieve_sections(question)
    if result is None:
        return 1
    chunks, ranked = result

    print("\nDie drei ähnlichsten Abschnitte:")
    for position, (score, chunk) in enumerate(ranked[:3], start=1):
        print(f"\n{position}. Ähnlichkeit: {score:.4f}")
        print(f"Quelle: {chunk['source']} | {chunk['section']}")
        print(chunk["text"])
    print("\nDie Werte sind keine Wahrscheinlichkeiten. Auch unpassende Fragen erhalten eine Rangfolge.")
    print("Gemma wurde nicht aufgerufen. Prüfe, ob die Fundstellen die Frage beantworten können.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
