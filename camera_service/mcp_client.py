"""Einen lokalen MCP-Server starten und simulierten CAM-03-Status abrufen."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


SERVER_PATH = Path(__file__).resolve().parent / "mcp_server.py"


async def main():
    if not SERVER_PATH.is_file():
        print(f"MCP-Serverdatei fehlt: {SERVER_PATH}")
        return 1
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "camera_service.mcp_server"],
        cwd=SERVER_PATH.parent.parent,
    )
    print("Starte den Kamera-MCP-Server als Unterprozess ...")
    try:
        async with Client(parameters, read_timeout_seconds=15) as client:
            print("MCP-Verbindung hergestellt.")
            tool_list = await client.list_tools()
            print("Angebotene MCP-Werkzeuge:")
            for tool in tool_list.tools:
                print(f"  - {tool.name}")
            if "get_camera_status" not in [tool.name for tool in tool_list.tools]:
                raise ValueError("Der Server bietet get_camera_status nicht an.")

            print("\nRufe get_camera_status mit camera_id=CAM-03 über MCP auf ...")
            result = await client.call_tool("get_camera_status", {"camera_id": "CAM-03"})
            if result.is_error:
                details = "\n".join(block.text for block in result.content if block.type == "text")
                raise ValueError(f"Werkzeugaufruf fehlgeschlagen: {details}")
            status = result.structured_content
            if not isinstance(status, dict) or status.get("camera_id") != "CAM-03" or status.get("simulated") is not True:
                raise ValueError("Unerwartetes Werkzeugergebnis: Simulierte CAM-03-Daten fehlen.")
            print("\nÜber MCP empfangene simulierte Statusdaten:")
            print(json.dumps(status, ensure_ascii=False, indent=2))
    except Exception as error:
        print(f"MCP-Versuch fehlgeschlagen ({type(error).__name__}): {error}")
        print("Prüfe .venv, MCP-Paket und Serverdatei. Servermeldungen stehen gegebenenfalls darüber.")
        return 1

    print("\nMCP-Verbindung geschlossen; der gestartete Serverprozess wurde beendet.")
    print("Gemma und LM Studio wurden nicht aufgerufen. Die Statusdaten sind keine Live-Daten.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("MCP-Client durch Strg+C beendet.", file=sys.stderr)
        raise SystemExit(130)
