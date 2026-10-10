"""Axis-HTTP-Anfragen und Modellfehler ohne laufendes LM Studio prüfen."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from camera_service.api import app
from camera_service.axis_service import MODEL_ID


class AxisAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_invalid_scenarios_never_call_model(self):
        for body in ({}, {"scenario": "CAM-99"}, {"scenario": "no_video", "extra": True}):
            with self.subTest(body=body), patch("camera_service.api.generate_axis_service_advice") as generate:
                response = self.client.post("/axis/service", json=body)
                self.assertEqual(response.status_code, 422)
                generate.assert_not_called()

    def test_simulated_case_and_sources_reach_response(self):
        completion = {"choices": [{"finish_reason": "stop", "message": {
            "content": "Simulation: Bitte Anzahl und Konfiguration der Streams nennen."
        }}]}
        with patch("camera_service.axis_service.request_json", side_effect=[
            {"data": [{"id": MODEL_ID}]}, completion
        ]):
            response = self.client.post("/axis/service", json={"scenario": "no_video"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIs(data["case"]["simulated"], True)
        self.assertEqual(data["case"]["video"]["observation"], "reported_missing")
        self.assertIsNone(data["case"]["video"]["transport"])
        self.assertEqual(data["sources"][0]["section"], "Abschnitt 3: Zusätzliche Videostreams")
        self.assertEqual(data["answer"], completion["choices"][0]["message"]["content"])
        self.assertNotIn("temperature_check", data)

    def test_length_returns_error_without_answer(self):
        completion = {"choices": [{"finish_reason": "length", "message": {"content": "Teiltext"}}]}
        with patch("camera_service.axis_service.request_json", side_effect=[
            {"data": [{"id": MODEL_ID}]}, completion
        ]):
            response = self.client.post("/axis/service", json={"scenario": "no_video"})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("answer", response.json())

    def test_missing_fixture_returns_server_error(self):
        with patch("camera_service.api.generate_axis_service_advice", side_effect=FileNotFoundError("fehlt")):
            with patch("camera_service.api.logger.exception"):
                response = self.client.post("/axis/service", json={"scenario": "unreachable"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("answer", response.json())


if __name__ == "__main__":
    unittest.main()
