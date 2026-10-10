"""Herkunft, Abrufgrenzen und Quellenkontext der Axis-Servicefälle prüfen."""

import copy
import json
import unittest
from unittest.mock import patch

from camera_service.axis_context import prepare_axis_context
from camera_service.axis_scenarios import SCENARIOS_PATH, load_scenario, simulate_service_case
from camera_service.axis_service import generate_axis_service_advice


class AxisScenarioTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))

    def load_changed_fixture(self, fixture):
        with patch("camera_service.axis_scenarios.SCENARIOS_PATH") as path:
            path.read_text.return_value = json.dumps(fixture)
            return load_scenario("no_video")

    def test_failed_device_requests_do_not_load_or_include_device_properties(self):
        for scenario in ("unreachable", "access_denied"):
            with self.subTest(scenario=scenario):
                with patch("camera_service.axis_scenarios.load_simulated_device_info") as device_info:
                    case = simulate_service_case(scenario)
                device_info.assert_not_called()
                self.assertNotIn("response", case["device_info"])
                self.assertEqual(case["video"]["observation"], "not_checked")
                self.assertIs(case["simulated"], True)

    def test_successful_device_request_does_not_become_verified_video(self):
        case = simulate_service_case("no_video")
        self.assertEqual(case["device_info"]["response"]["data"]["propertyList"]["ProdNbr"], "M2035-LE")
        self.assertEqual(case["video"]["observation"], "reported_missing")
        self.assertIsNone(case["video"]["transport"])

    def test_missing_false_or_text_simulation_label_is_rejected(self):
        for value in (None, False, "true", 1):
            with self.subTest(value=value):
                fixture = copy.deepcopy(self.fixture)
                fixture["simulated"] = value
                with self.assertRaisesRegex(ValueError, "simulated"):
                    self.load_changed_fixture(fixture)

    def test_claim_of_verified_video_is_not_accepted_as_supported_observation(self):
        fixture = copy.deepcopy(self.fixture)
        fixture["scenarios"]["no_video"]["video"]["observation"] = "verified_missing"
        with self.assertRaisesRegex(ValueError, "Videobeobachtung"):
            self.load_changed_fixture(fixture)

    def test_invalid_scenario_does_not_contact_model(self):
        with patch("camera_service.axis_service.request_json") as request:
            with self.assertRaisesRegex(ValueError, "Unbekanntes Szenario"):
                generate_axis_service_advice("not_a_scenario")
            request.assert_not_called()

    def test_unknown_transport_excludes_multicast_context_for_every_case(self):
        for scenario in ("unreachable", "access_denied", "no_video"):
            with self.subTest(scenario=scenario):
                prepared = prepare_axis_context(scenario)
                self.assertNotIn("Abschnitt 2: Fehlendes Multicast", prepared["context"])
                self.assertNotIn("cam-03.txt", prepared["context"])
                self.assertIn("https://help.axis.com/", prepared["context"])
                self.assertIn("T10175189", prepared["context"])
                self.assertIn("Fundstelle: Seite", prepared["context"])

    def test_missing_required_source_prevents_model_call(self):
        document = {"source": "zugriff-und-videobild.txt", "text": (
            "Axis-Notiz\nAbschnitt 1: Gerätezugriff\nEin Hinweis zum Zugriff."
        )}
        with patch("camera_service.axis_context.load_documents", return_value=[document]):
            with patch("camera_service.axis_service.request_json") as request:
                with self.assertRaisesRegex(ValueError, "Quelle fehlt"):
                    generate_axis_service_advice("no_video")
                request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
