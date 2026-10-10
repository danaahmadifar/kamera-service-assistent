"""Den Weg von Embedding-Suche zu Modellkontext ohne echten Server prüfen."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from camera_service.document_chat import MODEL_ID
from camera_service.lm_studio import EMBEDDING_MODEL_ID
from camera_service.semantic_chat import main


class SemanticChatTests(unittest.TestCase):
    def test_ranked_sections_and_scope_reach_gemma_but_lowest_section_does_not(self):
        documents = [{"source": "optik.txt", "text": (
            "Optik\nVersion: 1.0\n"
            "Abschnitt 1: Geltungsbereich\nFiktives Lernprojekt.\n"
            "Abschnitt 2: Sichtprüfung\nAuf Kondenswasser prüfen.\n"
            "Abschnitt 3: Vergleich\nTag und Nacht vergleichen.\n"
            "Abschnitt 4: Beobachtung\nBefunde dokumentieren.\n"
            "Abschnitt 5: Andere Angaben\nUNPASSENDER TEXT."
        )}]
        vectors = [[1, 0], [0, 1], [1, 0.1], [1, 0.5], [1, 1], [-1, 0]]
        responses = [
            {"data": [{"id": EMBEDDING_MODEL_ID}]},
            {"data": [{"index": i, "embedding": vector} for i, vector in enumerate(vectors)]},
            {"data": [{"id": MODEL_ID}]},
            {"choices": [{"finish_reason": "stop", "message": {
                "content": "Kondenswasser prüfen (optik.txt, Abschnitt 2).",
            }}]},
        ]
        with patch("builtins.input", return_value="Warum ist die Scheibe beschlagen?"):
            with patch("camera_service.semantic_search.load_documents", return_value=documents):
                with patch("camera_service.semantic_search.request_json", side_effect=responses[:2]) as embedding_api:
                    with patch("camera_service.document_chat.request_json", side_effect=responses[2:]) as chat_api:
                        with redirect_stdout(io.StringIO()):
                            self.assertEqual(main(), 0)
        inputs = embedding_api.call_args_list[1].args[2]["input"]
        self.assertTrue(inputs[0].startswith("search_query: "))
        self.assertTrue(all(text.startswith("search_document: ") for text in inputs[1:]))
        payload = chat_api.call_args_list[1].args[2]
        context = payload["messages"][1]["content"]
        self.assertIn("Fiktives Lernprojekt.", context)
        self.assertIn("optik.txt | Abschnitt 2: Sichtprüfung", context)
        self.assertIn("Warum ist die Scheibe beschlagen?", context)
        self.assertNotIn("UNPASSENDER TEXT", context)
        self.assertEqual(payload["model"], MODEL_ID)
        self.assertFalse(payload["stream"])

    def test_embedding_failure_prevents_chat_request(self):
        with patch("builtins.input", return_value="Beschlagene Scheibe?"):
            with patch("camera_service.semantic_search.request_json", return_value=None):
                with patch("camera_service.document_chat.request_json") as chat_api:
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(main(), 1)
                    chat_api.assert_not_called()
