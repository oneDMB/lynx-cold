# LYNX COLD ❄️ — Standalone MIDI Controller für LYNX SHARE

![Version](https://img.shields.io/badge/Version-1.1.0--nov.--2026-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen?style=for-the-badge)
![DAW](https://img.shields.io/badge/DAW-LYNX%20SHARE-orange?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

> **Das eiskalte, nordische Gegenstück zum originalen FL Studio Fire — von Grund auf als nativer, hochpräziser Standalone-Controller für die LYNX SHARE DAW entwickelt.**

---

## ❄️ 1. Die Idee (Was und Warum?)

Der Akai Fire Controller ist ein geniales Stück Studio-Hardware, war bisher jedoch fest an FL Studio gekoppelt. Wird er an einer alternativen DAW wie **LYNX SHARE** angeschlossen, bleibt die Hardware meist dunkel und stumm.

**LYNX COLD** befreit den Controller:  
Es fungiert als eigenständiger, latenzfreier Windows-Hintergrund-Agent, der die Hardware per USB ansteuert, die 64 RGB-Pads in ein interaktives Piano-Keyboard verwandelt, alle Drehregler glättet und die gesamte Transport- und Browser-Navigation für **LYNX SHARE** nutzbar macht.

* **Autor:** [@oneDMB](https://github.com/oneDMB) 🦊 (C) 2026
* **Partner / Co-Dev:** [@deftivity](https://github.com/deftivity) 🤠
* **Entwickelt für:** [LYNX SHARE DAW](https://github.com/lynx-share)

---

## ✨ 2. Der aktuelle Status (Features in Version 1.1.0)

Alles in Version 1.1.0 läuft out-of-the-box stabil:

### 🎹 Dual-Keyboard Note-Modus
* **64 anschlagdynamische RGB-Pads:** Aufgeteilt in zwei übereinanderliegende Oktaven (untere und obere Oktave wie zwei Manuale).
* **Live-Farbschema-Umschaltung:**
  * **Alt-Colors (Lynx Cold Look — Standard):** Halbtöne in Eisblau/Cyan (`#00FFFF`), Grundtöne (C) in Orange-Rot (`#FF4000`), Ganztöne in Weiß.
  * **Standard-Look:** Halbtöne in Bernstein (`#FF4000`), Grundtöne (C) in Lime-Grün (`#9CFF00`).
  * *Umschalten:* Einfach die Taste **`NOTE`** am Controller drücken oder per Klick im Taskleisten-Menü!
* **No Stuck Notes:** Intelligentes Noten-Tracking verhindert hängende Töne bei Oktavsprüngen während des Spielens.
* **Oktav-Schalter:** **`GRID ◄`** und **`GRID ►`** transponieren die Tastatur um `±12` Halbtöne und leuchten beim Drücken rot auf.

### 🎛️ Echte Studio-Drehregler (Stufenlos 0–127)
* **Kein An/Aus-Springen:** Relative Drehticks werden intern in eine saubere, analoge Potentiometer-Kurve von `0` bis `127` umgewandelt.
* **Touch-Sensor-Filter:** Die kapazitiven Berührungssensoren der Knöpfe werden gefiltert, sodass LYNX SHARE bei *MIDI Learn* nicht versehentlich den Touch-Trigger lernt.
  * **Regler 1:** MIDI CC 16
  * **Regler 2:** MIDI CC 17
  * **Regler 3:** MIDI CC 18
  * **Regler 4:** MIDI CC 19

### 📂 Intelligente Browser-Steuerung (Select-Rad)
* **Drehen (Rechts / Links):** Scrollt im LYNX-Browser nach unten bzw. oben.
* **Select-Knopf drücken:**
  * **1. Klick:** Klappt den gewählten Ordner auf (`Pfeiltaste Rechts`).
  * **2. Klick:** Klappt den Ordner wieder zu (`Pfeiltaste Links`).
  * **Mit Shift:** Erzwingt das Schließen des Ordners.
* **BROWSER-Taste:** Öffnet und schließt die Browserleiste (`Alt + F8` mit Entprellungsschutz).

### ⏯️ Vollwertige Transport-Sektion
* **`PLAY`:** Dunkelorange im Standby. Blinkt bei Wiedergabe im 4/4-Takt (**1. Schlag Hellorange, Schläge 2–4 Hellgrün**).
* **`STOP`:** Aus im Standby, dunkelorange bei Play. Stoppt die DAW zuverlässig per Leertaste und setzt alle LEDs zurück.
* **`RECORD`:** Dunkelorange im Standby, schaltet bei Aufnahme auf **reines Rot**.
* **`PAT/SONG`:** **Hellorange** im Pattern-Modus, **Hellgrün** im Song-Modus (`Taste L`). Mit `SHIFT` = Metronom an/aus (`Strg + M`).
* **`PATTERN ▲ / ▼`:** Schaltet durch die Patterns (`NumPad +` / `-`). Mit `SHIFT + ▼` = Neues leeres Pattern (`F4`).

### ❄️ Hintergrund-Agent mit Tray-Icon
* Läuft als **`.pyw` komplett ohne schwarzes Konsolenfenster**.
* Eigenes eisblaues **❄️-Symbol** in der Windows-Taskleiste neben der Uhr.
* Rechtsklick-Menü mit **About-Dialog**, **Farbschema-Umschalter**, **GitHub-Direktlinks** und **Beenden-Befehl**.

---

## 🚀 3. Einfache Installation

### Voraussetzungen
1. **Windows 10 oder 11 (64-Bit)**
2. **Python 3.8+** (Bei der Installation den Haken bei *„Add Python to PATH“* setzen)
3. Der virtuelle MIDI-Treiber **loopMIDI** (oder das teVirtualMIDI SDK) muss auf dem PC installiert sein. *(Das Programm loopMIDI muss nicht zwingend aktiv laufen, nur der Treiber wird benötigt).*

### Schritt 1: Benötigte Bibliotheken installieren
Öffne die Windows-Eingabeaufforderung (`cmd`) und installiere die Abhängigkeiten mit folgendem Befehl:

```bash
pip install mido python-rtmidi pystray Pillow
```

### Schritt 2: Skript starten
1. Lade die Datei `lynx_cold_midi_controller.pyw` herunter.
2. Starte sie einfach per Doppelklick.
3. *(Es öffnet sich kein störendes Fenster – das ❄️-Icon erscheint direkt neben der Windows-Uhr und der Controller leuchtet auf).*

> **💡 Tipp (Autostart):** Drücke `Win + R`, tippe `shell:startup` ein und lege eine Verknüpfung der `.pyw`-Datei hinein. LYNX COLD startet dann bei jedem PC-Start automatisch im Hintergrund!

### Schritt 3: In LYNX SHARE aktivieren
1. Starte LYNX SHARE.
2. Öffne die MIDI-Einstellungen.
3. Aktiviere unter den MIDI-Eingängen den Eintrag: **`👉 Lynx Cold MIDI Controller`**.
4. Fertig! Du kannst sofort losspielen.

---

## 🗺️ 4. Roadmap & Ausblick (Entwickler gesucht!)

Version 1.1.0 ist das solide Fundament als Controller & Keyboard. Für zukünftige Releases sind folgende Meilensteine geplant:

* **v1.2.0:** Drum-Modus (16-Pad FPC-Layout für Drum-Sampler & Slicex mit Bank A/B).
* **v1.3.0:** Step-Sequenzer-Modus (Lauflicht-Feedback der Channel-Rack-Steps über die Pads).
* **v2.0.0:** OLED-Display Emulation (Darstellung von Preset-Namen, Track-Labels und VU-Metern über SysEx).
* **Future:** Performance-Modus (Clip-Launching aus der Playlist).

---

## 🤝 Mitwirken / Contributing

Du programmierst in Python, C++ oder entwickelst an LYNX SHARE mit? Pull Requests und Feedback sind herzlich willkommen!  
Forke das Repository, erstelle einen Branch und gestalte LYNX COLD mit uns weiter!

---

## 📦 5. Lizenz & Disclaimer

* **Autoren:** [@oneDMB](https://github.com/oneDMB) 🦊 & [@deftivity](https://github.com/deftivity) 🤠
* **Lizenz:** Lizenziert unter der [MIT License](LICENSE).

### Disclaimer
*This project is an independent open-source tool developed for Lynx Share and is not affiliated with, sponsored by, or endorsed by inMusic Brands, Inc. or Akai Professional. "AKAI" and "Fire" are registered trademarks of their respective owners.*
