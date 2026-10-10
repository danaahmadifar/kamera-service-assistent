# Vorführung des Kamera-Service-Assistenten

## 1. Start

Docker Desktop und den LM-Studio-API-Server auf dem Windows-PC starten. Die getestete Adresse ist `http://localhost:1234/v1`; Gemma und Nomic müssen unter den im Projekt konfigurierten IDs verfügbar sein.

Im Projektordner:

```powershell
docker compose down
docker compose up -d --build
docker compose ps
```

API und Webserver sollten laufen; die API sollte `healthy` melden. Im Browser **http://127.0.0.1:8090** öffnen und neu laden.

## 2. Axis-Fall zeigen

1. `no_video` auswählen und einen Servicevorschlag erstellen.
2. Datenbasis erklären: Geräteinformationen simuliert, fehlendes Bild nur Benutzerangabe, Übertragungsmodus unbekannt.
3. Quellen und Vorschlag vergleichen. Keine Ursache darf als festgestellt behauptet werden; fehlende Informationen und begrenzte Quellenlage sind zulässige Ergebnisse.
4. Auf Timeout wechseln: Der alte Vorschlag muss sofort verschwinden.
5. Einen neuen Vorschlag abrufen. Der simulierte Geräte-Timeout ist ein gültiger Testfall und kein Ausfall unserer Service-API.

## 3. Erwarteten Fehler zeigen

```powershell
try {
    Invoke-RestMethod `
        -Uri 'http://127.0.0.1:8090/api/axis/service' `
        -Method Post `
        -ContentType 'application/json; charset=utf-8' `
        -Body '{"scenario":"unbekannt"}' `
        -TimeoutSec 15
} catch {
    "HTTP-Status: $([int]$_.Exception.Response.StatusCode)"
    $_.ErrorDetails.Message
}
```

Erwartung: HTTP 422 mit Validierungsdetails, kein Servicevorschlag. Pydantic weist die Szenario-ID vor einem Modellaufruf ab. Ein Verbindungsfehler erfüllt diese Prüfung nicht.

## 4. CAM-03-Funktionen zeigen

* Simulierten Status abrufen: Messzeitpunkt, internen Sensor und Python-Bereichsprüfung erklären.
* Dokumentfrage stellen, beispielsweise: „Was soll ich bei einer beschlagenen Sichtscheibe von CAM-03 prüfen? Nenne Quellen und behaupte keine festgestellte Ursache.“
* Optik-Prüfplan erstellen: Python prüft das Format und Quellenpaare; Tätigkeiten bleiben noch durchzuführen.

## 5. Grenzen erklären

Keine echte Kamera und keine automatisch freigegebene Wartungsdiagnose. Ein Modellvorschlag ist fachlich zu prüfen. Im Axis-Zweig entscheidet eine feste Python-Regel über die Quellen; im CAM-03-Zweig erfolgt eine semantische Suche. Eine formal akzeptierte Quelle belegt nicht automatisch die Aussage.

Alle drei Axis-Browserfälle, der sofortige Szenariowechsel und der HTTP-422-Fehlversuch wurden vom Benutzer lokal bestätigt. 15 Axis-Tests sind lokal bestätigt; beim vollständigen Python-Lauf bestanden 86 Tests. Diese Nachweise betreffen die Simulation, nicht reale Axis-Hardware.

Bei Fehlern:

```powershell
docker compose logs --tail 80 api web
```

Beenden: `docker compose down` im Projektordner.
