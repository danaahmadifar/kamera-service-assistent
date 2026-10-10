"""HTTP-Antworten und Fehlerfälle des simulierten Status-Endpunkts prüfen."""

import unittest
import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from camera_service.api import app
from camera_service.document_chat import MODEL_ID
from camera_service.documents import DOCS_DIR, load_documents, split_documents
from camera_service.plan_validation import EXAMPLE_JSON


class CameraStatusAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_real_simulation_is_returned_with_python_result(self):
        response = self.client.get("/cameras/cam-03/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"]["camera_id"], "CAM-03")
        self.assertIs(data["status"]["simulated"], True)
        expected = 0 <= data["status"]["temperature_c"] <= 80
        self.assertEqual(data["temperature_check"]["within_range"], expected)

    def test_unknown_camera_is_404_without_reading_status_file(self):
        with patch("camera_service.api.get_camera_status") as read_status:
            response = self.client.get("/cameras/CAM-99/status")
        self.assertEqual(response.status_code, 404)
        self.assertIn("CAM-99", response.json()["detail"])
        read_status.assert_not_called()

    def test_invalid_status_and_missing_file_are_500(self):
        for error in [ValueError("Ungültiger Sensor"), FileNotFoundError("Statusdatei fehlt")]:
            with self.subTest(error=error):
                with patch("camera_service.api.get_camera_status", side_effect=error):
                    with patch("camera_service.api.logger.exception"):
                        response = self.client.get("/cameras/CAM-03/status")
                self.assertEqual(response.status_code, 500)
                self.assertNotIn("status", response.json())

    def test_above_limit_is_returned_as_false_not_http_error(self):
        status = {"camera_id": "CAM-03", "sensor": "board_temperature",
                  "temperature_c": 85.0, "measured_at": "2026-10-07T10:00:00+02:00",
                  "simulated": True}
        with patch("camera_service.api.get_camera_status", return_value=status):
            response = self.client.get("/cameras/CAM-03/status")
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()["temperature_check"]["within_range"], False)


class DocumentSearchAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_ranked_sources_and_text_reach_http_response(self):
        ranked = [(0.9 - i * 0.1, {
            "source": f"datei-{i}.txt", "section": "Abschnitt 2: Prüfung", "text": f"Prüftext {i}",
        }) for i in range(4)]
        with patch("camera_service.api.retrieve_sections", return_value=([], ranked)) as search:
            response = self.client.post("/documents/search", json={"question": "  Sichtscheibe beschlagen?  "})
        self.assertEqual(response.status_code, 200)
        search.assert_called_once_with("Sichtscheibe beschlagen?")
        self.assertEqual(len(response.json()["matches"]), 3)
        self.assertEqual(response.json()["matches"][0]["source"], "datei-0.txt")
        self.assertEqual(response.json()["matches"][0]["text"], "Prüftext 0")

    def test_invalid_request_never_starts_embedding_search(self):
        for body in [{}, {"question": "   "}, {"question": 75},
                     {"question": "x" * 1001}, {"question": "Bild?", "extra": True}]:
            with self.subTest(body=body):
                with patch("camera_service.api.retrieve_sections") as search:
                    response = self.client.post("/documents/search", json=body)
                self.assertEqual(response.status_code, 422)
                search.assert_not_called()

    def test_unavailable_search_is_503_without_fake_matches(self):
        with patch("camera_service.api.retrieve_sections", return_value=None):
            response = self.client.post("/documents/search", json={"question": "Bild unscharf?"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("matches", response.json())


class DocumentAnswerAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.chunks = split_documents(load_documents(DOCS_DIR))
        self.match = next(chunk for chunk in self.chunks
                          if chunk["source"] == "wartung-optik.txt"
                          and chunk["section"].startswith("Abschnitt 2:"))

    def ask_with_completion(self, completion):
        with patch("camera_service.api.retrieve_sections", return_value=(self.chunks, [(0.7, self.match)])):
            with patch("camera_service.document_chat.request_json", side_effect=[
                {"data": [{"id": MODEL_ID}]}, completion,
            ]) as request:
                response = self.client.post("/documents/answer", json={"question": "Sichtscheibe beschlagen?"})
        return response, request

    def test_answer_and_actual_context_sources_reach_http_response(self):
        response, request = self.ask_with_completion({"choices": [{
            "message": {"content": "  Sichtscheibe prüfen (wartung-optik.txt, Abschnitt 2).  "},
            "finish_reason": "stop",
        }]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "Sichtscheibe prüfen (wartung-optik.txt, Abschnitt 2).")
        self.assertEqual(response.json()["finish_reason"], "stop")
        self.assertEqual(response.json()["sources"], [
            {"source": chunk["source"], "section": chunk["section"]}
            for chunk in self.chunks if chunk["source"] == "wartung-optik.txt"
            and chunk["section"].startswith(("Abschnitt 1:", "Abschnitt 2:"))
        ])
        payload = request.call_args.args[2]
        self.assertIn("Sichtscheibe beschlagen?", payload["messages"][1]["content"])
        self.assertIn("keine Live-Befunde", payload["messages"][1]["content"])
        self.assertNotIn("Netzwerkverbindung", payload["messages"][1]["content"])
        self.assertFalse(payload["stream"])

    def test_search_failure_and_blank_question_do_not_call_gemma(self):
        with patch("camera_service.api.retrieve_sections", return_value=None) as search:
            with patch("camera_service.api.generate_context_answer") as generate:
                response = self.client.post("/documents/answer", json={"question": "Bild?"})
                self.assertEqual(response.status_code, 503)
                search.reset_mock()
                response = self.client.post("/documents/answer", json={"question": "   "})
                self.assertEqual(response.status_code, 422)
                search.assert_not_called()
                generate.assert_not_called()

    def test_empty_or_failed_completion_is_502_without_answer(self):
        for completion in [None, {}, {"choices": [{
            "message": {"content": ""}, "finish_reason": "length",
        }]}]:
            with self.subTest(completion=completion):
                response, request = self.ask_with_completion(completion)
                self.assertEqual(response.status_code, 502)
                self.assertNotIn("answer", response.json())

    def test_partial_answer_keeps_length_reason_visible(self):
        response, request = self.ask_with_completion({"choices": [{
            "message": {"content": "Unvollständiger Text"}, "finish_reason": "length",
        }]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["finish_reason"], "length")

    def test_empty_context_does_not_call_gemma(self):
        with patch("camera_service.api.retrieve_sections", return_value=([], [])):
            with patch("camera_service.api.generate_context_answer") as generate:
                response = self.client.post("/documents/answer", json={"question": "Bild?"})
        self.assertEqual(response.status_code, 503)
        generate.assert_not_called()


class ServicePlanAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.chunks = split_documents(load_documents(DOCS_DIR))

    def ask(self, answer=EXAMPLE_JSON, finish_reason="stop"):
        with patch("camera_service.api.retrieve_sections", return_value=(self.chunks, [])):
            with patch("camera_service.document_chat.request_json", side_effect=[
                {"data": [{"id": MODEL_ID}]},
                {"choices": [{"message": {"content": answer}, "finish_reason": finish_reason}]},
            ]) as request:
                response = self.client.post("/cameras/CAM-03/plan")
        return response, request

    def test_valid_plan_uses_real_simulation_and_only_sent_sources(self):
        response, request = self.ask()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["plan"], json.loads(EXAMPLE_JSON))
        self.assertIs(data["status"]["simulated"], True)
        allowed = {(source["source"], source["section"]) for source in data["sources"]}
        for step in data["plan"]["steps"]:
            self.assertIn((step["source"], step["section"]), allowed)
            self.assertEqual(step["status"], "pending")
        payload = request.call_args.args[2]
        self.assertEqual(payload["max_tokens"], 4096)
        self.assertIn(json.dumps(data["status"]["temperature_c"]), payload["messages"][1]["content"])
        self.assertIn('"within_range": ' + json.dumps(data["temperature_check"]["within_range"]),
                      payload["messages"][1]["content"])

    def test_unknown_camera_never_starts_search_or_gemma(self):
        with patch("camera_service.api.retrieve_sections") as search:
            with patch("camera_service.api.generate_context_answer") as generate:
                response = self.client.post("/cameras/CAM-99/plan")
        self.assertEqual(response.status_code, 404)
        search.assert_not_called()
        generate.assert_not_called()

    def test_invalid_or_truncated_model_plan_never_reaches_response(self):
        invalid_source = json.loads(EXAMPLE_JSON)
        invalid_source["steps"][0].update(source="cam-03.txt", section="Abschnitt 3: Angaben für die Bewertung")
        completed = json.loads(EXAMPLE_JSON)
        completed["steps"][0]["status"] = "completed"
        extra = json.loads(EXAMPLE_JSON)
        extra["temperature_check"] = {"within_range": False}
        for answer, reason in [(EXAMPLE_JSON, "length"), ("", "length"), ("Kein JSON", "stop"),
                               (json.dumps(invalid_source), "stop"), (json.dumps(completed), "stop"),
                               (json.dumps(extra), "stop")]:
            with self.subTest(answer=answer[:25], reason=reason):
                response, request = self.ask(answer, reason)
                self.assertEqual(response.status_code, 502)
                self.assertNotIn("plan", response.json())

    def test_missing_required_optics_source_prevents_model_call(self):
        chunks = [chunk for chunk in self.chunks if not (
            chunk["source"] == "wartung-optik.txt" and chunk["section"].startswith("Abschnitt 2:")
        )]
        with patch("camera_service.api.retrieve_sections", return_value=(chunks, [])):
            with patch("camera_service.api.generate_context_answer") as generate:
                response = self.client.post("/cameras/CAM-03/plan")
        self.assertEqual(response.status_code, 503)
        generate.assert_not_called()

    def test_unavailable_search_prevents_model_call(self):
        with patch("camera_service.api.retrieve_sections", return_value=None):
            with patch("camera_service.api.generate_context_answer") as generate:
                response = self.client.post("/cameras/CAM-03/plan")
        self.assertEqual(response.status_code, 503)
        generate.assert_not_called()
