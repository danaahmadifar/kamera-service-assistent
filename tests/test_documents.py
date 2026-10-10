"""Abschnittsgrenzen, vollständigen Inhalt und Quellenzuordnung prüfen."""

import unittest

from camera_service.documents import search_chunks, split_documents


class DocumentChunkTests(unittest.TestCase):
    def setUp(self):
        self.document = {
            "source": "beispiel.txt",
            "text": (
                "Beispieldokument\nVersion: 1.0\n\n"
                "Abschnitt 1: Temperatur\nDer interne Grenzwert ist 80 °C.\n\n"
                "Abschnitt 2: Optik\nSichtscheibe auf Schmutz prüfen."
            ),
        }

    def test_sections_preserve_text_and_source_without_mixing(self):
        chunks = split_documents([self.document])
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["source"], "beispiel.txt")
        self.assertEqual(chunks[1]["source"], "beispiel.txt")
        self.assertEqual(chunks[0]["title"], "Beispieldokument")
        self.assertEqual(chunks[0]["document_header"], "Beispieldokument\nVersion: 1.0")
        self.assertEqual(chunks[0]["section"], "Abschnitt 1: Temperatur")
        self.assertEqual(chunks[0]["text"], "Abschnitt 1: Temperatur\nDer interne Grenzwert ist 80 °C.")
        self.assertEqual(chunks[1]["text"], "Abschnitt 2: Optik\nSichtscheibe auf Schmutz prüfen.")

    def test_missing_section_headings_are_rejected(self):
        self.document["text"] = "Beispieldokument\nText ohne Abschnittsüberschrift."
        with self.assertRaises(ValueError):
            split_documents([self.document])

    def test_empty_section_is_rejected(self):
        self.document["text"] = "Beispieldokument\nAbschnitt 1: Temperatur\n\nAbschnitt 2: Optik\nText."
        with self.assertRaises(ValueError):
            split_documents([self.document])

    def test_duplicate_section_number_is_rejected(self):
        self.document["text"] = "Beispieldokument\nAbschnitt 1: Temperatur\nText.\nAbschnitt 1: Optik\nAnderer Text."
        with self.assertRaises(ValueError):
            split_documents([self.document])


class ChunkSearchTests(unittest.TestCase):
    def setUp(self):
        self.chunks = split_documents([{
            "source": "beispiel.txt",
            "text": (
                "Beispieldokument\n"
                "Abschnitt 1: Optik\nSichtscheibe auf Kondenswasser prüfen.\n"
                "Abschnitt 2: Netzwerk\nNetzwerkverbindung überprüfen."
            ),
        }])

    def test_case_insensitive_match_preserves_source_and_section(self):
        matches = search_chunks(self.chunks, "  KONDENSWASSER  ")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["source"], "beispiel.txt")
        self.assertEqual(matches[0]["section"], "Abschnitt 1: Optik")
        self.assertIn("Sichtscheibe auf Kondenswasser prüfen.", matches[0]["text"])

    def test_phrase_requires_contiguous_text(self):
        self.assertEqual(len(search_chunks(self.chunks, "auf Kondenswasser")), 1)
        self.assertEqual(search_chunks(self.chunks, "Kondenswasser Sichtscheibe"), [])

    def test_absent_term_returns_no_matches(self):
        self.assertEqual(search_chunks(self.chunks, "Zahnräder"), [])

    def test_empty_query_is_rejected(self):
        with self.assertRaises(ValueError):
            search_chunks(self.chunks, "   ")
