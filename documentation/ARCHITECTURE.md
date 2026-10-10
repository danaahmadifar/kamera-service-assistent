# Architektur und API

## Zwei getrennte Serviceabläufe

**Axis:** React → `POST /axis/service` → simuliertes Szenario → feste Quellenauswahl → Gemma → freier Text mit separater Datenbasis und Quellen. Keine Nomic-Abfrage, CAM-03-Temperaturprüfung oder formale Planvalidierung.

**CAM-03:** Dokumentfragen verwenden Nomic und Gemma. Der Statusabruf benötigt kein Modell. Der Optik-Prüfplan kombiniert Status, Python-Temperaturprüfung, semantische Fundstellen und Pflichtquellen; Gemmas JSON wird formal geprüft.

## Prozesse und Adressen

| Prozess | Compose-Betrieb | Lokale Entwicklung |
| --- | --- | --- |
| Browser | PC: `127.0.0.1:8090` | PC: `127.0.0.1:5173` |
| Webserver | Nginx-Container: Port 80 | Vite auf dem PC: Port 5173 |
| API | API-Container: `api:8000`, kein veröffentlichter Host-Port | Uvicorn auf dem PC: Port 8000 |
| LM Studio | Windows-Host: Port 1234 | Windows-Host: Port 1234 |

Nginx und Vite entfernen beim Weiterleiten das Präfix `/api`. Im Container verwendet die API `http://host.docker.internal:1234/v1`; lokale Python-Aufrufe verwenden standardmäßig `http://localhost:1234/v1`.

## API-Endpunkte

| Methode | Pfad in FastAPI | Eingabe | Ergebnis |
| --- | --- | --- | --- |
| GET | `/health` | – | Erreichbarkeit der Anwendung, kein Modell- oder Kamera-Test |
| GET | `/cameras/{camera_id}/status` | CAM-03 | Simulierte Messung und Python-Temperaturprüfung |
| POST | `/documents/search` | `{"question":"…"}` | Drei ähnliche CAM-03-Abschnitte mit Scores |
| POST | `/documents/answer` | `{"question":"…"}` | Gemmas Text, Abbruchgrund und mitgesendete Quellen |
| POST | `/cameras/{camera_id}/plan` | CAM-03, kein Body | Formal geprüfter Optik-JSON-Plan mit Datenbasis |
| POST | `/axis/service` | `{"scenario":"no_video"}` | Axis-Fall, Textvorschlag, Quellen und Hinweis |

HTTP 422 bezeichnet eine abgewiesene Eingabe, 404 eine unbekannte CAM-03-ID. Nicht lesbare Simulationsdateien führen im Status-/Axis-Endpoint zu 500; fehlgeschlagene Modellantworten zu 502. Die CAM-03-Suche verwendet bei nicht verfügbarer Suche 503. Ein simulierter Geräte-Timeout ist dagegen ein gültiger Servicefall und kann mit HTTP 200 beantwortet werden.

## Python-Module

| Modul in `camera_service/` | Aufgabe |
| --- | --- |
| `api.py` | FastAPI-Anwendung, Eingabeprüfung und HTTP-Antworten |
| `lm_studio.py` | Gemeinsamer requests-Client, URL und Modell-IDs |
| `documents.py` | Dateien laden, Abschnitte bilden, wörtliche Suche |
| `semantic_search.py` | Nomic-Embeddings prüfen und nach Kosinusähnlichkeit sortieren |
| `document_chat.py` | Quellenkontext und CAM-03-Modellantwort |
| `semantic_chat.py` | CLI für Dokumentfragen mit semantischer Suche |
| `camera_tools.py` | Simulierter CAM-03-Status und feste Temperaturregel |
| `service_plan.py` | Pflichtquellen und Optik-Prüfplan, auch als CLI |
| `plan_validation.py` | Struktur, `pending` und erlaubte Quellenpaare prüfen |
| `axis_device.py` | Nachgebildete Geräteinformationsantwort lesen |
| `axis_scenarios.py` | Drei getrennte Geräte-/Videofälle simulieren |
| `axis_context.py` | Axis-Abschnitt anhand einer festen Regel auswählen |
| `axis_service.py` | Eigene Axis-Systemnachricht und vollständiger Textvorschlag |
| `tool_calling.py` | Gemma-Werkzeugvorschlag prüfen, ausführen und zurücksenden |
| `mcp_server.py` | CAM-03-Statuswerkzeug per stdio anbieten |
| `mcp_client.py` | Serverprozess starten, Werkzeug aufrufen und Verbindung schließen |

Die HTTP-API ruft Python-Funktionen direkt auf. MCP und Tool Calling sind separat ausführbare Integrationsbeispiele, keine versteckten Bestandteile der Browser-API.

## Daten und Quellen

* `data/cam-03-status.json`: feste fiktive Temperaturmessung mit Messzeitpunkt und Simulationskennzeichnung.
* `data/axis/device-info.json`: eigener Simulationsumschlag mit nachgebildeter VAPIX-Antwort.
* `data/axis/scenarios.json`: eigene Fallbeschreibung; kein VAPIX-Protokoll und keine echte HTTP-Verbindung.
* `reference_docs/cam03/`: drei fiktive Dokumente, neun Abschnitte.
* `reference_docs/axis/`: kurze eigene Handbuchzusammenfassungen mit Originalquellen.

Alle Dateipfade werden relativ zum Paketstandort aufgelöst. Die Textauswahl bewahrt Dokumentkopf, Geltungsbereich und Abschnittsquelle. Dokumente werden als Daten an das Modell übergeben; ihre Inhalte sind keine zusätzlichen Systemanweisungen.

## Separate CLI-Aufrufe

Aus dem Projektordner mit eingerichteter `.venv`:

```powershell
.\.venv\Scripts\python.exe -m camera_service.axis_scenarios no_video
.\.venv\Scripts\python.exe -m camera_service.axis_context no_video
.\.venv\Scripts\python.exe -m camera_service.axis_service no_video
.\.venv\Scripts\python.exe -m camera_service.semantic_chat
.\.venv\Scripts\python.exe -m camera_service.service_plan --json
.\.venv\Scripts\python.exe -m camera_service.tool_calling
.\.venv\Scripts\python.exe -m camera_service.mcp_client
```

Szenarien, Kontext und MCP benötigen kein LM Studio. Axis-Service, semantischer Chat, Optik-Plan und Tool Calling rufen die lokale Modell-API auf. `mcp_client` startet seinen Server selbst; stdout des Servers bleibt für Protokollnachrichten reserviert.

## Validierung und Prüfnachweise

86 Python-Tests decken JSON- und Quellenverarbeitung, Grenzwerte, Tool-Argumente, API-Fehler, gekürzte Modellantworten und einen echten stdio-Subprozess ab. Die 15 Axis-Tests wurden auch vom Benutzer lokal bestätigt. Nach der Umordnung bestanden alle 86 Tests auf Windows und im frisch gebauten Linux-Image. Frontend-Build, Webassets, Nginx-Weiterleitung, Health, Statusabruf, HTTP 422 und Quellenpfade wurden ebenfalls geprüft. Frühere echte Modell- und Browserversuche bleiben zusätzlich dokumentiert; die Strukturprüfung erzeugte keine neuen Gemma-Antworten.

Der Axis-Aufruf gibt nur nichtleeren Text mit `finish_reason: stop` aus. Ein CAM-03-JSON-Plan wird bei anderem Abbruchgrund abgewiesen. Gewöhnliche Dokumentantworten können dagegen einen gekürzten Text mit sichtbarem `length`-Hinweis liefern. Keine dieser Prüfungen bestätigt die fachliche Richtigkeit des Textes.
