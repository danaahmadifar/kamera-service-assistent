"""Werkzeugregistrierung und SDK-Aufruf ohne Modell oder Netzwerk prüfen."""

import unittest

from mcp import Client

from camera_service.mcp_server import mcp
from camera_service.camera_tools import get_camera_status


class CameraMCPServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_is_discoverable_with_camera_argument(self):
        async with Client(mcp) as client:
            result = await client.list_tools()
        self.assertEqual([tool.name for tool in result.tools], ["get_camera_status"])
        schema = result.tools[0].input_schema
        self.assertEqual(schema["properties"]["camera_id"]["type"], "string")
        self.assertIn("camera_id", schema["required"])

    async def test_sdk_call_returns_the_existing_simulation(self):
        expected = get_camera_status("CAM-03")
        async with Client(mcp) as client:
            result = await client.call_tool("get_camera_status", {"camera_id": "CAM-03"})
        self.assertEqual(result.structured_content, expected)
        self.assertIs(result.structured_content["simulated"], True)
