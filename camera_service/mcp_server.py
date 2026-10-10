"""Ein einziges MCP-Werkzeug für simulierte CAM-03-Statusdaten anbieten."""

import sys

from mcp.server import MCPServer

from camera_service.camera_tools import get_camera_status as read_camera_status


mcp = MCPServer("Camera Service Assistant")


@mcp.tool()
def get_camera_status(camera_id: str) -> dict[str, str | float | bool]:
    """Simulierte Statusdaten für CAM-03 aus der lokalen JSON-Datei lesen; keine Live-Daten."""
    return read_camera_status(camera_id)


if __name__ == "__main__":
    # stdout ist für MCP-Nachrichten reserviert; Meldungen gehen an stderr.
    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        print("MCP-Server durch Strg+C beendet.", file=sys.stderr)
