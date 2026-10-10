"""Fehlerhafte Modellantworten dürfen nicht als vollständiger Vorschlag gelten."""

import unittest
from unittest.mock import patch

from camera_service.axis_service import MODEL_ID, generate_axis_service_advice


class AxisServiceTests(unittest.TestCase):
    def answer(self, content, reason):
        return {"choices": [{"finish_reason": reason, "message": {"content": content}}]}

    def run_with_response(self, response):
        with patch("camera_service.axis_service.request_json", side_effect=[
            {"data": [{"id": MODEL_ID}]}, response
        ]):
            return generate_axis_service_advice("no_video")

    def test_token_limited_text_is_rejected_even_when_nonempty(self):
        with self.assertRaisesRegex(ValueError, "Tokenlimit"):
            self.run_with_response(self.answer("Ein unvollständiger Vorschlag", "length"))

    def test_empty_successful_answer_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "keinen Antworttext"):
            self.run_with_response(self.answer("  ", "stop"))

    def test_missing_completion_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "gültige Modellantwort"):
            self.run_with_response(None)

    def test_missing_model_prevents_generation(self):
        with patch("camera_service.axis_service.request_json", return_value={"data": []}) as request:
            with self.assertRaisesRegex(ValueError, "nicht verfügbar"):
                generate_axis_service_advice("no_video")
            self.assertEqual(request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
