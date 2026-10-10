"""Prüfungen der fiktiven Temperaturregel aus cam-03.txt, Abschnitt 2."""

import unittest

from camera_service.camera_tools import evaluate_temperature, get_camera_status


class TemperatureTests(unittest.TestCase):
    def setUp(self):
        self.status = get_camera_status("CAM-03")

    def test_lower_limit_is_included(self):
        self.status["temperature_c"] = 0.0
        result = evaluate_temperature(self.status)
        self.assertTrue(result["within_range"])

    def test_upper_limit_is_included(self):
        self.status["temperature_c"] = 80.0
        result = evaluate_temperature(self.status)
        self.assertTrue(result["within_range"])

    def test_below_lower_limit_is_outside(self):
        self.status["temperature_c"] = -0.1
        result = evaluate_temperature(self.status)
        self.assertFalse(result["within_range"])

    def test_above_upper_limit_is_outside(self):
        self.status["temperature_c"] = 80.1
        result = evaluate_temperature(self.status)
        self.assertFalse(result["within_range"])

    def test_other_sensor_is_rejected(self):
        self.status["sensor"] = "ambient_temperature"
        with self.assertRaises(ValueError):
            evaluate_temperature(self.status)
