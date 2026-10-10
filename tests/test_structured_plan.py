"""Echte Programmkette mit simulierten Modellantworten vor der Planausgabe prüfen."""

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from camera_service.document_chat import MODEL_ID
from camera_service.documents import DOCS_DIR, load_documents, split_documents
from camera_service.plan_validation import EXAMPLE_JSON
from camera_service.service_plan import main


class StructuredPlanTests(unittest.TestCase):
    def run_response(self, answer, finish_reason="stop"):
        chunks = split_documents(load_documents(DOCS_DIR))
        responses = [{"data": [{"id": MODEL_ID}]}, {"choices": [{
            "finish_reason": finish_reason, "message": {"content": answer},
        }]}]
        output = io.StringIO()
        with patch("camera_service.service_plan.retrieve_sections", return_value=(chunks, [])):
            with patch("camera_service.document_chat.request_json", side_effect=responses) as request:
                with redirect_stdout(output):
                    result = main(structured=True)
        return result, output.getvalue(), request.call_args.args[2]

    def test_valid_model_plan_is_printed_after_validation(self):
        result, output, payload = self.run_response(EXAMPLE_JSON)
        self.assertEqual(result, 0)
        self.assertIn("Planformat und Quellenpaare geprüft", output)
        self.assertIn("1. Noch durchzuführen:", output)
        self.assertIn("Abschnitt 2: Sichtprüfung bei unscharfem Bild", payload["messages"][1]["content"])
        self.assertNotIn("Abschnitt 3: Angaben für die Bewertung", payload["messages"][1]["content"])

    def test_malformed_json_and_markdown_are_rejected(self):
        for answer in ["Kein JSON", "```json\n" + EXAMPLE_JSON + "\n```"]:
            with self.subTest(answer=answer[:20]):
                result, output, payload = self.run_response(answer)
                self.assertEqual(result, 1)
                self.assertIn("Kein Plan freigegeben", output)
                self.assertNotIn("1. Noch durchzuführen:", output)

    def test_existing_but_unsent_section_is_rejected(self):
        plan = json.loads(EXAMPLE_JSON)
        plan["steps"][0].update(source="cam-03.txt", section="Abschnitt 3: Angaben für die Bewertung")
        result, output, payload = self.run_response(json.dumps(plan))
        self.assertEqual(result, 1)
        self.assertIn("nicht freigegeben", output)
        self.assertNotIn("1. Noch durchzuführen:", output)

    def test_completed_step_is_rejected(self):
        plan = json.loads(EXAMPLE_JSON)
        plan["steps"][0]["status"] = "completed"
        result, output, payload = self.run_response(json.dumps(plan))
        self.assertEqual(result, 1)
        self.assertNotIn("1. Noch durchzuführen:", output)

    def test_length_termination_rejects_even_parseable_plan(self):
        result, output, payload = self.run_response(EXAMPLE_JSON, finish_reason="length")
        self.assertEqual(result, 1)
        self.assertIn("nicht regulär beendet (length)", output)
        self.assertNotIn("1. Noch durchzuführen:", output)

    def test_empty_length_response_never_reaches_plan_output(self):
        result, output, payload = self.run_response("", finish_reason="length")
        self.assertEqual(result, 1)
        self.assertIn("Kein Antworttext erhalten", output)
        self.assertIn("Angefordertes Ausgabelimit: 4096 Tokens", output)
        self.assertNotIn("1. Noch durchzuführen:", output)

    def test_no_model_fields_can_replace_python_temperature_result(self):
        plan = json.loads(EXAMPLE_JSON)
        plan["temperature_check"] = {"within_range": False}
        result, output, payload = self.run_response(json.dumps(plan))
        self.assertEqual(result, 1)
        self.assertIn('"within_range": true', output)
        self.assertNotIn("1. Noch durchzuführen:", output)
