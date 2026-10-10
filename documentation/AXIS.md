# Axis-Quellen und Simulationsumfang

## Anwendungsfall

„Kein Videobild“ an einer AXIS M2035-LE als begrenzter Proof of Concept. Es gibt keine angeschlossene Axis-Kamera und keinen Hardware-Kompatibilitätstest.

## Originalquellen

| Quelle | Verwendung |
| --- | --- |
| [AXIS M20 Bullet Camera Series – User manual](https://help.axis.com/download/um_m2035_le_t10175189_2412.pdf) | Gerätezugriff, fehlendes Multicast-H.264-Bild und zusätzliche Videostreams |
| [VAPIX – Basic device information](https://developer.axis.com/vapix/network-video/basic-device-information/) | Struktur einer JSON-Geräteinformationsantwort |

Das verwendete Handbuch trägt die Kennung **T10175189**, Ausgabe **2026-07 (M25.2)**. Online geprüft am **10. Oktober 2026**. Es umfasst M2035-LE und M2036-LE; modellabhängige Einschränkungen bleiben zu beachten. Seitenangaben beziehen sich auf gedruckte Seiten.

`reference_docs/axis/zugriff-und-videobild.txt` enthält kurze eigene deutsche Zusammenfassungen, keine vollständige Kopie und keine autorisierte Übersetzung des Handbuchs. Jede Fundstelle behält Originalabschnitt, Seite und Geltungsbereich.

## Nachgebildete Geräteinformationen

`data/axis/device-info.json` enthält `simulated: true` als eigene Herkunftskennzeichnung. Unter `response` liegt die nachgebildete Antwort mit `apiVersion`, `context` und `data.propertyList`. Die Gerätefelder sind `Brand`, `ProdNbr` und `Version`.

`SIMULATED-OS` ist ein erfundener Platzhalter, keine echte Firmwareversion. Die Beispielantwort wurde nicht von einem Gerät abgerufen. Der Simulator stellt keinen VAPIX-HTTP-Server bereit; er liest lokale JSON-Dateien.

## Drei Testfälle

| ID | Geräteabruf | Videobeobachtung |
| --- | --- | --- |
| `unreachable` | Timeout auf diesen Abruf | Nicht geprüft |
| `access_denied` | Abruf abgewiesen | Nicht geprüft |
| `no_video` | Simulierte Geräteinformationen vorhanden | Benutzerangabe: kein Bild |

`video.transport` bleibt in diesen ersten Fällen `null`. Ein erfolgreicher Geräteabruf beweist keinen funktionierenden Videostream. Ein Timeout belegt weder die Ursache noch die generelle Unerreichbarkeit aller Gerätedienste. `access_denied` beweist kein falsches Passwort.

## Quellenauswahl

Die feste Projektregel wählt Abschnitt 1 bei Abruffehlern und Abschnitt 3 bei erfolgreichem Abruf. Abschnitt 2 (Multicast-H.264) wird bei unbekanntem Modus nicht mitgegeben. Das ist eine begrenzte Auswahlregel für unsere Szenarien, keine vom Hersteller vorgeschriebene Diagnose.

Die Anzahl unterschiedlich konfigurierter Streams ist unbekannt. Abschnitt 3 liefert daher höchstens einen möglichen Prüfhinweis. DHCP-Wechsel und aktives HTTPS sind ebenfalls offene Bedingungen. Der Vorschlag darf aus den Fundstellen keine bereits festgestellte Ursache ableiten.

## Beobachtete Grenzen

Gemma hat die unzureichende Quellenlage teilweise ausdrücklich benannt. In einem Timeout-Versuch bezeichnete es das Gerät allerdings allgemein als „nicht erreichbar“. Diese Verallgemeinerung ist durch die Daten nicht belegt. Prompt-Regeln und bestandene Tests verhindern solche Modellfehler nicht zuverlässig.
