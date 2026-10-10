"""Prüfen, dass nur der ausdrücklich erlaubte Modellvorschlag ausgeführt wird."""

import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from camera_service.tool_calling import MODEL_ID, build_followup_messages, execute_status_tool, main


class StatusToolTests(unittest.TestCase):
    def setUp(self):
        input_patch = patch("builtins.input", return_value="Bewerte die simulierte Temperatur von CAM-03.")
        self.input_mock = input_patch.start()
        self.addCleanup(input_patch.stop)
        self.tool_call = {
            "type": "function",
            "id": "test-call-1",
            "function": {
                "name": "get_camera_status",
                "arguments": '{"camera_id":"CAM-03"}',
            },
        }

    def test_valid_call_passes_camera_id_to_function(self):
        with patch("camera_service.tool_calling.get_camera_status", return_value={"simulated": True}) as status_tool:
            result = execute_status_tool([self.tool_call])
            status_tool.assert_called_once_with("CAM-03")
            self.assertEqual(result, {"simulated": True})

    def test_unknown_function_is_not_executed(self):
        self.tool_call["function"]["name"] = "unknown_function"
        with patch("camera_service.tool_calling.get_camera_status") as status_tool:
            with self.assertRaises(ValueError):
                execute_status_tool([self.tool_call])
            status_tool.assert_not_called()

    def test_missing_call_id_is_rejected_before_execution(self):
        for call_id in (None, "", "   ", 75):
            with self.subTest(call_id=call_id):
                self.tool_call["id"] = call_id
                with patch("camera_service.tool_calling.get_camera_status") as status_tool:
                    with self.assertRaises(ValueError):
                        execute_status_tool([self.tool_call])
                    status_tool.assert_not_called()

    def test_result_is_linked_to_call_and_original_history_is_preserved(self):
        messages = [{"role": "user", "content": "Status von CAM-03?"}]
        assistant_message = {"role": "assistant", "tool_calls": [self.tool_call]}
        result = {"temperature_c": 75.0, "simulated": True}
        followup = build_followup_messages(messages, assistant_message, result)
        self.assertEqual(len(messages), 1)
        self.assertEqual(followup[0], messages[0])
        self.assertEqual(followup[1]["role"], "assistant")
        self.assertEqual(followup[1]["tool_calls"], [self.tool_call])
        self.assertEqual(followup[2]["role"], "tool")
        self.assertEqual(followup[2]["tool_call_id"], self.tool_call["id"])
        self.assertEqual(json.loads(followup[2]["content"]), result)

    def test_full_roundtrip_sends_tool_result_in_second_chat_request(self):
        responses = [
            {"data": [{"id": MODEL_ID}]},
            {"choices": [{"finish_reason": "tool_calls", "message": {
                "role": "assistant", "tool_calls": [self.tool_call],
            }}]},
            {"choices": [{"finish_reason": "stop", "message": {
                "role": "assistant", "content": "Simulierte Temperatur: 75 °C.",
            }}]},
        ]
        result = {
            "camera_id": "CAM-03", "sensor": "board_temperature",
            "temperature_c": 75.0, "simulated": True,
            "measured_at": "2026-10-07T10:00:00+02:00",
        }
        with patch("camera_service.tool_calling.request_json", side_effect=responses) as request:
            with patch("camera_service.tool_calling.get_camera_status", return_value=result) as status_tool:
                with redirect_stdout(io.StringIO()):
                    exit_code = main()
                status_tool.assert_called_once_with("CAM-03")
        self.assertEqual(exit_code, 0)
        self.assertEqual(request.call_count, 3)
        followup_payload = request.call_args_list[2].args[2]
        self.assertNotIn("tools", followup_payload)
        self.assertEqual(followup_payload["messages"][-1]["tool_call_id"], "test-call-1")
        returned_result = json.loads(followup_payload["messages"][-1]["content"])
        self.assertEqual(returned_result["status"], result)
        self.assertTrue(returned_result["temperature_check"]["within_range"])
        self.assertEqual(returned_result["temperature_check"]["maximum_c"], 80.0)
        self.assertIn("cam-03.txt", followup_payload["messages"][0]["content"])

    def test_above_limit_is_returned_as_python_result(self):
        status = {
            "camera_id": "CAM-03", "sensor": "board_temperature",
            "temperature_c": 85.0, "simulated": True,
            "measured_at": "2026-10-07T10:00:00+02:00",
        }
        responses = [
            {"data": [{"id": MODEL_ID}]},
            {"choices": [{"message": {"tool_calls": [self.tool_call]}}]},
            {"choices": [{"message": {"content": "Außerhalb des Bereichs."}}]},
        ]
        with patch("camera_service.tool_calling.request_json", side_effect=responses) as request:
            with patch("camera_service.tool_calling.get_camera_status", return_value=status):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 0)
        followup = request.call_args_list[2].args[2]
        returned_result = json.loads(followup["messages"][-1]["content"])
        self.assertFalse(returned_result["temperature_check"]["within_range"])
        self.assertEqual(returned_result["temperature_check"]["temperature_c"], 85.0)

    def test_invalid_temperature_stops_before_followup_request(self):
        status = {"camera_id": "CAM-03", "sensor": "board_temperature", "temperature_c": None}
        responses = [
            {"data": [{"id": MODEL_ID}]},
            {"choices": [{"message": {"tool_calls": [self.tool_call]}}]},
        ]
        with patch("camera_service.tool_calling.request_json", side_effect=responses) as request:
            with patch("camera_service.tool_calling.get_camera_status", return_value=status):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 1)
        self.assertEqual(request.call_count, 2)

    def test_general_question_returns_text_without_status_or_followup(self):
        question = "Was bedeutet Bildrate?"
        self.input_mock.return_value = question
        responses = [
            {"data": [{"id": MODEL_ID}]},
            {"choices": [{"finish_reason": "stop", "message": {
                "content": "Die Bildrate ist die Anzahl der Bilder pro Sekunde.",
            }}]},
        ]
        output = io.StringIO()
        with patch("camera_service.tool_calling.request_json", side_effect=responses) as request:
            with patch("camera_service.tool_calling.get_camera_status") as status_tool:
                with redirect_stdout(output):
                    self.assertEqual(main(), 0)
                status_tool.assert_not_called()
        self.assertEqual(request.call_count, 2)
        payload = request.call_args_list[1].args[2]
        self.assertEqual(payload["messages"][1]["content"], question)
        self.assertIn("Anzahl der Bilder pro Sekunde", output.getvalue())

    def test_empty_question_does_not_send_http_request(self):
        self.input_mock.return_value = "   "
        with patch("camera_service.tool_calling.request_json") as request:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 1)
            request.assert_not_called()

    def test_empty_model_reply_is_not_reported_as_success(self):
        responses = [
            {"data": [{"id": MODEL_ID}]},
            {"choices": [{"finish_reason": "length", "message": {"content": ""}}]},
        ]
        with patch("camera_service.tool_calling.request_json", side_effect=responses) as request:
            with patch("camera_service.tool_calling.get_camera_status") as status_tool:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 1)
                status_tool.assert_not_called()
        self.assertEqual(request.call_count, 2)

    def test_invalid_arguments_are_not_executed(self):
        for arguments in (
            "kein JSON",
            "[]",
            "{}",
            '{"camera_id":"CAM-99"}',
            '{"camera_id":75}',
            '{"camera_id":"CAM-03","extra":true}',
            {"camera_id": "CAM-03"},
        ):
            with self.subTest(arguments=arguments):
                tool_call = copy.deepcopy(self.tool_call)
                tool_call["function"]["arguments"] = arguments
                with patch("camera_service.tool_calling.get_camera_status") as status_tool:
                    with self.assertRaises(ValueError):
                        execute_status_tool([tool_call])
                    status_tool.assert_not_called()

    def test_invalid_call_structure_is_not_executed(self):
        for tool_calls in (None, [], [self.tool_call, self.tool_call], [None], [{}]):
            with self.subTest(tool_calls=tool_calls):
                with patch("camera_service.tool_calling.get_camera_status") as status_tool:
                    with self.assertRaises(ValueError):
                        execute_status_tool(tool_calls)
                    status_tool.assert_not_called()
