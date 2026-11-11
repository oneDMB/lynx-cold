# LYNX COLD ❄️ — Standalone MIDI Controller for LYNX SHARE

![Version](https://img.shields.io/badge/Version-1.1.0--nov.--2026-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen?style=for-the-badge)
![DAW](https://img.shields.io/badge/DAW-LYNX%20SHARE-orange?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

> **The icy, Nordic counterpart to the original FL Studio Fire — built from the ground up as a native, high-precision standalone controller for the LYNX SHARE DAW.**

---

## ❄️ 1. The Idea (What and Why?)

The Akai Fire controller is a brilliant piece of studio hardware, but it has historically been tightly bound to FL Studio. When plugged into an alternative DAW like **LYNX SHARE**, the hardware typically stays dark and silent.

**LYNX COLD** sets the controller free:  
It acts as an independent, latency-free Windows background agent that drives the hardware via USB, turns the 64 RGB pads into an interactive piano keyboard, smooths out all rotary knobs, and makes the entire transport and browser navigation usable for **LYNX SHARE**.

* **Author:** [@oneDMB](https://github.com/oneDMB) 🦊 (C) 2026
* **Partner / Co-Dev:** [@deftivity](https://github.com/deftivity) 🤠
* **Developed for:** [LYNX SHARE DAW](https://github.com/lynx-share)

---

## ✨ 2. Current Status (Features in Version 1.1.0)

Everything in version 1.1.0 runs stably out of the box:

### 🎹 Dual-Keyboard Note Mode
* **64 Velocity-Sensitive RGB Pads:** Split into two overlapping octaves (lower and upper octave like two manuals).
* **Live Color Scheme Switching:**
  * **Alt-Colors (Lynx Cold Look — Default):** Semitones in ice blue/cyan (`#00FFFF`), root notes (C) in orange-red (`#FF4000`), whole tones in white.
  * **Standard-Look:** Semitones in amber (`#FF4000`), root notes (C) in lime green (`#9CFF00`).
  * *Switching:* Simply press the **`NOTE`** button on the controller or click via the tray menu!
* **No Stuck Notes:** Intelligent note tracking prevents hanging notes during octave shifts while playing.
* **Octave Switches:** **`GRID ◄`** and **`GRID ►`** transpose the keyboard by `±12` semitones and light up red when pressed.

### 🎛️ Real Studio Knobs (Stepless 0–127)
* **No Sudden Jumps:** Relative rotary ticks are internally converted into a clean, analog potentiometer curve from `0` to `127`.
* **Touch Sensor Filter:** The capacitive touch sensors of the knobs are filtered so that LYNX SHARE does not accidentally learn the touch trigger during *MIDI Learn*.
  * **Knob 1:** MIDI CC 16
  * **Knob 2:** MIDI CC 17
  * **Knob 3:** MIDI CC 18
  * **Knob 4:** MIDI CC 19

### 📂 Intelligent Browser Navigation (Select Wheel)
* **Rotate (Right / Left):** Scrolls down or up in the LYNX browser.
* **Press Select Button:**
  * **1st Click:** Expands the selected folder (`Right Arrow`).
  * **2nd Click:** Collapses the folder again (`Left Arrow`).
  * **With Shift:** Forces the folder to close.
* **BROWSER Button:** Opens and closes the browser sidebar (`Alt + F8` with debounce protection).

### ⏯️ Full-Featured Transport Section
* **`PLAY`:** Dark orange in standby. Flashes during playback in a 4/4 beat (**1st beat bright orange, beats 2–4 bright green**).
* **`STOP`:** Off in standby, dark orange during play. Stops the DAW reliably via Spacebar and resets all LEDs.
* **`RECORD`:** Dark orange in standby, switches to **pure red** when recording.
* **`PAT/SONG`:** **Bright orange** in Pattern mode, **bright green** in Song mode (`Key L`). With `SHIFT` = Metronome on/off (`Ctrl + M`).
* **`PATTERN ▲ / ▼`:** Steps through patterns (`NumPad +` / `-`). With `SHIFT + ▼` = New empty pattern (`F4`).

### ❄️ Background Agent with Tray Icon
* Runs as a **`.pyw` completely without a black console window**.
* Dedicated ice-blue **❄️ icon** in the Windows taskbar next to the clock.
* Right-click menu with **About dialog**, **Color scheme switcher**, **Direct GitHub links**, and **Exit command**.

---

## 🚀 3. Easy Installation

### Prerequisites
1. **Windows 10 or 11 (64-bit)**
2. **Python 3.8+** (Make sure to check *"Add Python to PATH"* during installation)
3. The virtual MIDI driver **loopMIDI** (or the teVirtualMIDI SDK) must be installed on your PC. *(loopMIDI does not need to be actively running; only the driver is required).*

### Step 1: Install Required Libraries
Open the Windows Command Prompt (`cmd`) and install the dependencies with the following command:

```bash
pip install mido python-rtmidi pystray Pillow
```

### Step 2: Start the Script
1. Download the `lynx_cold_midi_controller.pyw` file.
2. Simply start it with a double click.
3. *(No distracting window will open — the ❄️ icon appears directly next to the Windows clock, and the controller lights up).*

> **💡 Tip (Autostart):** Press `Win + R`, type `shell:startup`, and place a shortcut of the `.pyw` file inside. LYNX COLD will then automatically launch in the background every time your PC starts!

### Step 3: Enable in LYNX SHARE
1. Launch LYNX SHARE.
2. Open the MIDI settings.
3. Enable the following entry under MIDI inputs: **`👉 Lynx Cold MIDI Controller`**.
4. Done! You can start playing right away.

---

## 🗺️ 4. Roadmap & Outlook (Developers Wanted!)

Version 1.1.0 serves as a solid foundation as a controller & keyboard. The following milestones are planned for future releases:

* **v1.2.0:** Drum Mode (16-pad FPC layout for drum samplers & Slicex with Bank A/B).
* **v1.3.0:** Step Sequencer Mode (running light feedback of channel rack steps via the pads).
* **v2.0.0:** OLED Display Emulation (displaying preset names, track labels, and VU meters via SysEx).
* **Future:** Performance Mode (clip launching from the playlist).

---

## 🤝 Contributing

Do you program in Python, C++, or contribute to LYNX SHARE? Pull requests and feedback are very welcome!  
Fork the repository, create a branch, and help shape the future of LYNX COLD with us!

---

## 📦 5. License & Disclaimer

* **Authors:** [@oneDMB](https://github.com/oneDMB) 🦊 [@deftivity](https://github.com/deftivity) 🤠
* **License:** Licensed under the [MIT License](LICENSE).

### Disclaimer
*This project is an independent open-source tool developed for Lynx Share and is not affiliated with, sponsored by, or endorsed by inMusic Brands, Inc. or Akai Professional. "AKAI" and "Fire" are registered trademarks of their respective owners.*
