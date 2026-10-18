# Kellerlüftung for Home Assistant

Automatische, messwertbasierte Lüftungssteuerung für kühle Keller und Gewölbekeller. Die Regelung verwendet die **absolute Feuchte** innen und außen, eine Hysterese, Mindestlaufzeit/Mindestpause und optional den Betriebszustand von bis zu zwei Kondenstrocknern.

> Die Integration steuert ausschließlich anhand der gemessenen Raum- und Außenluft. Eine sichere Aussage über Kondensation an der kältesten Wandoberfläche ist ohne Oberflächentemperatursensor nicht möglich.

Version **1.0.1** korrigiert vier priorisierte Fehler. Siehe [Änderungen](CHANGELOG.md) und [Einspielanleitung für HA OS](INSTALLATION-1.0.1.md).

## Installation

### HACS Custom Repository
1. Repository `https://github.com/lenni76/L-ftung-Keller` als benutzerdefiniertes Repository vom Typ **Integration** hinzufügen.
2. **Kellerlüftung** installieren.
3. Home Assistant neu starten.
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Kellerlüftung**.

### Manuell
Den Ordner `custom_components/kellerlueftung` nach `/config/custom_components/kellerlueftung` kopieren und Home Assistant neu starten.

## Einrichtung

Pflichtfelder:
- Kellertemperatur
- Keller-Luftfeuchtigkeit
- Außentemperatur
- Außen-Luftfeuchtigkeit
- Lüfter (`fan` oder `switch`)

Optional:
- Trockner 1
- Trockner 2

Ein Trockner kann als `binary_sensor` oder als Leistungssensor angegeben werden. Bei Leistungssensoren gilt die konfigurierbare Watt-Schwelle.

## Regelung

Die Integration berechnet absolute Feuchte und Taupunkt innen/außen. `Entfeuchtungspotenzial = absolute Feuchte Keller - absolute Feuchte außen`. Nur ein positiver und ausreichend großer Vorteil erlaubt automatisches Lüften. Je höher die relative Kellerfeuchte, desto kleiner ist standardmäßig die erforderliche Differenz. Bei aktivem Trockner wird die erforderliche Differenz um den konfigurierten Bonus reduziert, jedoch niemals unter die sichere Hysterese-Grenze.

Standardwerte:
- Mindestfeuchte: 60 %
- mittlere Feuchtestufe: 65 %
- hohe Feuchtestufe: 75 %
- benötigte Differenz: 1.5 / 1.0 / 0.5 g/m³
- Ausschaltschwelle: 0.4 g/m³
- Trockner-Bonus: 0.5 g/m³
- Mindestlaufzeit: 10 min
- Mindestpause: 10 min
- maximale Laufzeit: deaktiviert

## Entitäten

Die Integration stellt Diagnose-Sensoren für absolute Feuchte, Taupunkte, Entfeuchtungspotenzial, benötigte Differenz, Status und Entscheidung bereit. Zusätzlich gibt es Binärsensoren für „Lüften sinnvoll“, „Trockner aktiv“ und „Sensoren in Ordnung“ sowie eine Betriebsart-Auswahl mit **Automatik**, **Aus** und **Manuell ein**.

## Konfiguration ändern

- **Neu konfigurieren**: Zuordnung der physischen Sensoren, Trockner und des Lüfters.
- **Konfigurieren**: Regelparameter und Zeitwerte.

## Fail-safe

Fehlt im Automatikbetrieb einer der vier Pflicht-Messwerte, ist er nicht endlich oder ist ein Feuchtewert außerhalb 0–100 %, wird die Regelung gesperrt und eine Abschaltung des Lüfters versucht. Für diese Kellerregelung wird ein Temperatur-Eingabebereich von −100 bis +100 °C akzeptiert. Werte außerhalb dieses Bereichs sowie ungültige Rechenergebnisse sperren ebenfalls die Automatik. In diesem Zustand werden keine ungültigen numerischen Diagnosewerte veröffentlicht. Die manuelle Betriebsart ist eine bewusste Benutzerübersteuerung.

Die gewählte Betriebsart wird vor der ersten Regelentscheidung wiederhergestellt und ab Version 1.0.1 separat gespeichert. Beim ersten Update wird der bisherige Zustand der Betriebsart-Auswahl übernommen. Die Auswahl muss dafür aktiviert sein. Ist beim ersten Update weder eine gespeicherte Betriebsart noch eine aktive Auswahl verfügbar, bleibt die Regelung gesperrt. Nach erfolgreicher Übernahme bleibt die Betriebsart auch bei deaktivierter Auswahl erhalten.

## Entwicklung und Validierung

Die Regressionstests für die vier Korrekturen lassen sich ohne installierte HA-Laufzeit mit Python 3.12 oder neuer ausführen:

```sh
python3 -m unittest discover -s tests/standalone -v
```

Sie verwenden unveränderte Produktionsmethoden mit nachgebildeten HA-Schnittstellen. Ein vollständiger HA-Integrationstest wird dadurch nicht ersetzt.

## Lizenz

MIT
