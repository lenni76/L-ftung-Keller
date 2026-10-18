# Kellerlüftung 1.0.1 in HA OS einspielen

Version 1.0.1 enthält die vollständigen Integrationsdateien und basiert auf dem Repository-Commit `d4babce6bedf13a54ca895b00607c496eb9b4219`. Diese Anleitung beschreibt das manuelle Einspielen auf Home Assistant OS.

## Vorbereitung über die HA-Oberfläche

1. Erstelle über **Einstellungen → System → Backups** eine aktuelle Sicherung. Sichere außerdem den bisherigen Ordner `custom_components/kellerlueftung` außerhalb von `custom_components`, damit du bei Bedarf zurückwechseln kannst.
2. Öffne **Einstellungen → Geräte & Dienste → Entitäten**, filtere nach der Integration **Kellerlüftung** und öffne die Entität **Betriebsart**. Sie muss für die erstmalige Übernahme des bisherigen Zustands aktiviert sein.
3. Notiere die bisherige Betriebsart und wähle für das Einspielen **Aus**. Kontrolliere am tatsächlichen Lüfterzustand, dass der Lüfter ausgeschaltet ist. Nach dem Update wählst du deine gewünschte Betriebsart wieder aus.

## Vollständigen Integrationsordner ersetzen

1. Entpacke `Kellerlueftung-1.0.1.zip` auf deinem Mac.
2. Öffne deinen vorhandenen Dateizugriff auf HA. Wenn du Samba bereits eingerichtet hast, verbinde im Finder über **Gehe zu → Mit Server verbinden** mit `smb://DEIN-HA-HOSTNAME-ODER-IP` und öffne die Freigabe `config`.
3. Ersetze den vollständigen Ordner `custom_components/kellerlueftung` durch den gleichnamigen Ordner aus dem ZIP. Keine zweite Kopie der Integration unter `custom_components` liegen lassen. In der HA-Laufzeit lautet der Zielpfad `/config/custom_components/kellerlueftung`.
4. Starte **Home Assistant Core** über die Neustartfunktion der HA-Oberfläche neu. Ein Neuladen der Integration allein ersetzt die bereits importierten Python-Dateien nicht zuverlässig. Proxmox und die VM müssen dafür nicht neu gestartet werden.

Die offizielle HA-OS-Dokumentation beschreibt [Dateizugriff einschließlich Samba und Backups](https://www.home-assistant.io/common-tasks/os/). Diese Anleitung setzt keinen bereits vorhandenen Samba-Zugang voraus: Falls du einen anderen Dateizugriff eingerichtet hast, verwende diesen für den vollständigen Ordnerwechsel.

## Nach dem Neustart kontrollieren

1. Öffne die Geräteansicht der Integration **Kellerlüftung** unter **Einstellungen → Geräte & Dienste**. Die Integration meldet jetzt Version **1.0.1** als Softwareversion ihres Geräts.
2. Prüfe zunächst, dass die Betriebsart **Aus** erhalten blieb und der Lüfter aus ist.
3. Öffne **Konfigurieren** an der Integration. Der Dialog für die Regelparameter sollte ohne Fehler öffnen. Zunächst kannst du ihn ohne Änderungen schließen.
4. Wähle deine gewünschte Betriebsart. Bei gültigen Messwerten sollten **Sensoren in Ordnung**, **Status** und **Entscheidung** nachvollziehbare Zustände anzeigen. Die Temperatursensoren müssen weiterhin Werte in **°C** liefern.
5. Prüfe unter **Einstellungen → System → Protokolle**, ob Fehler zur Integration `kellerlueftung` gemeldet werden.

Zeigt die Integration nach dem ersten Update „Betriebsart nicht verfügbar“, aktiviere die Betriebsart-Entität und lade die Integration neu. Ohne übernehmbaren gespeicherten Zustand ist die bisherige Standardbetriebsart **Automatik**; prüfe daher anschließend die gewünschte Auswahl.

## Validierungsstand

Die Korrektur hat 23 Regressionstests mit nachgebildeten HA-Schnittstellen sowie Syntax- und JSON-Prüfungen bestanden. Zusätzlich wurde Version 1.0.1 in einer bestehenden HA-Core-2026.10.2-Installation eingespielt: Core-Neustart, Erkennung der Integration und Öffnen des Einrichtungsdialogs wurden erfolgreich geprüft. Die Steuerung mit zugeordneten realen Sensoren und einem Lüfter, Hassfest und HACS-Validation wurden nicht geprüft. Die vier mittel priorisierten Befunde aus der vorangegangenen Prüfung bleiben offen.

## Zurückwechseln

Ersetze den Integrationsordner durch deine gesicherte vorherige Kopie und starte Home Assistant Core neu. Kontrolliere danach Betriebsart und tatsächlichen Lüfterzustand. Eine Wiederherstellung der gesamten HA-Sicherung ist nur nötig, falls der reine Dateirückwechsel nicht ausreicht.
