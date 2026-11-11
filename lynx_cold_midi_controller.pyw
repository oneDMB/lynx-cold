# =============================================================================
#  LYNX COLD ❄️ MIDI CONTROLLER
#  Version 1.1.0 nov. 2026
#  Autor: @oneDMB
#  🦊 https://github.com/oneDMB
#  🤠 https://github.com/deftivity
#  Entwickelt für Lynx Share
# =============================================================================

import colorsys
import ctypes
from ctypes import wintypes
import os
import sys
import threading
import time
import webbrowser

# --- PAKET-PRÜFUNG ---
missing = []
try:
    import mido
except ImportError:
    missing.append("mido python-rtmidi")
try:
    import pystray
except ImportError:
    missing.append("pystray")
try:
    from PIL import Image, ImageDraw
except ImportError:
    missing.append("Pillow")

if missing:
    print(f"Bitte installieren: pip install {' '.join(missing)}")
    sys.exit(1)

# =============================================================================
# EINSTELLUNGEN: PORT, HELLIGKEIT & TEMPO
# =============================================================================
virtual_port_name = "Lynx Cold MIDI Controller"
PAD_BRIGHTNESS = 64  
PAD_SATURATION = 101
DEFAULT_BPM = 120.0  

def hsv_scale_color(hex_col, brightness=PAD_BRIGHTNESS, saturation=PAD_SATURATION):
    r = ((hex_col >> 16) & 0xFF) / 255.0
    g = ((hex_col >> 8) & 0xFF) / 255.0
    b = (hex_col & 0xFF) / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = min(1.0, (s * 2.0) * (saturation / 128.0))
    v = v * (brightness / 128.0)
    if v > 0.0: v = max(v, 0.05)
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return (int(r2 * 255) >> 1, int(g2 * 255) >> 1, int(b2 * 255) >> 1)

# =============================================================================
# DIE ZWEI OFFIZIELLEN FARBSCHEMATA
# =============================================================================
COLOR_SETS = [
    # Schema 0: Standard ("Wie es war") -> Bernstein & Lime
    {
        "name": "Standard (Bernstein / Lime)",
        "black": hsv_scale_color(0xFF4000),  # Bernstein / Orange-Rot
        "white": hsv_scale_color(0xFFFFFF),  # Weiß
        "root":  hsv_scale_color(0x9CFF00),  # Lime / Gelb-Grün
    },
    # Schema 1: Alt-Colors ("Lynx Cold") -> Eisblau & Orange
    {
        "name": "Alt-Colors (Eisblau / Orange)",
        "black": hsv_scale_color(0x00FFFF),  # Cyan / Eisblau
        "white": hsv_scale_color(0xFFFFFF),  # Weiß
        "root":  hsv_scale_color(0xFF4000),  # Warmes Orange-Rot
    }
]

# Startet standardmäßig im eisblauen Lynx-Cold-Look
current_color_set = 1
COLOR_PLAY_USER = (100, 100, 100)

# =============================================================================
# WINDOWS KEYBOARD SIMULATION
# =============================================================================
user32 = ctypes.WinDLL('user32', use_last_error=True)
MY_EXTRA_INFO = 0x910910

def press_key(vk, scan=0, extended=False):
    flags_down = 1 if extended else 0
    flags_up = (1 if extended else 0) | 2
    user32.keybd_event(vk, scan, flags_down, MY_EXTRA_INFO)
    user32.keybd_event(vk, scan, flags_up, MY_EXTRA_INFO)

def press_ctrl_key(vk, scan=0):
    user32.keybd_event(0x11, 0x1D, 0, MY_EXTRA_INFO)
    user32.keybd_event(vk, scan, 0, MY_EXTRA_INFO)
    user32.keybd_event(vk, scan, 2, MY_EXTRA_INFO)
    user32.keybd_event(0x11, 0x1D, 2, MY_EXTRA_INFO)

def press_alt_f8_safe():
    def _run():
        user32.keybd_event(0x12, 0x38, 0, MY_EXTRA_INFO)
        time.sleep(0.02)
        user32.keybd_event(0x77, 0x42, 0, MY_EXTRA_INFO)
        time.sleep(0.02)
        user32.keybd_event(0x77, 0x42, 2, MY_EXTRA_INFO)
        time.sleep(0.02)
        user32.keybd_event(0x12, 0x38, 2, MY_EXTRA_INFO)
    threading.Thread(target=_run, daemon=True).start()

# =============================================================================
# 1. HARDWARE VERBINDUNG
# =============================================================================
in_ports = mido.get_input_names()
out_ports = mido.get_output_names()

fire_in_name = next((p for p in in_ports if "fire" in p.lower()), None)
fire_out_name = next((p for p in out_ports if "fire" in p.lower()), None)

if not fire_in_name or not fire_out_name:
    try:
        user32.MessageBoxW(0, "Hardware wurde nicht per USB gefunden!", "Lynx Cold", 0x10)
    except Exception:
        pass
    sys.exit(1)

try:
    fire_in = mido.open_input(fire_in_name)
    fire_out = mido.open_output(fire_out_name)
except Exception as e:
    user32.MessageBoxW(0, f"Fehler beim Öffnen des Controllers:\n{e}", "Lynx Cold", 0x10)
    sys.exit(1)

# =============================================================================
# 2. VIRTUELLER MIDI-PORT FÜR LYNX
# =============================================================================
vm_dll = None
vm_paths = [
    r"C:\Windows\System32\teVirtualMIDI64.dll",
    r"C:\Program Files\Tobias Erichsen\teVirtualMIDI\teVirtualMIDI64.dll",
    "teVirtualMIDI64.dll"
]
for p in vm_paths:
    if os.path.exists(p) or p == "teVirtualMIDI64.dll":
        try:
            vm_dll = ctypes.WinDLL(p, use_last_error=True)
            break
        except Exception:
            pass

if not vm_dll:
    user32.MessageBoxW(0, "teVirtualMIDI64.dll nicht gefunden! Bitte loopMIDI installieren.", "Lynx Cold", 0x10)
    sys.exit(1)

TE_VM_FLAGS_PARSE_RX = 1
TE_VM_FLAGS_INSTANTIATE_TX = 8
VM_CALLBACK = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), wintypes.DWORD, ctypes.c_size_t)
def dummy_cb(port_handle, data_ptr, length, instance): pass
vm_dummy_cb = VM_CALLBACK(dummy_cb)

vm_dll.virtualMIDICreatePortEx2.restype = ctypes.c_void_p
vm_dll.virtualMIDIClosePort.restype = None
vm_dll.virtualMIDISendData.restype = wintypes.BOOL
vm_dll.virtualMIDISendData.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), wintypes.DWORD]

lynx_midi_out = vm_dll.virtualMIDICreatePortEx2(
    virtual_port_name,
    vm_dummy_cb,
    0,
    65535,
    TE_VM_FLAGS_PARSE_RX | TE_VM_FLAGS_INSTANTIATE_TX
)

def send_to_lynx(msg):
    if not lynx_midi_out: return
    raw = msg.bytes()
    buf = (ctypes.c_ubyte * len(raw))(*raw)
    vm_dll.virtualMIDISendData(lynx_midi_out, buf, len(raw))

# =============================================================================
# 3. LED-STEUERUNG
# =============================================================================
def set_button_led(cc_id, val):
    try:
        fire_out.send(mido.Message("control_change", control=cc_id, value=val))
    except Exception:
        pass

def set_pad_leds(pad_color_list):
    length = len(pad_color_list) * 4
    len_msb = (length >> 7) & 0x7F
    len_lsb = length & 0x7F
    raw = [0xF0, 0x47, 0x7F, 0x43, 0x65, len_msb, len_lsb]
    for pad_idx, r, g, b in pad_color_list:
        raw.extend([pad_idx & 0x7F, r & 0x7F, g & 0x7F, b & 0x7F])
    raw.append(0xF7)
    try:
        fire_out.send(mido.Message.from_bytes(raw))
    except Exception:
        pass

WHITE_STEPS = [0, 2, 4, 5, 7, 9, 11, 12, 14, 16, 17, 19, 21, 23, 24, 26]
BLACK_STEPS = [-1, 1, 3, -1, 6, 8, 10, -1, 13, 15, -1, 18, 20, 22, -1, 25]
current_key_offset = 48

def get_pad_note_and_color(pad_idx, offset):
    row = pad_idx // 16
    col = pad_idx % 16
    c_set = COLOR_SETS[current_color_set]

    if row == 3:
        note = offset + WHITE_STEPS[col]
        return note, c_set["root"] if (col % 7 == 0) else c_set["white"]
    elif row == 2:
        semi = BLACK_STEPS[col]
        if semi == -1: return None, (0, 0, 0)
        return offset + semi, c_set["black"]
    elif row == 1:
        note = offset + 12 + WHITE_STEPS[col]
        return note, c_set["root"] if (col % 7 == 0) else c_set["white"]
    elif row == 0:
        semi = BLACK_STEPS[col]
        if semi == -1: return None, (0, 0, 0)
        return offset + 12 + semi, c_set["black"]

def refresh_all_pads():
    updates = []
    for pad in range(64):
        _, col = get_pad_note_and_color(pad, current_key_offset)
        updates.append((pad, col[0], col[1], col[2]))
    set_pad_leds(updates)

def toggle_color_scheme():
    global current_color_set
    current_color_set = 1 - current_color_set
    refresh_all_pads()

# =============================================================================
# 4. INITIALISIERUNG
# =============================================================================
is_playing = False
is_recording = False
is_song_mode = False
is_browser_open = False
is_folder_expanded = False
shift_held = False
alt_held = False
running = True

knob_values = {16: 64, 17: 64, 18: 64, 19: 64}

set_button_led(0x2D, 2)   # Note-Taste an
set_button_led(0x33, 2)   # Play: dunkel orange
set_button_led(0x34, 0)   # Stop: aus
set_button_led(0x35, 2)   # Record: dunkel orange
set_button_led(0x32, 4)   # Pattern: hell orange
set_button_led(0x1B, 20)  # User 1 LED
set_button_led(0x21, 0)
set_button_led(0x1F, 0)
set_button_led(0x20, 0)
set_button_led(0x22, 0)
set_button_led(0x23, 0)

refresh_all_pads()

# =============================================================================
# 5. TAKT-THREAD FÜR PLAY-BLINKEN
# =============================================================================
def beat_ticker_thread():
    beat_step = 0
    while running:
        if is_playing:
            beat_duration = 60.0 / DEFAULT_BPM
            current_flash = 4 if (beat_step % 4 == 0) else 3
            set_button_led(0x33, current_flash)
            time.sleep(0.12)
            if is_playing:
                set_button_led(0x33, 1)
            beat_step += 1
            time.sleep(max(0.01, beat_duration - 0.12))
        else:
            beat_step = 0
            time.sleep(0.05)

threading.Thread(target=beat_ticker_thread, daemon=True).start()

# =============================================================================
# 6. MIDI-THREAD
# =============================================================================
active_notes = {}

def midi_listener_loop():
    global current_key_offset, is_folder_expanded, is_browser_open
    global shift_held, alt_held, is_playing, is_recording, is_song_mode

    for msg in fire_in:
        if not running:
            break
        try:
            # PADS (54 bis 117)
            if msg.type in ("note_on", "note_off") and 54 <= msg.note <= 117:
                pad_idx = msg.note - 54
                note_val, default_color = get_pad_note_and_color(pad_idx, current_key_offset)
                if note_val is not None:
                    is_down = (msg.type == "note_on" and msg.velocity > 0)
                    if is_down:
                        send_to_lynx(mido.Message("note_on", note=note_val, velocity=msg.velocity))
                        active_notes[pad_idx] = note_val
                        set_pad_leds([(pad_idx, COLOR_PLAY_USER[0], COLOR_PLAY_USER[1], COLOR_PLAY_USER[2])])
                    else:
                        if pad_idx in active_notes:
                            send_to_lynx(mido.Message("note_off", note=active_notes[pad_idx], velocity=0))
                            del active_notes[pad_idx]
                        set_pad_leds([(pad_idx, default_color[0], default_color[1], default_color[2])])

            # NOTE-TASTE -> FARBSCHEMA UMSCHALTEN
            elif msg.note == 0x2D and msg.type == "note_on" and msg.velocity > 0:
                toggle_color_scheme()

            # ALT-TASTE
            elif msg.note == 0x31:
                alt_held = (msg.type == "note_on" and msg.velocity > 0)
                set_button_led(0x31, 2 if alt_held else 0)

            # 4 DREHREGLER (0-127)
            elif msg.type in ("note_on", "note_off") and 16 <= msg.note <= 19:
                pass
            elif msg.type == "control_change" and msg.control in (16, 17, 18, 19):
                delta = msg.value if msg.value < 64 else msg.value - 128
                new_val = max(0, min(127, knob_values[msg.control] + (delta * 2)))
                if new_val != knob_values[msg.control]:
                    knob_values[msg.control] = new_val
                    send_to_lynx(mido.Message("control_change", control=msg.control, value=new_val))

            # SELECT DREHREGLER -> BROWSER HOCH/RUNTER
            elif msg.type == "control_change" and msg.control == 118:
                is_folder_expanded = False
                if msg.value < 64:
                    press_key(0x28, 0x50, extended=True)
                else:
                    press_key(0x26, 0x48, extended=True)

            # SELECT DRÜCKEN -> ORDNER AUF/ZU
            elif msg.note == 25 and msg.type == "note_on" and msg.velocity > 0:
                if shift_held:
                    press_key(0x25, 0x4B, extended=True)
                    is_folder_expanded = False
                else:
                    if not is_folder_expanded:
                        press_key(0x27, 0x4D, extended=True)
                        is_folder_expanded = True
                    else:
                        press_key(0x25, 0x4B, extended=True)
                        is_folder_expanded = False

            # BROWSER TASTE -> ALT + F8
            elif msg.note == 33 and msg.type == "note_on" and msg.velocity > 0:
                press_alt_f8_safe()
                is_browser_open = not is_browser_open
                set_button_led(0x21, 2 if is_browser_open else 0)

            # PATTERN ▲ (Num +)
            elif msg.note == 0x1F:
                is_down = (msg.type == "note_on" and msg.velocity > 0)
                set_button_led(0x1F, 2 if is_down else 0)
                if is_down: press_key(0x6B, 0x4E)

            # PATTERN ▼ (Num - / Shift: F4)
            elif msg.note == 0x20:
                is_down = (msg.type == "note_on" and msg.velocity > 0)
                set_button_led(0x20, 2 if is_down else 0)
                if is_down:
                    if shift_held: press_key(0x73, 0x3E)
                    else: press_key(0x6D, 0x4A)

            # OKTAVEN: GRID ◄ / ►
            elif msg.note in (0x22, 0x23):
                is_down = (msg.type == "note_on" and msg.velocity > 0)
                set_button_led(msg.note, 2 if is_down else 0)
                if is_down:
                    if msg.note == 0x22: current_key_offset = max(12, current_key_offset - 12)
                    elif msg.note == 0x23: current_key_offset = min(96, current_key_offset + 12)
                    refresh_all_pads()

            # SHIFT
            elif msg.note == 0x30:
                shift_held = (msg.type == "note_on" and msg.velocity > 0)
                set_button_led(0x30, 2 if shift_held else 0)

            # PLAY
            elif msg.note == 0x33 and msg.type == "note_on" and msg.velocity > 0:
                if not shift_held:
                    if not is_playing:
                        press_key(0x20, 0x39)
                        is_playing = True
                        set_button_led(0x34, 2)
                    else:
                        press_key(0x20, 0x39)
                        is_playing = False
                        set_button_led(0x33, 2)
                        set_button_led(0x34, 0)

            # STOP
            elif msg.note == 0x34 and msg.type == "note_on" and msg.velocity > 0:
                if not shift_held:
                    if is_playing:
                        press_key(0x20, 0x39)
                        is_playing = False
                    set_button_led(0x33, 2)
                    set_button_led(0x34, 0)

            # RECORD
            elif msg.note == 0x35 and msg.type == "note_on" and msg.velocity > 0:
                if not shift_held:
                    press_key(0x52, 0x13)
                    is_recording = not is_recording
                    set_button_led(0x35, 3 if is_recording else 2)

            # PAT/SONG
            elif msg.note == 0x32 and msg.type == "note_on" and msg.velocity > 0:
                if shift_held:
                    press_ctrl_key(0x4D, 0x32)
                else:
                    press_key(0x4C, 0x26)
                    is_song_mode = not is_song_mode
                    set_button_led(0x32, 3 if is_song_mode else 4)

        except Exception:
            pass

threading.Thread(target=midi_listener_loop, daemon=True).start()

# =============================================================================
# 7. TASKLEISTEN-AGENT MIT ABOUT-FENSTER & LINKS
# =============================================================================
def create_tray_icon():
    img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((6, 6, 58, 58), fill=(0, 180, 255, 255), outline=(255, 255, 255, 255), width=2)
    d.line((32, 16, 32, 48), fill="white", width=4)
    d.line((16, 32, 48, 32), fill="white", width=4)
    d.line((20, 20, 44, 44), fill="white", width=3)
    d.line((20, 44, 44, 20), fill="white", width=3)
    return img

def quit_agent(icon, item):
    global running
    running = False
    icon.stop()

def toggle_color_from_tray(icon, item):
    toggle_color_scheme()

def show_about_dialog(icon, item):
    def _msg():
        about_msg = (
            "LYNX COLD ❄️ MIDI CONTROLLER\n"
            "Version 1.1.0 nov. 2026\n\n"
            "Autor: @oneDMB\n\n"
            "🦊 https://github.com/oneDMB\n"
            "🤠 https://github.com/deftivity\n\n"
            "Entwickelt für Lynx Share"
        )
        user32.MessageBoxW(0, about_msg, "Über LYNX COLD ❄️", 0x40)
    threading.Thread(target=_msg, daemon=True).start()

tray = pystray.Icon(
    "LynxCold",
    create_tray_icon(),
    "Lynx Cold MIDI Controller",
    menu=pystray.Menu(
        pystray.MenuItem("Lynx Cold ❄️ v1.1.0", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Farbschema wechseln (Note)", toggle_color_from_tray),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Über / About ℹ️", show_about_dialog),
        pystray.MenuItem("🦊 GitHub @oneDMB", lambda icon, item: webbrowser.open("https://github.com/oneDMB")),
        pystray.MenuItem("🤠 GitHub @deftivity", lambda icon, item: webbrowser.open("https://github.com/deftivity")),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Beenden", quit_agent)
    )
)

tray.run()

# =============================================================================
# CLEANUP BEIM BEENDEN
# =============================================================================
running = False
set_pad_leds([(p, 0, 0, 0) for p in range(64)])
for b in (0x2D, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x1B, 0x21, 0x1F, 0x20, 0x22, 0x23):
    set_button_led(b, 0)

try:
    if lynx_midi_out:
        vm_dll.virtualMIDIClosePort(lynx_midi_out)
    fire_in.close()
    fire_out.close()
except Exception:
    pass

sys.exit(0)