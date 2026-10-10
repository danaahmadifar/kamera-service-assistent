"""Prüfen, welche Fundstellen mitgesendet werden und wann die API unberührt bleibt."""

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from camera_service.document_chat import MODEL_ID, main


class DocumentChatTests(unittest.TestCase):
    def setUp(self):
        self.documents = [
            {"source": "optik.txt", "text": (
                "Optik-Dokument\nVersion: 1.0\n"
                "Abschnitt 1: Geltungsbereich\nFiktive CAM-03.\n"
                "Abschnitt 2: Sichtprüfung\nSichtscheibe auf Kondenswasser prüfen.\n"
                "Abschnitt 3: Andere Angaben\nNicht benötigte Fokuswerte."
            )},
            {"source": "netzwerk.txt", "text": (
                "Netzwerk-Dokument\nAbschnitt 1: Geltungsbereich\nFiktive Netzwerkprüfung.\n"
                "Abschnitt 2: Diagnose\nNetzwerkverbindung überprüfen."
            )},
        ]

    def test_found_section_and_its_scope_are_sent_without_unrelated_text(self):
        question = "Was soll ich an der Sichtscheibe prüfen?"
        responses = [
            {"data": [{"id": MODEL_ID}]},
            {"choices": [{"finish_reason": "stop", "message": {
                "content": "Kondenswasser prüfen (optik.txt, Abschnitt 2).",
            }}]},
        ]
        with patch("builtins.input", side_effect=["Kondenswasser", question]):
            with patch("camera_service.document_chat.load_documents", return_value=self.documents):
                with patch("camera_service.document_chat.request_json", side_effect=responses) as request:
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(main(), 0)
        self.assertEqual(request.call_count, 2)
        payload = request.call_args_list[1].args[2]
        context = payload["messages"][1]["content"]
        self.assertIn(question, context)
        self.assertIn("optik.txt | Abschnitt 2: Sichtprüfung", context)
        self.assertIn("Fiktive CAM-03.", context)
        self.assertNotIn("Fokuswerte", context)
        self.assertNotIn("Netzwerkverbindung", context)
        self.assertNotIn("tools", payload)

    def test_no_matches_does_not_contact_model(self):
        with patch("builtins.input", side_effect=["Zahnräder", "Welche Angaben gibt es dazu?"]):
            with patch("camera_service.document_chat.load_documents", return_value=self.documents):
                with patch("camera_service.document_chat.request_json") as request:
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(main(), 0)
                    request.assert_not_called()

    def test_empty_question_does_not_contact_model(self):
        with patch("builtins.input", side_effect=["Kondenswasser", "   "]):
            with patch("camera_service.document_chat.request_json") as request:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 1)
                request.assert_not_called()
