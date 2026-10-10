"""Einen echten stdio-Aufruf zwischen Client- und Serverprozess prüfen."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CLIENT_PATH = Path(__file__).resolve().parents[1] / "camera_service" / "mcp_client.py"


class CameraMCPClientTests(unittest.TestCase):
    def test_stdio_roundtrip_works_from_another_working_directory(self):
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        environment["PYTHONPATH"] = str(CLIENT_PATH.parent.parent)
        with tempfile.TemporaryDirectory(prefix="kamera-mcp-test-") as directory:
            result = subprocess.run(
                [sys.executable, "-m", "camera_service.mcp_client"], cwd=directory,
                env=environment, capture_output=True, text=True, encoding="utf-8",
                timeout=25,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MCP-Verbindung hergestellt.", result.stdout)
        self.assertIn("  - get_camera_status", result.stdout)
        self.assertIn('"camera_id": "CAM-03"', result.stdout)
        self.assertIn('"simulated": true', result.stdout)
        self.assertIn("MCP-Verbindung geschlossen", result.stdout)
