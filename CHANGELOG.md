# Änderungen

## 1.0.1 – 18. Oktober 2026

Korrektur der vier hoch priorisierten Befunde aus der Prüfung von Version 1.0.0:

- **Optionsdialog:** Der Optionsflow wird ohne ConfigEntry-Konstruktorargument erzeugt. Die von Home Assistant bereitgestellte schreibgeschützte Eigenschaft `config_entry` wird verwendet.
- **Entitätsaktualisierung:** Der Dispatcher-Empfänger ist mit `@callback` gekennzeichnet und schreibt Zustände im Ereignisloop.
- **Betriebsart beim Start:** Die Regelung beginnt nach dem Laden der Plattformen und der Betriebsart. Die Betriebsart wird mit HAs `Store` pro Konfiguration gespeichert. Bestehende Zustände der Betriebsart-Auswahl werden beim ersten Update übernommen. Vor Abschluss des Starts werden keine Schaltbefehle ausgeführt. Ohne wiederherstellbare Betriebsart bleibt die Automatik gesperrt.
- **Ungültige Messwerte:** Nicht endliche Zahlen, Temperaturen außerhalb des für diese Regelung festgelegten Bereichs −100 bis +100 °C und ungültige Berechnungsergebnisse werden abgefangen. Die Automatik sperrt und versucht den Lüfter auszuschalten; ungültige numerische Diagnosewerte werden nicht veröffentlicht.

23 Regressionstests mit nachgebildeten HA-Schnittstellen bestehen. Syntax- und JSON-Prüfungen bestehen ebenfalls. Zusätzlich wurden das Einspielen in eine bestehende HA-Core-2026.10.2-Installation, der Core-Neustart, die Erkennung der Integration und das Öffnen des Einrichtungsdialogs erfolgreich geprüft. Die Lüftersteuerung mit zugeordneten realen Geräten, Hassfest und HACS-Validation wurden nicht geprüft.

Die mittel priorisierten Befunde zu externen Schaltungen/Zeitstempeln, Aktorwechsel, Einschalten im manuellen Modus bei ausgefallenen Sensoren und Temperatur-Einheitenumrechnung sind nicht Bestandteil dieser Korrektur. Insbesondere müssen die verwendeten Temperaturwerte weiterhin in °C vorliegen.

Offizielle Referenzen:

- [OptionsFlow](https://developers.home-assistant.io/blog/2024/11/12/options-flow/)
- [Thread-Sicherheit](https://contributors.home-assistant.io/core/internals/thread-safety/)
- [HA-Plattforminitialisierung, Core 2026.10.2](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/helpers/entity_platform.py)
- [HA-Speicherschnittstelle, Core 2026.10.2](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/helpers/storage.py)
