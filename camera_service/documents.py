"""Die lokalen Textdokumente mit ihrem Quelldateinamen einlesen."""

import re
from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parents[1] / "reference_docs" / "cam03"


def load_documents(directory):
    """Alle direkten .txt-Dateien als Liste aus Quelle und Text laden."""
    if not directory.is_dir():
        raise FileNotFoundError(f"Dokumentenordner fehlt: {directory}")
    paths = sorted(path for path in directory.glob("*.txt") if path.is_file())
    if not paths:
        raise ValueError("Der Dokumentenordner enthält keine .txt-Dateien.")

    documents = []
    for path in paths:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"Das Dokument {path.name} ist leer.")
        documents.append({"source": path.name, "text": text})
    return documents


def split_documents(documents):
    """Dokumente an Überschriften der Form 'Abschnitt 1: ...' aufteilen."""
    chunks = []
    for document in documents:
        parts = re.split(r"(?m)^(Abschnitt [0-9]+:[^\r\n]*)\r?$", document["text"])
        if len(parts) == 1:
            raise ValueError(f"Keine Abschnittsüberschriften in {document['source']} gefunden.")
        header = parts[0].strip()
        if not header:
            raise ValueError(f"Der Dokumenttitel fehlt in {document['source']}.")
        seen_sections = set()
        for index in range(1, len(parts), 2):
            section = parts[index].strip()
            body = parts[index + 1].strip()
            section_id = section.split(":", 1)[0]
            if section_id in seen_sections:
                raise ValueError(f"Doppelter {section_id} in {document['source']}.")
            if not body:
                raise ValueError(f"Leerer {section_id} in {document['source']}.")
            seen_sections.add(section_id)
            chunks.append({
                "source": document["source"],
                "title": header.splitlines()[0],
                "document_header": header,
                "section": section,
                "text": f"{section}\n{body}",
            })
    return chunks


def search_chunks(chunks, query):
    """Alle Chunks mit einem wörtlichen Treffer zurückgeben, unabhängig von Großschreibung."""
    search_text = query.strip().casefold()
    if not search_text:
        raise ValueError("Bitte gib einen nichtleeren Suchbegriff ein.")
    return [chunk for chunk in chunks if search_text in chunk["text"].casefold()]


def main():
    try:
        documents = load_documents(DOCS_DIR)
        chunks = split_documents(documents)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Dokumente konnten nicht geladen werden: {error}")
        return 1

    print(f"Geladene Dokumente: {len(documents)}")
    for document in documents:
        print(f"  - {document['source']}: {len(document['text'])} Zeichen")
    print(f"\nTextabschnitte (Chunks): {len(chunks)}")
    for chunk in chunks:
        print(f"  - {chunk['source']} | {chunk['section']} | {len(chunk['text'])} Zeichen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
