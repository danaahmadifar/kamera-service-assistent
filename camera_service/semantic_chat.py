"""Embedding-Suche mit einer quellenbezogenen Gemma-Antwort verbinden."""

from camera_service.document_chat import answer_from_context, build_document_context
from camera_service.semantic_search import retrieve_sections


def main():
    question = input("Deine Frage an die Dokumente: ").strip()
    result = retrieve_sections(question)
    if result is None:
        return 1
    chunks, ranked = result
    selected = ranked[:3]
    print("\nAusgewählte Abschnitte nach Ähnlichkeit:")
    for score, chunk in selected:
        print(f"{score:.4f} | {chunk['source']} | {chunk['section']}")
    print("Die Rangfolge beweist keine Relevanz und keinen Gerätebefund.")

    matches = [chunk for score, chunk in selected]
    context = build_document_context(chunks, matches)
    print("\nAn Gemma gesendeter Dokumentkontext (Fundstellen und Geltungsbereich):")
    print(context)
    return answer_from_context(question, context)


if __name__ == "__main__":
    raise SystemExit(main())
