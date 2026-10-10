"""Trennung der Python-Prüfung und des geplanten Optik-Ablaufs prüfen."""

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from camera_service.document_chat import MODEL_ID, answer_from_context
from camera_service.documents import DOCS_DIR, load_documents, split_documents
from camera_service.service_plan import main


class ServicePlanTests(unittest.TestCase):
    def test_real_evaluation_and_required_sources_reach_model(self):
        chunks = split_documents(load_documents(DOCS_DIR))
        ranked = [(0.9, chunk) for chunk in chunks if chunk["source"] == "netzwerk-diagnose.txt"]
        for temperature, expected in [(75.0, True), (85.0, False)]:
            status = {"camera_id": "CAM-03", "sensor": "board_temperature",
                      "temperature_c": temperature, "measured_at": "2026-10-07T10:00:00+02:00",
                      "simulated": True}
            with self.subTest(temperature=temperature):
                with patch("camera_service.service_plan.get_camera_status", return_value=status):
                    with patch("camera_service.service_plan.retrieve_sections", return_value=(chunks, ranked)):
                        with patch("camera_service.service_plan.answer_from_context", return_value=0) as answer:
                            with redirect_stdout(io.StringIO()):
                                self.assertEqual(main(), 0)
                context = answer.call_args.args[1]
                self.assertIn("cam-03.txt | Abschnitt 2: Temperaturbereiche", context)
                self.assertIn("wartung-optik.txt | Abschnitt 3: Abgrenzung", context)
                self.assertEqual(answer.call_args.kwargs["evidence"]["temperature_check"]["within_range"], expected)

    def test_invalid_temperature_stops_before_any_model_request(self):
        with patch("camera_service.service_plan.get_camera_status", return_value={"camera_id": "CAM-03", "sensor": "wrong"}):
            with patch("camera_service.service_plan.retrieve_sections") as search:
                with patch("camera_service.service_plan.answer_from_context") as answer:
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(main(), 1)
                    search.assert_not_called()
                    answer.assert_not_called()

    def test_missing_required_source_prevents_gemma_call(self):
        with patch("camera_service.service_plan.retrieve_sections", return_value=([], [])):
            with patch("camera_service.service_plan.answer_from_context") as answer:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 1)
                answer.assert_not_called()

    def test_optional_evidence_is_transmitted_without_changing_boolean(self):
        evidence = {"temperature_check": {"within_range": False}}
        responses = [{"data": [{"id": MODEL_ID}]}, {"choices": [{
            "finish_reason": "stop", "message": {"content": "Außerhalb des Bereichs."},
        }]}]
        with patch("camera_service.document_chat.request_json", side_effect=responses) as request:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(answer_from_context("Prüfplan", "Quellen", evidence), 0)
        payload = request.call_args.args[2]
        self.assertIn(json.dumps(evidence, ensure_ascii=False, indent=2), payload["messages"][1]["content"])
        self.assertIn("Messzeitpunkt ist kein Zeitpunkt der Bildstörung", payload["messages"][0]["content"])
