# LYNX COLD ❄️ — Standalone MIDI Controller for LYNX SHARE

![Version](https://img.shields.io/badge/Version-1.6.6--nov.--2026-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen?style=for-the-badge)
![DAW](https://img.shields.io/badge/DAW-LYNX%20SHARE-orange?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

> **The icy, Nordic counterpart to the original FL Studio Fire — built from the ground up as a native, high-precision standalone controller for the LYNX SHARE DAW.**

---

## ❄️ 1. The Idea (What and Why?)

The Akai Fire controller is a brilliant piece of studio hardware, but it has historically been tightly bound to FL Studio. When plugged into an alternative DAW like **LYNX SHARE**, the hardware typically stays dark and silent.

**LYNX COLD** sets the controller free:  
It acts as an independent, latency-free Windows background agent (with single-instance protection and 1ms Windows precision timing) that drives the hardware via USB, turns the 64 RGB pads into an interactive piano keyboard, a live-synced 999×160 step sequencer, or a customizable RGB FPC drum machine, smooths out all rotary knobs, and syncs directly to the DAW's MIDI clock.

* **Author:** [@oneDMB](https://github.com/oneDMB) 🦊 (C) 2026
* **Partner / Co-Dev:** [@deftivity](https://github.com/deftivity) 🤠
* **Developed for:** [LYNX SHARE DAW](https://github.com/lynx-share)

---

## ✨ 2. Current Status (Features in Version 1.6.6)

### 🥁 1. Step Sequencer Mode (`STEP` Button)
* **Massive 999 × 160 Grid:** Supports up to **999 channels** vertically and **10 bars (160 steps)** horizontally, configurable via the **Edit Grid (Raster)** GUI.
* **Bidirectional Channel Rack Sync:** Reads active steps and channel mute states in real time from the *Lynx Share - Channel Rack* window (DPI-aware with selectable UI scaling from `80%` to `250%`) and toggles them directly via pad presses.
* **Channel Mute & Solo:** The 4 row buttons on the left mirror the green mute LEDs of the visible channels. Press to **Mute/Unmute**, or hold **`SHIFT` + Row Button** to **Solo**.
* **Grid Navigation:**
  * **Select Wheel:** Scrolls horizontally through steps (`SHIFT + Wheel` jumps 16 steps / 1 bar).
  * **`ALT` + Select Wheel** (or **`ALT` + `PATTERN ▲ / ▼`**): Scrolls vertically through channels (`+ SHIFT` jumps 4 channels).
  * **Press Select Button:** Resets step offset to 0 (or channel offset to 0 when holding `ALT`).
* **Color Schemes:** Press **`STEP`** again while in Step mode to toggle between ice-blue and lime-green beat group highlights.

### 🎹 2. Dual-Keyboard Note Mode (`NOTE` Button)
* **64 Velocity-Sensitive RGB Pads:** Split into two overlapping octaves (lower and upper octave like two manuals).
* **Live Color Scheme Switching:**
  * **Alt-Colors (Lynx Cold Look — Default):** Semitones in ice blue/cyan (`#00FFFF`), root notes (C) in orange-red (`#FF4000`), whole tones in white.
  * **Standard-Look:** Semitones in amber (`#FF4000`), root notes (C) in lime green (`#9CFF00`).
  * *Switching:* Simply press the **`NOTE`** button again on the controller or click via the tray menu.
* **No Stuck Notes:** Intelligent note tracking prevents hanging notes during mode or octave shifts while playing.
* **Octave Switches:** **`GRID ◄`** and **`GRID ►`** transpose the keyboard by `±12` semitones (`C1` to `C8`) and light up red when pressed.

### 🥁 3. Custom RGB Drum Mode (`DRUM` Button)
* **32-Pad FPC Bank A & B Layout:** Maps Bank A (16 pads) and Bank B (16 pads) side-by-side onto the 64-pad matrix.
* **3 Switchable Positions:** Press **`DRUM`** repeatedly to shift the active 8×4 drum zone between **Left** (cols 0–7), **Center** (cols 4–11), and **Right** (cols 8–15).
* **Interactive RGB Pad Editor:** Customize every single pad color in Bank A and Bank B using the built-in **Edit Drum Pads (RGB)** window, featuring a 16-color Cold Palette, 4 persistent custom color slots, full RGB color picker, and direct `#HEX` input (saved automatically to `lynx_cold_drum_colors.json`). Right-click Bank `A` or `B` in the editor to reset to default gradients.

### ⏱️ 4. Bidirectional MIDI Clock Sync & Precision Tempo
* **External DAW Clock Sync:** Receives MIDI Clock (`0xF8`), Start (`0xFA`), Continue (`0xFB`), Stop (`0xFC`), and Song Position Pointer (`0xF2`) directly from LYNX SHARE for rock-solid playhead and beat-LED synchronization.
* **Drift-Free Internal Fallback:** Uses Windows `winmm` 1ms timer resolution when running standalone without external clock.
* **Edit Tempo (BPM) GUI:** Rotary knob dialog (`10.0` – `522.0 BPM`) with mouse drag, scroll wheel (`+ Shift` for `±10 BPM`), and live MIDI Sync status indicator.

### 🎛️ 5. Studio Knobs & Intelligent Browser Navigation
* **Stepless Knobs (CC 16–19):** Relative rotary ticks are smoothed into an analog `0–127` curve with capacitive touch-sensor filtering for clean *MIDI Learn*.
* **Browser Navigation (`BROWSER` Button & Select Wheel):**
  * **`BROWSER`:** Toggles the browser sidebar (`Alt + F8`).
  * **Select Wheel (when Browser open):** Scrolls up/down; clicking expands (`Right Arrow`) or collapses (`Left Arrow`) folders (`SHIFT + Click` forces collapse).

### ⏯️ 6. Full-Featured Transport Section
* **`PLAY`:** Dark orange in standby; flashes in 4/4 time during playback (**beat 1 bright orange, beats 2–4 bright green**).
* **`STOP`:** Stops playback (`Space`) and resets transport LEDs.
* **`RECORD`:** Toggles recording (`R`) and switches to **pure red** when active.
* **`PAT/SONG`:** Toggles Pattern/Song mode (`L`). With **`SHIFT`** = Metronome on/off (`Ctrl + M`).
* **`PATTERN ▲ / ▼`:** Steps through patterns (`NumPad +` / `-`). With **`SHIFT + ▼`** = New empty pattern (`F4`).

### ❄️ 7. Background Agent & Tray Menu
* Runs silently as a **`.pyw`** without a console window, protected by a Windows mutex against accidental double launches.
* Right-click the **❄️ tray icon** to access:
  * **Edit Tempo (BPM)...**
  * **Edit Grid (Raster)...**
  * **Edit Drum Pads (RGB)...**
  * **Farbschema / Layout wechseln**
  * **LYNX SHARE Skalierung** (`80%` – `250%` DPI/UI scaling)
  * **Über / About ℹ️** & direct GitHub links

---

## 🚀 3. Easy Installation

### Prerequisites
1. **Windows 10 or 11 (64-bit)**
2. **Python 3.8+** (Make sure *"Add Python to PATH"* and *tcl/tk* are enabled during installation)
3. The virtual MIDI driver **loopMIDI** (or the `teVirtualMIDI` SDK) must be installed so `teVirtualMIDI64.dll` is available on your system. *(loopMIDI does not need to stay open; only the driver is required).*

### Step 1: Install Required Libraries
Open the Windows Command Prompt (`cmd`) and install the dependencies:

```bash
pip install mido python-rtmidi pystray Pillow
```

### Step 2: Start the Script
1. Download `lynx_cold_midi_controller.pyw`.
2. Start it with a double click.
3. *(The ❄️ icon appears in the Windows system tray next to the clock, and the controller lights up).*

> **💡 Tip (Autostart):** Press `Win + R`, type `shell:startup`, and place a shortcut to the `.pyw` file inside. LYNX COLD will then launch automatically in the background whenever Windows starts!

### Step 3: Configure in LYNX SHARE
1. Launch **LYNX SHARE** and open the MIDI settings.
2. Enable **`👉 Lynx Cold MIDI Controller`** as a **MIDI Input** (for notes, knobs, and drum pads).
3. *(Optional, recommended)* Enable **`👉 Lynx Cold MIDI Controller`** as a **MIDI Output / Clock Sync** target so LYNX COLD locks automatically to your DAW's tempo and playhead.
4. If you use Windows display scaling other than 100%, select your matching percentage under **Tray Icon → LYNX SHARE Skalierung** for accurate Channel Rack step syncing.

---

## 🗺️ 4. Roadmap & Outlook (Developers Wanted!)

Most core features from the initial roadmap (`Drum Mode`, `Step Sequencer Mode`, `Bidirectional MIDI Clock Sync`, and `GUI Editors`) are now implemented and stable! Upcoming ideas for future releases:

* **v1.7.0+:** Quick-preset templates for Drum Pad color banks & Channel Rack auto-scale detection.
* **v2.0.0:** OLED Display Emulation (displaying active mode, BPM, channel names, and parameters via SysEx).
* **Future:** Performance Mode (clip launching from the playlist).

---

## 🤝 Contributing

Do you program in Python, C++, or contribute to LYNX SHARE? Pull requests and feedback are very welcome!  
Fork the repository, create a branch, and help shape the future of LYNX COLD with us!

---

## 📦 5. License & Disclaimer

* **Authors:** [@oneDMB](https://github.com/oneDMB) 🦊 & [@deftivity](https://github.com/deftivity) 🤠
* **License:** Licensed under the [MIT License](LICENSE).

### Disclaimer
*This project is an independent open-source tool developed for Lynx Share and is not affiliated with, sponsored by, or endorsed by inMusic Brands, Inc. or Akai Professional. "AKAI" and "Fire" are registered trademarks of their respective owners.*
