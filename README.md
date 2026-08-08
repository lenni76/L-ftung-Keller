# Kellerlüftung for Home Assistant

Automatische, messwertbasierte Lüftungssteuerung für kühle Keller und Gewölbekeller. Die Regelung verwendet die **absolute Feuchte** innen und außen, eine Hysterese, Mindestlaufzeit/Mindestpause und optional den Betriebszustand von bis zu zwei Kondenstrocknern.

> Version 1.0.0 steuert ausschließlich anhand der gemessenen Raum- und Außenluft. Eine sichere Aussage über Kondensation an der kältesten Wandoberfläche ist ohne Oberflächentemperatursensor nicht möglich.

## Installation

### HACS Custom Repository
1. Repository `https://github.com/lenni76/ha-kellerlueftung` als benutzerdefiniertes Repository vom Typ **Integration** hinzufügen.
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

Fehlt im Automatikbetrieb einer der vier Pflicht-Messwerte oder ist ein Feuchtewert unplausibel, wird der Lüfter abgeschaltet. Die manuelle Betriebsart ist eine bewusste Benutzerübersteuerung.

## Entwicklung und Validierung

Das Repository enthält Workflows für HACS Validation und Hassfest. Für eine Aufnahme als HACS-Standardrepository ist zusätzlich ein Eintrag im offiziellen `home-assistant/brands` Repository erforderlich.

## Lizenz

MIT
