# =============================================================================
#  LYNX COLD ❄️ MIDI CONTROLLER
#  Version 1.6.6 nov. 2026
#  Autor: @oneDMB
#  🦊 https://github.com/oneDMB
#  🤠 https://github.com/deftivity
#  Entwickelt für Lynx Share
# =============================================================================

import colorsys
import ctypes
from ctypes import wintypes
import json
import math
import os
import sys
import threading
import time
import webbrowser

# =============================================================================
# DOPPELSTART-SPERRE (SINGLE INSTANCE MUTEX)
# =============================================================================
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

mutex_handle = kernel32.CreateMutexW(None, False, "LynxColdMidiController_SingleInstance_Mutex")
if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
    try:
        ctypes.WinDLL('user32').MessageBoxW(
            0,
            "LYNX COLD ❄️ läuft bereits!\n\nDu findest das ❄️-Symbol unten rechts in der Windows-Taskleiste neben der Uhr.",
            "Lynx Cold - Bereits aktiv",
            0x40
        )
    except Exception:
        pass
    sys.exit(0)

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
    from PIL import Image, ImageDraw, ImageGrab
except ImportError:
    missing.append("Pillow")

if missing:
    print(f"Bitte installieren: pip install {' '.join(missing)}")
    sys.exit(1)

try:
    import tkinter as tk
    from tkinter import colorchooser
    HAS_TK = True
except ImportError:
    HAS_TK = False

# =============================================================================
# WINDOWS 1ms PRÄZISIONS-TIMER AKTIVIEREN (GEGEN TEMPO-DRIFT)
# =============================================================================
try:
    winmm = ctypes.WinDLL('winmm')
    winmm.timeBeginPeriod(1)
except Exception:
    winmm = None

# =============================================================================
# EINSTELLUNGEN: PORT, HELLIGKEIT, TEMPO, RASTER, DRUM-FARBEN & SKALIERUNG
# =============================================================================
virtual_port_name = "Lynx Cold MIDI Controller"
PAD_BRIGHTNESS = 64  
PAD_SATURATION = 101
DEFAULT_BPM = 120.0  

lynx_scale = 1.0

MAX_ALLOC_BARS = 10
MAX_ALLOC_CHANNELS = 999
MIN_DOWN_CHANNELS = 4

grid_right_bars = 1
grid_down_limit = 5

def hsv_scale_color(hex_col, brightness=PAD_BRIGHTNESS, saturation=PAD_SATURATION):
    if hex_col == 0:
        return (0, 0, 0)
    r = ((hex_col >> 16) & 0xFF) / 255.0
    g = ((hex_col >> 8) & 0xFF) / 255.0
    b = (hex_col & 0xFF) / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = min(1.0, (s * 2.0) * (saturation / 128.0))
    v = v * (brightness / 128.0)
    if v > 0.0: v = max(v, 0.05)
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return (int(r2 * 255) >> 1, int(g2 * 255) >> 1, int(b2 * 255) >> 1)

COLOR_SETS = [
    {
        "name": "Standard (Bernstein / Lime)",
        "black": hsv_scale_color(0xFF4000),
        "white": hsv_scale_color(0xFFFFFF),
        "root":  hsv_scale_color(0x9CFF00),
    },
    {
        "name": "Alt-Colors (Eisblau / Orange)",
        "black": hsv_scale_color(0x00FFFF),
        "white": hsv_scale_color(0xFFFFFF),
        "root":  hsv_scale_color(0xFF4000),
    }
]

# Bank A Default: Gradient von Pad 1 (Eisblau 0x00FFFF) zu Pad 16 (Licht aus 0x000000)
DEFAULT_BANK_A_COLORS = [
    ((int(round(255 * (15 - i) / 15.0)) << 8) | int(round(255 * (15 - i) / 15.0)))
    for i in range(16)
]

# Bank B Default: Pads 1..8 Step-Weiß (0x666666), Verlauf zu Pad 13..16 (Licht aus)
def _make_bank_b_defaults():
    cols = []
    for i in range(16):
        if i <= 7:          # Pads 1..8 -> Voll an (Weiß)
            v = 102
        else:               # Pads 9..16 (inkl. Pad 29, 30, 31) -> Sanfter Verlauf bis zum Ende
            t = (15 - i) / 7.0
            v = int(round(102 * t))
            
        cols.append((v << 16) | (v << 8) | v)
    return cols

DEFAULT_BANK_B_COLORS = _make_bank_b_defaults()

drum_colors_a = list(DEFAULT_BANK_A_COLORS)
drum_colors_b = list(DEFAULT_BANK_B_COLORS)
custom_palette_slots = [0x000000, 0x000000, 0x000000, 0x000000]

COLD_PALETTE = [
    0xFF0000, 0xFF4000, 0xFF9600, 0xFFFF00,
    0x80FF00, 0x00FF00, 0x00FF64, 0x00FFFF,
    0x0080FF, 0x0000FF, 0x5A00FF, 0xB400FF,
    0xFF00FF, 0xFF006E, 0xFFFFFF, 0x000000,
]

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lynx_cold_drum_colors.json")
try:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data.get("bank_a"), list) and len(data["bank_a"]) == 16:
                drum_colors_a = [int(x) for x in data["bank_a"]]
            if isinstance(data.get("bank_b"), list) and len(data["bank_b"]) == 16:
                drum_colors_b = [int(x) for x in data["bank_b"]]
            if isinstance(data.get("custom_palette"), list) and len(data["custom_palette"]) == 4:
                custom_palette_slots = [int(x) for x in data["custom_palette"]]
except Exception:
    pass

def save_drum_colors():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "bank_a": drum_colors_a,
                "bank_b": drum_colors_b,
                "custom_palette": custom_palette_slots
            }, f)
    except Exception:
        pass

current_color_set = 1
step_color_set = 0
drum_layout_mode = 0
COLOR_PLAY_USER = (100, 100, 100)

# =============================================================================
# WINDOWS WIN32 & CHANNEL RACK PIXEL-KLICK / SYNC LOGIK
# =============================================================================
user32 = ctypes.WinDLL('user32', use_last_error=True)
MY_EXTRA_INFO = 0x910910

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass

user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

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

channel_rack_hwnd = None
last_pad_click_time = 0.0
last_mute_click_time = 0.0

def get_channel_rack_hwnd():
    global channel_rack_hwnd
    if channel_rack_hwnd and user32.IsWindow(channel_rack_hwnd):
        return channel_rack_hwnd

    found = []
    def enum_cb(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                t = buf.value.lower()
                if "lynx share - channel rack" in t and not any(b in t for b in ["chrome", "edge", "firefox", "opera"]):
                    found.append(hwnd)
                    return False
        return True

    cb = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(enum_cb)
    user32.EnumWindows(cb, 0)
    if found:
        channel_rack_hwnd = found[0]
    return channel_rack_hwnd

def is_lynx_window_active():
    fg = user32.GetForegroundWindow()
    if not fg:
        return False
    length = user32.GetWindowTextLengthW(fg)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(fg, buf, length + 1)
        t = buf.value.lower()
        if "lynx" in t and not any(b in t for b in ["chrome", "edge", "firefox", "opera"]):
            return True
    return False

def click_channel_rack_step(actual_col, actual_row):
    global last_pad_click_time
    hwnd = get_channel_rack_hwnd()
    if not hwnd:
        return

    last_pad_click_time = time.time()

    x = int(round((296 + (actual_col * 22)) * lynx_scale))
    y = int(round((48 + (actual_row * 30)) * lynx_scale))

    pt = wintypes.POINT(x, y)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))

    user32.SetForegroundWindow(hwnd)

    old_pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(old_pt))

    user32.SetCursorPos(pt.x, pt.y)
    user32.mouse_event(0x0002, 0, 0, 0, MY_EXTRA_INFO)
    user32.mouse_event(0x0004, 0, 0, 0, MY_EXTRA_INFO)
    user32.SetCursorPos(old_pt.x, old_pt.y)

def click_channel_rack_mute(actual_row, solo=False):
    global last_mute_click_time
    hwnd = get_channel_rack_hwnd()
    if not hwnd:
        return

    last_mute_click_time = time.time()

    x = int(round(13 * lynx_scale))
    y = int(round((48 + (actual_row * 30)) * lynx_scale))

    pt = wintypes.POINT(x, y)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))

    user32.SetForegroundWindow(hwnd)

    old_pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(old_pt))

    user32.SetCursorPos(pt.x, pt.y)
    if solo:
        user32.mouse_event(0x0008, 0, 0, 0, MY_EXTRA_INFO)
        user32.mouse_event(0x0010, 0, 0, 0, MY_EXTRA_INFO)
    else:
        user32.mouse_event(0x0002, 0, 0, 0, MY_EXTRA_INFO)
        user32.mouse_event(0x0004, 0, 0, 0, MY_EXTRA_INFO)
    user32.SetCursorPos(old_pt.x, old_pt.y)

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
# 2. BIDIREKTIONALER VIRTUELLER MIDI-PORT FÜR LYNX (INKL. CLOCK-SYNC)
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
TE_VM_FLAGS_INSTANTIATE_BOTH = 12
VM_CALLBACK = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), wintypes.DWORD, ctypes.c_size_t)

midi_sync_active = False
last_clock_time = 0.0
clock_tick_count = 0
clock_timestamps = []
sync_ui_dirty = False
sync_play_led_target = -1
cached_highest_active_col = 15

def get_max_step_offset():
    return max(0, (grid_right_bars * 16) - 16)

def get_max_channel_offset():
    return max(0, grid_down_limit - 4)

def update_highest_active_col():
    global cached_highest_active_col
    highest = 15
    limit_r = min(grid_down_limit, MAX_ALLOC_CHANNELS)
    for c in range(TOTAL_ALLOC_STEPS - 1, 15, -1):
        found = False
        for r in range(limit_r):
            if step_matrix[r][c] == 1:
                highest = c
                found = True
                break
        if found:
            break
    cached_highest_active_col = highest

def get_total_pattern_steps():
    max_cols = grid_right_bars * 16
    highest = max(15, min(max_cols - 1, cached_highest_active_col))
    if step_offset > 0:
        highest = min(max_cols - 1, max(highest, step_offset + 15))
    return min(max_cols, ((highest // 16) + 1) * 16)

def on_virtual_midi_received(port_handle, data_ptr, length, instance):
    global midi_sync_active, last_clock_time, clock_tick_count, DEFAULT_BPM
    global is_playing, current_playhead_step, sync_ui_dirty, sync_play_led_target

    if not data_ptr or length == 0:
        return

    status = data_ptr[0]

    if status == 0xF8:
        now = time.perf_counter()
        if last_clock_time > 0 and (now - last_clock_time) > 0.5:
            clock_timestamps.clear()

        clock_timestamps.append(now)
        if len(clock_timestamps) > 49:
            clock_timestamps.pop(0)

        if len(clock_timestamps) >= 25:
            total_dt = clock_timestamps[-1] - clock_timestamps[0]
            intervals = len(clock_timestamps) - 1
            if total_dt > 0.05:
                bpm_calc = round((60.0 * intervals) / (total_dt * 24.0), 1)
                if 10.0 <= bpm_calc <= 522.0:
                    DEFAULT_BPM = bpm_calc

        last_clock_time = now
        midi_sync_active = True

        if is_playing:
            total_steps = get_total_pattern_steps()
            new_step = (clock_tick_count // 6) % total_steps
            if new_step != current_playhead_step:
                current_playhead_step = new_step
                sync_ui_dirty = True

            beat_tick = clock_tick_count % 24
            if beat_tick == 0:
                beat_num = (clock_tick_count // 24) % 4
                sync_play_led_target = 4 if beat_num == 0 else 3
                sync_ui_dirty = True
            elif beat_tick == 6:
                sync_play_led_target = 1
                sync_ui_dirty = True

            clock_tick_count += 1

    elif status == 0xFA:
        midi_sync_active = True
        last_clock_time = time.perf_counter()
        clock_timestamps.clear()
        clock_tick_count = 0
        is_playing = True
        current_playhead_step = 0
        sync_play_led_target = 4
        sync_ui_dirty = True

    elif status == 0xFB:
        midi_sync_active = True
        last_clock_time = time.perf_counter()
        clock_timestamps.clear()
        is_playing = True
        sync_play_led_target = 3
        sync_ui_dirty = True

    elif status == 0xFC:
        is_playing = False
        current_playhead_step = -1
        sync_play_led_target = 2
        sync_ui_dirty = True

    elif status == 0xF2 and length >= 3:
        spp = data_ptr[1] | (data_ptr[2] << 7)
        clock_tick_count = spp * 6

vm_cb_ref = VM_CALLBACK(on_virtual_midi_received)

vm_dll.virtualMIDICreatePortEx2.restype = ctypes.c_void_p
vm_dll.virtualMIDIClosePort.restype = None
vm_dll.virtualMIDISendData.restype = wintypes.BOOL
vm_dll.virtualMIDISendData.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), wintypes.DWORD]

lynx_midi_out = vm_dll.virtualMIDICreatePortEx2(
    virtual_port_name,
    vm_cb_ref,
    0,
    65535,
    TE_VM_FLAGS_PARSE_RX | TE_VM_FLAGS_INSTANTIATE_BOTH
)

def send_to_lynx(msg):
    if not lynx_midi_out: return
    raw = msg.bytes()
    buf = (ctypes.c_ubyte * len(raw))(*raw)
    vm_dll.virtualMIDISendData(lynx_midi_out, buf, len(raw))

# =============================================================================
# 3. THREAD-SICHERE LED-STEUERUNG & MODI (NOTE, STEP, DRUM)
# =============================================================================
led_lock = threading.Lock()

def set_button_led(cc_id, val):
    with led_lock:
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

FPC_NOTE_MAP = {
    52: 37, 53: 36, 54: 42, 55: 54,
    56: 60, 57: 61, 58: 62, 59: 63,
    36: 40, 37: 38, 38: 46, 39: 44,
    40: 64, 41: 65, 42: 66, 43: 67,
    20: 48, 21: 47, 22: 45, 23: 43,
    24: 68, 25: 69, 26: 70, 27: 71,
     4: 49,  5: 55,  6: 51,  7: 53,
     8: 72,  9: 73, 10: 74, 11: 75,
}

current_key_offset = 48
current_mode = "NOTE"
TOTAL_ALLOC_STEPS = MAX_ALLOC_BARS * 16

step_matrix = [[0] * TOTAL_ALLOC_STEPS for _ in range(MAX_ALLOC_CHANNELS)]
mute_matrix = [0] * MAX_ALLOC_CHANNELS
cached_mute_leds = [-1, -1, -1, -1]
step_offset = 0
channel_offset = 0
current_playhead_step = -1
active_notes = {}

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

def get_drum_pad_note_and_color(pad_idx):
    row = pad_idx // 16
    col = pad_idx % 16

    if drum_layout_mode == 0:    # 1. Drücken: FPC Links (Spalten 0..7)
        if 0 <= col <= 7:
            note = FPC_NOTE_MAP.get(pad_idx + 4, None)
            if note is not None:
                hex_c = drum_colors_a[row * 4 + col] if col < 4 else drum_colors_b[row * 4 + (col - 4)]
                return note, hsv_scale_color(hex_c)
        return None, (0, 0, 0)

    elif drum_layout_mode == 1:  # 2. Drücken: FPC Mitte (Spalten 4..11)
        if 4 <= col <= 11:
            note = FPC_NOTE_MAP.get(pad_idx, None)
            if note is not None:
                hex_c = drum_colors_a[row * 4 + (col - 4)] if col < 8 else drum_colors_b[row * 4 + (col - 8)]
                return note, hsv_scale_color(hex_c)
        return None, (0, 0, 0)

    else:                        # 3. Drücken: FPC Rechts an der Kante (Spalten 8..15)
        if 8 <= col <= 15:
            note = FPC_NOTE_MAP.get(pad_idx - 4, None)
            if note is not None:
                hex_c = drum_colors_a[row * 4 + (col - 8)] if col < 12 else drum_colors_b[row * 4 + (col - 12)]
                return note, hsv_scale_color(hex_c)
        return None, (0, 0, 0)

def get_step_mode_pad_color(row, col):
    actual_row = row + channel_offset
    actual_col = col + step_offset

    if actual_row >= grid_down_limit or actual_col >= (grid_right_bars * 16):
        return (0, 0, 0)

    if actual_col == current_playhead_step:
        return (0, 127, 0)

    if step_matrix[actual_row][actual_col] == 1:
        return (127, 40, 0)

    if (actual_col // 4) % 2 == 0:
        return (25, 25, 25)
    else:
        if step_color_set == 0:
            return COLOR_SETS[1]["black"]
        else:
            return COLOR_SETS[0]["root"]

def refresh_mute_leds():
    for row in range(4):
        actual_row = row + channel_offset
        if actual_row < grid_down_limit:
            val = 2 if mute_matrix[actual_row] == 1 else 0
        else:
            val = 0
        if cached_mute_leds[row] != val:
            cached_mute_leds[row] = val
            set_button_led(0x24 + row, val)

def refresh_all_pads():
    with led_lock:
        updates = []
        for pad in range(64):
            row = pad // 16
            col = pad % 16

            if current_mode == "NOTE":
                _, col_rgb = get_pad_note_and_color(pad, current_key_offset)
                updates.append((pad, col_rgb[0], col_rgb[1], col_rgb[2]))
            elif current_mode == "DRUM":
                _, col_rgb = get_drum_pad_note_and_color(pad)
                updates.append((pad, col_rgb[0], col_rgb[1], col_rgb[2]))
            else:
                col_rgb = get_step_mode_pad_color(row, col)
                updates.append((pad, col_rgb[0], col_rgb[1], col_rgb[2]))

        set_pad_leds(updates)
    refresh_mute_leds()

def toggle_color_scheme():
    global current_color_set
    current_color_set = 1 - current_color_set
    refresh_all_pads()

def toggle_step_color_scheme():
    global step_color_set
    step_color_set = 1 - step_color_set
    refresh_all_pads()

def toggle_drum_layout():
    global drum_layout_mode
    drum_layout_mode = (drum_layout_mode + 1) % 3
    refresh_all_pads()

def release_held_notes():
    for pad_idx, note_val in list(active_notes.items()):
        send_to_lynx(mido.Message("note_off", note=note_val, velocity=0))
    active_notes.clear()

def set_controller_mode(new_mode):
    global current_mode
    release_held_notes()
    current_mode = new_mode

    set_button_led(0x2C, 2 if current_mode == "STEP" else 0)
    set_button_led(0x2D, 2 if current_mode == "NOTE" else 0)
    set_button_led(0x2E, 2 if current_mode == "DRUM" else 0)
    set_button_led(0x2F, 0)
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

set_button_led(0x33, 2)
set_button_led(0x34, 0)
set_button_led(0x35, 2)
set_button_led(0x32, 4)
set_button_led(0x1B, 20)
set_button_led(0x21, 0)
set_button_led(0x1F, 0)
set_button_led(0x20, 0)
set_button_led(0x22, 0)
set_button_led(0x23, 0)
for b in (0x24, 0x25, 0x26, 0x27):
    set_button_led(b, 0)

set_controller_mode("NOTE")

# =============================================================================
# 5. BILDSCHIRM-SYNC THREAD (CHANNEL RACK: STEPS + MUTE-PUNKTE)
# =============================================================================
def screen_sync_thread():
    while running:
        if is_lynx_window_active():
            hwnd = get_channel_rack_hwnd()
            if hwnd and not user32.IsIconic(hwnd):
                try:
                    ch_snap = channel_offset
                    down_lim = grid_down_limit
                    max_steps = grid_right_bars * 16

                    client_rect = wintypes.RECT()
                    user32.GetClientRect(hwnd, ctypes.byref(client_rect))
                    max_cx = client_rect.right - 5
                    max_cy = client_rect.bottom - 5

                    if (time.time() - last_mute_click_time) > 0.25:
                        mx = int(round(13 * lynx_scale))
                        my0 = int(round((48 + ch_snap * 30) * lynx_scale))
                        my3 = min(max_cy, int(round((48 + (ch_snap + 3) * 30) * lynx_scale)))

                        if mx < max_cx and my3 >= my0:
                            pt_m1 = wintypes.POINT(mx, my0)
                            pt_m2 = wintypes.POINT(mx, my3)
                            user32.ClientToScreen(hwnd, ctypes.byref(pt_m1))
                            user32.ClientToScreen(hwnd, ctypes.byref(pt_m2))

                            m_bbox = (pt_m1.x - 2, pt_m1.y - 2, pt_m2.x + 3, pt_m2.y + 3)
                            try:
                                m_img = ImageGrab.grab(bbox=m_bbox, all_screens=True)
                            except TypeError:
                                m_img = ImageGrab.grab(bbox=m_bbox)

                            for row in range(4):
                                actual_row = row + ch_snap
                                if actual_row >= down_lim:
                                    continue
                                cy = int(round((48 + actual_row * 30) * lynx_scale))
                                if cy > my3:
                                    mute_matrix[actual_row] = 0
                                    continue
                                py = cy - my0 + 2
                                is_unmuted = 0
                                for dx in (1, 2, 3):
                                    r, g, b = m_img.getpixel((dx, py))[:3]
                                    if g > 110 and g > (r + 25):
                                        is_unmuted = 1
                                        break
                                mute_matrix[actual_row] = is_unmuted
                            refresh_mute_leds()

                    if current_mode == "STEP" and (time.time() - last_pad_click_time) > 0.25:
                        offset_snap = step_offset
                        x0 = int(round((296 + offset_snap * 22) * lynx_scale))
                        y0 = int(round((48 + ch_snap * 30) * lynx_scale))
                        x15 = min(max_cx, int(round((296 + (offset_snap + 15) * 22) * lynx_scale)))
                        y3 = min(max_cy, int(round((48 + (ch_snap + 3) * 30) * lynx_scale)))

                        if x15 > x0 and y3 > y0:
                            pt_tl = wintypes.POINT(x0, y0)
                            pt_br = wintypes.POINT(x15, y3)
                            user32.ClientToScreen(hwnd, ctypes.byref(pt_tl))
                            user32.ClientToScreen(hwnd, ctypes.byref(pt_br))

                            bbox = (pt_tl.x - 2, pt_tl.y - 2, pt_br.x + 3, pt_br.y + 3)
                            try:
                                img = ImageGrab.grab(bbox=bbox, all_screens=True)
                            except TypeError:
                                img = ImageGrab.grab(bbox=bbox)

                            changed = False
                            for row in range(4):
                                actual_row = row + ch_snap
                                if actual_row >= down_lim:
                                    continue
                                cy = int(round((48 + actual_row * 30) * lynx_scale))
                                if cy > y3:
                                    continue
                                py = cy - y0 + 2

                                for col in range(16):
                                    actual_col = col + offset_snap
                                    if actual_col >= max_steps:
                                        continue
                                    cx = int(round((296 + actual_col * 22) * lynx_scale))
                                    if cx > x15:
                                        continue
                                    px = cx - x0 + 2

                                    r, g, b = img.getpixel((px, py))[:3]

                                    is_active = 1 if (r > 140 and (r - b) > 60) else 0
                                    if step_matrix[actual_row][actual_col] != is_active:
                                        step_matrix[actual_row][actual_col] = is_active
                                        changed = True

                            if changed:
                                update_highest_active_col()
                                refresh_all_pads()
                except Exception:
                    pass

        time.sleep(0.16)

threading.Thread(target=screen_sync_thread, daemon=True).start()

# =============================================================================
# 6. DRIFT-FREIER TAKT- & SYNC-THREAD
# =============================================================================
def beat_ticker_thread():
    global current_playhead_step, midi_sync_active, sync_ui_dirty, sync_play_led_target
    step_timer = 0
    next_step_time = 0.0
    was_playing = False

    while running:
        if midi_sync_active and (time.perf_counter() - last_clock_time) < 0.8:
            if sync_ui_dirty:
                sync_ui_dirty = False
                if sync_play_led_target != -1:
                    set_button_led(0x33, sync_play_led_target)
                    set_button_led(0x34, 2 if is_playing else 0)
                    sync_play_led_target = -1
                if current_mode == "STEP":
                    refresh_all_pads()
            was_playing = is_playing
            time.sleep(0.004)
            continue
        else:
            midi_sync_active = False

        if is_playing:
            if not was_playing:
                next_step_time = time.perf_counter()
                step_timer = 0
                was_playing = True

            step_duration = (60.0 / DEFAULT_BPM) / 4.0
            total_steps = get_total_pattern_steps()
            current_playhead_step = step_timer % total_steps

            if current_mode == "STEP":
                refresh_all_pads()

            if step_timer % 4 == 0:
                current_flash = 4 if (step_timer % 16 == 0) else 3
                set_button_led(0x33, current_flash)
            elif step_timer % 4 == 1:
                set_button_led(0x33, 1)

            step_timer += 1
            next_step_time += step_duration

            sleep_for = next_step_time - time.perf_counter()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                next_step_time = time.perf_counter()
        else:
            was_playing = False
            step_timer = 0
            if current_playhead_step != -1:
                current_playhead_step = -1
                if current_mode == "STEP":
                    refresh_all_pads()
            time.sleep(0.03)

threading.Thread(target=beat_ticker_thread, daemon=True).start()

# =============================================================================
# 7. MIDI-THREAD
# =============================================================================
def midi_listener_loop():
    global current_key_offset, step_offset, channel_offset, is_folder_expanded, is_browser_open
    global shift_held, alt_held, is_playing, is_recording, is_song_mode

    for msg in fire_in:
        if not running:
            break
        try:
            if msg.type == "control_change":
                if msg.control in (16, 17, 18, 19):
                    delta = msg.value if msg.value < 64 else msg.value - 128
                    new_val = max(0, min(127, knob_values[msg.control] + (delta * 2)))
                    if new_val != knob_values[msg.control]:
                        knob_values[msg.control] = new_val
                        send_to_lynx(mido.Message("control_change", control=msg.control, value=new_val))

                elif msg.control == 118:
                    if is_browser_open:
                        is_folder_expanded = False
                        if msg.value < 64:
                            press_key(0x28, 0x50, extended=True)
                        else:
                            press_key(0x26, 0x48, extended=True)
                    else:
                        if current_mode == "STEP":
                            if alt_held:
                                max_ch = get_max_channel_offset()
                                ch_jump = 4 if shift_held else 1
                                if msg.value < 64:
                                    channel_offset = min(max_ch, channel_offset + ch_jump)
                                else:
                                    channel_offset = max(0, channel_offset - ch_jump)
                            else:
                                max_st = get_max_step_offset()
                                step_jump = 16 if shift_held else 1
                                if msg.value < 64:
                                    step_offset = min(max_st, step_offset + step_jump)
                                else:
                                    step_offset = max(0, step_offset - step_jump)
                            refresh_all_pads()

            elif msg.type in ("note_on", "note_off"):
                if 54 <= msg.note <= 117:
                    pad_idx = msg.note - 54
                    row = pad_idx // 16
                    col = pad_idx % 16

                    if current_mode in ("NOTE", "DRUM"):
                        if current_mode == "NOTE":
                            note_val, default_color = get_pad_note_and_color(pad_idx, current_key_offset)
                        else:
                            note_val, default_color = get_drum_pad_note_and_color(pad_idx)

                        if note_val is not None:
                            is_down = (msg.type == "note_on" and msg.velocity > 0)
                            if is_down:
                                send_to_lynx(mido.Message("note_on", note=note_val, velocity=msg.velocity))
                                active_notes[pad_idx] = note_val
                                with led_lock:
                                    set_pad_leds([(pad_idx, COLOR_PLAY_USER[0], COLOR_PLAY_USER[1], COLOR_PLAY_USER[2])])
                            else:
                                if pad_idx in active_notes:
                                    send_to_lynx(mido.Message("note_off", note=active_notes[pad_idx], velocity=0))
                                    del active_notes[pad_idx]
                                with led_lock:
                                    set_pad_leds([(pad_idx, default_color[0], default_color[1], default_color[2])])
                    else:
                        if msg.type == "note_on" and msg.velocity > 0:
                            actual_row = row + channel_offset
                            actual_col = col + step_offset
                            if actual_row < grid_down_limit and actual_col < (grid_right_bars * 16):
                                click_channel_rack_step(actual_col, actual_row)
                                step_matrix[actual_row][actual_col] = 1 - step_matrix[actual_row][actual_col]
                                update_highest_active_col()
                                refresh_all_pads()

                elif 16 <= msg.note <= 19:
                    pass

                elif 0x24 <= msg.note <= 0x27 and msg.type == "note_on" and msg.velocity > 0:
                    row = msg.note - 0x24
                    actual_row = row + channel_offset
                    if actual_row < grid_down_limit:
                        if shift_held:
                            click_channel_rack_mute(actual_row, solo=True)
                        else:
                            click_channel_rack_mute(actual_row, solo=False)
                            mute_matrix[actual_row] = 1 - mute_matrix[actual_row]
                            refresh_mute_leds()

                elif msg.note == 0x2C and msg.type == "note_on" and msg.velocity > 0:
                    if current_mode != "STEP":
                        set_controller_mode("STEP")
                    else:
                        toggle_step_color_scheme()

                elif msg.note == 0x2D and msg.type == "note_on" and msg.velocity > 0:
                    if current_mode != "NOTE":
                        set_controller_mode("NOTE")
                    else:
                        toggle_color_scheme()

                elif msg.note == 0x2E and msg.type == "note_on" and msg.velocity > 0:
                    if current_mode != "DRUM":
                        set_controller_mode("DRUM")
                    else:
                        toggle_drum_layout()

                elif msg.note == 0x2F:
                    pass

                elif msg.note == 0x31:
                    alt_held = (msg.type == "note_on" and msg.velocity > 0)
                    set_button_led(0x31, 2 if alt_held else 0)

                elif msg.note == 25 and msg.type == "note_on" and msg.velocity > 0:
                    if is_browser_open:
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
                    else:
                        if current_mode == "STEP":
                            if alt_held:
                                channel_offset = 0
                            else:
                                step_offset = 0
                            refresh_all_pads()

                elif msg.note == 33 and msg.type == "note_on" and msg.velocity > 0:
                    press_alt_f8_safe()
                    is_browser_open = not is_browser_open
                    set_button_led(0x21, 2 if is_browser_open else 0)

                elif msg.note == 0x1F:
                    is_down = (msg.type == "note_on" and msg.velocity > 0)
                    set_button_led(0x1F, 2 if is_down else 0)
                    if is_down:
                        if alt_held and current_mode == "STEP":
                            ch_jump = 4 if shift_held else 1
                            channel_offset = max(0, channel_offset - ch_jump)
                            refresh_all_pads()
                        else:
                            press_key(0x6B, 0x4E)

                elif msg.note == 0x20:
                    is_down = (msg.type == "note_on" and msg.velocity > 0)
                    set_button_led(0x20, 2 if is_down else 0)
                    if is_down:
                        if alt_held and current_mode == "STEP":
                            max_ch = get_max_channel_offset()
                            ch_jump = 4 if shift_held else 1
                            channel_offset = min(max_ch, channel_offset + ch_jump)
                            refresh_all_pads()
                        elif shift_held:
                            press_key(0x73, 0x3E)
                        else:
                            press_key(0x6D, 0x4A)

                elif msg.note in (0x22, 0x23):
                    is_down = (msg.type == "note_on" and msg.velocity > 0)
                    set_button_led(msg.note, 2 if is_down else 0)
                    if is_down:
                        if msg.note == 0x22: current_key_offset = max(12, current_key_offset - 12)
                        elif msg.note == 0x23: current_key_offset = min(96, current_key_offset + 12)
                        refresh_all_pads()

                elif msg.note == 0x30:
                    shift_held = (msg.type == "note_on" and msg.velocity > 0)
                    set_button_led(0x30, 2 if shift_held else 0)

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

                elif msg.note == 0x34 and msg.type == "note_on" and msg.velocity > 0:
                    if not shift_held:
                        if is_playing:
                            press_key(0x20, 0x39)
                            is_playing = False
                        set_button_led(0x33, 2)
                        set_button_led(0x34, 0)

                elif msg.note == 0x35 and msg.type == "note_on" and msg.velocity > 0:
                    if not shift_held:
                        press_key(0x52, 0x13)
                        is_recording = not is_recording
                        set_button_led(0x35, 3 if is_recording else 2)

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
# 8. TKINTER FENSTER: ALLE EXAKT 270x340 GROSS!
# =============================================================================
tk_root = None
tempo_win = None
grid_win = None
drum_win = None
color_popup = None

if HAS_TK:
    tk_root = tk.Tk()
    tk_root.withdraw()

def show_tempo_gui_on_main_thread():
    global tempo_win, DEFAULT_BPM
    if not HAS_TK or not tk_root:
        return

    if tempo_win is not None and tempo_win.winfo_exists():
        tempo_win.lift()
        tempo_win.focus_force()
        return

    tempo_win = tk.Toplevel(tk_root)
    tempo_win.title("LYNX COLD - Edit Tempo (BPM)")
    tempo_win.geometry("270x340")
    tempo_win.resizable(False, False)
    tempo_win.configure(bg="#1E1E1E")
    tempo_win.attributes("-topmost", True)

    MIN_BPM = 10.0
    MAX_BPM = 522.0

    lbl_title = tk.Label(tempo_win, text="EDIT TEMPO (BPM)", fg="#AAAAAA", bg="#1E1E1E", font=("Segoe UI", 10, "bold"))
    lbl_title.pack(pady=(12, 2))

    lbl_sync = tk.Label(tempo_win, text="○ Manuell", fg="#888888", bg="#1E1E1E", font=("Segoe UI", 9))
    lbl_sync.pack(pady=(0, 8))

    canvas = tk.Canvas(tempo_win, width=170, height=170, bg="#1E1E1E", highlightthickness=0)
    canvas.pack()

    lbl_bpm = tk.Label(tempo_win, text=f"{DEFAULT_BPM:.1f} BPM", fg="#00B4FF", bg="#1E1E1E", font=("Segoe UI", 16, "bold"))
    lbl_bpm.pack(pady=(2, 10))

    drag_state = {"y": 0, "start_bpm": DEFAULT_BPM}
    last_drawn = {"bpm": -1.0, "sync": None}

    def draw_knob(force=False):
        sync_now = midi_sync_active and (time.perf_counter() - last_clock_time) < 0.8
        if not force and last_drawn["bpm"] == DEFAULT_BPM and last_drawn["sync"] == sync_now:
            return
        last_drawn["bpm"] = DEFAULT_BPM
        last_drawn["sync"] = sync_now

        canvas.delete("all")
        cx, cy, r = 85, 85, 62
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=-45, extent=270, style=tk.ARC, outline="#383838", width=10)

        ratio = max(0.0, min(1.0, (DEFAULT_BPM - MIN_BPM) / (MAX_BPM - MIN_BPM)))
        extent = -ratio * 270.0
        arc_color = "#00E676" if sync_now else "#00B4FF"
        if abs(extent) > 0.5:
            canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=225, extent=extent, style=tk.ARC, outline=arc_color, width=10)

        ir = 44
        canvas.create_oval(cx - ir, cy - ir, cx + ir, cy + ir, fill="#2A2A2A", outline="#444444", width=2)

        angle_deg = 225.0 - (ratio * 270.0)
        angle_rad = math.radians(angle_deg)
        nx = cx + math.cos(angle_rad) * (ir - 10)
        ny = cy - math.sin(angle_rad) * (ir - 10)
        canvas.create_line(cx, cy, nx, ny, fill=arc_color, width=4, capstyle=tk.ROUND)

        if sync_now:
            lbl_sync.config(text="● MIDI Sync aktiv (LYNX SHARE)", fg="#00E676")
            lbl_bpm.config(text=f"{DEFAULT_BPM:.1f} BPM", fg="#00E676")
        else:
            lbl_sync.config(text="○ Manuell (Kein MIDI Clock)", fg="#888888")
            lbl_bpm.config(text=f"{DEFAULT_BPM:.1f} BPM", fg="#00B4FF")

    def set_bpm(val):
        global DEFAULT_BPM
        DEFAULT_BPM = round(max(MIN_BPM, min(MAX_BPM, val)), 1)
        draw_knob(force=True)

    def on_mouse_down(event):
        drag_state["y"] = event.y
        drag_state["start_bpm"] = DEFAULT_BPM

    def on_mouse_drag(event):
        dy = drag_state["y"] - event.y
        set_bpm(drag_state["start_bpm"] + dy * 1.2)

    def on_mouse_wheel(event):
        inc = 10.0 if (event.state & 0x0001) else 1.0
        step = inc if (event.delta > 0) else -inc
        set_bpm(DEFAULT_BPM + step)

    canvas.bind("<Button-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_drag)
    tempo_win.bind("<MouseWheel>", on_mouse_wheel)

    btn_frame = tk.Frame(tempo_win, bg="#1E1E1E")
    btn_frame.pack(pady=4)

    tk.Button(btn_frame, text=" - 1 ", command=lambda: set_bpm(DEFAULT_BPM - 1), bg="#333333", fg="white", relief=tk.FLAT, width=6).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text=" + 1 ", command=lambda: set_bpm(DEFAULT_BPM + 1), bg="#333333", fg="white", relief=tk.FLAT, width=6).pack(side=tk.LEFT, padx=5)

    def on_close():
        global tempo_win
        if tempo_win is not None:
            tempo_win.destroy()
            tempo_win = None

    tk.Button(btn_frame, text="OK", command=on_close, bg="#0078D7", fg="white", relief=tk.FLAT, width=6).pack(side=tk.LEFT, padx=5)

    def poll_sync():
        if not running or tempo_win is None or not tempo_win.winfo_exists():
            return
        draw_knob(force=False)
        tempo_win.after(250, poll_sync)

    tempo_win.protocol("WM_DELETE_WINDOW", on_close)
    draw_knob(force=True)
    tempo_win.after(250, poll_sync)

def open_tempo_window(icon=None, item=None):
    if HAS_TK and tk_root:
        tk_root.after(0, show_tempo_gui_on_main_thread)

def show_grid_gui_on_main_thread():
    global grid_win, grid_down_limit, grid_right_bars, step_offset, channel_offset
    if not HAS_TK or not tk_root:
        return

    if grid_win is not None and grid_win.winfo_exists():
        grid_win.lift()
        grid_win.focus_force()
        return

    grid_win = tk.Toplevel(tk_root)
    grid_win.title("LYNX COLD - Edit Grid (Raster)")
    grid_win.geometry("270x340")
    grid_win.resizable(False, False)
    grid_win.configure(bg="#1E1E1E")
    grid_win.attributes("-topmost", True)

    tk.Label(grid_win, text="EDIT GRID (RASTER)", fg="#AAAAAA", bg="#1E1E1E", font=("Segoe UI", 10, "bold")).pack(pady=(12, 4))

    canvas = tk.Canvas(grid_win, width=214, height=205, bg="#1E1E1E", highlightthickness=0)
    canvas.pack()

    def draw_pad_icon(x, y, w, h, fill_col):
        canvas.create_rectangle(x, y, x + w, y + h, fill="#000000", outline="#000000", width=2)
        canvas.create_rectangle(x + 3, y + 3, x + w - 3, y + h - 3, fill=fill_col, outline="")
        sx1 = x + (w // 2) - 5
        sx2 = x + (w // 2) + 5
        sy1 = y + 6
        sy2 = y + 9
        canvas.create_rectangle(sx1, sy1, sx2, sy2, fill="#111111", outline="")

    def redraw_grid_graphic():
        canvas.delete("all")
        draw_pad_icon(14, 4, 30, 38, "#00F5D4")

        canvas.create_line(58, 6, 196, 6, fill="#FFFFFF", width=3)
        canvas.create_line(196, 6, 196, 40, fill="#FFFFFF", width=3)
        canvas.create_line(58, 40, 196, 40, fill="#FFFFFF", width=3)
        canvas.create_rectangle(88, 12, 168, 34, fill="#1E1E1E", outline="#FFFFFF", width=2)
        canvas.create_text(128, 23, text=f"right ({grid_right_bars})", fill="#FFFFFF", font=("Consolas", 9, "bold"))

        canvas.create_line(14, 54, 14, 194, fill="#FFFFFF", width=3)
        canvas.create_line(44, 54, 44, 194, fill="#FFFFFF", width=3)
        canvas.create_line(14, 194, 44, 194, fill="#FFFFFF", width=3)
        canvas.create_rectangle(1, 112, 57, 136, fill="#1E1E1E", outline="#FFFFFF", width=2)
        canvas.create_text(29, 124, text=f"down {grid_down_limit}", fill="#FFFFFF", font=("Consolas", 8, "bold"))

        for r in range(3):
            for c in range(3):
                px = 64 + c * 44
                py = 54 + r * 48
                draw_pad_icon(px, py, 32, 38, "#E0E0E0")

    bottom_frame = tk.Frame(grid_win, bg="#1E1E1E")
    bottom_frame.pack(fill=tk.X, padx=14, pady=(6, 10))

    row1 = tk.Frame(bottom_frame, bg="#1E1E1E")
    row1.pack(fill=tk.X, pady=(0, 6))

    right_var = tk.StringVar(value=str(grid_right_bars))
    entry_right = tk.Entry(row1, textvariable=right_var, fg="#00FFFF", bg="#2A2A2A", insertbackground="white",
                           justify="center", width=4, relief=tk.FLAT, font=("Segoe UI", 11, "bold"))
    entry_right.pack(side=tk.LEFT)
    lbl_r_txt = tk.Label(row1, text="1. Rechts (1–10 x 16)", fg="#AAAAAA", bg="#1E1E1E", font=("Segoe UI", 8))
    lbl_r_txt.pack(side=tk.LEFT, padx=(8, 3))
    lbl_right_steps = tk.Label(row1, text=f"= {grid_right_bars * 16} Steps", fg="#888888", bg="#1E1E1E", font=("Segoe UI", 8))
    lbl_right_steps.pack(side=tk.LEFT)

    row2 = tk.Frame(bottom_frame, bg="#1E1E1E")
    row2.pack(fill=tk.X)

    down_var = tk.StringVar(value=str(grid_down_limit))
    entry_down = tk.Entry(row2, textvariable=down_var, fg="#00FFFF", bg="#2A2A2A", insertbackground="white",
                          justify="center", width=4, relief=tk.FLAT, font=("Segoe UI", 11, "bold"))
    entry_down.pack(side=tk.LEFT)
    lbl_d_txt = tk.Label(row2, text="2. Runter (4–999):", fg="#AAAAAA", bg="#1E1E1E", font=("Segoe UI", 8))
    lbl_d_txt.pack(side=tk.LEFT, padx=(8, 0))

    def update_limits(new_down=None, new_right=None):
        global grid_down_limit, grid_right_bars, channel_offset, step_offset
        if new_down is not None:
            grid_down_limit = max(MIN_DOWN_CHANNELS, min(MAX_ALLOC_CHANNELS, int(new_down)))
            channel_offset = min(channel_offset, get_max_channel_offset())
        if new_right is not None:
            grid_right_bars = max(1, min(MAX_ALLOC_BARS, int(new_right)))
            step_offset = min(step_offset, get_max_step_offset())

        down_var.set(str(grid_down_limit))
        right_var.set(str(grid_right_bars))
        lbl_right_steps.config(text=f"= {grid_right_bars * 16} Steps")
        redraw_grid_graphic()
        refresh_all_pads()

    def apply_entry_down(event=None):
        try:
            val = int(down_var.get())
            update_limits(new_down=val)
        except ValueError:
            down_var.set(str(grid_down_limit))

    def apply_entry_right(event=None):
        try:
            val = int(right_var.get())
            update_limits(new_right=val)
        except ValueError:
            right_var.set(str(grid_right_bars))

    def wheel_right(event):
        delta = 1 if event.delta > 0 else -1
        update_limits(new_right=grid_right_bars + delta)

    def wheel_down(event):
        step = 10 if (event.state & 0x0001) else 1
        delta = step if event.delta > 0 else -step
        update_limits(new_down=grid_down_limit + delta)

    for w in (entry_right, row1, lbl_r_txt, lbl_right_steps):
        w.bind("<MouseWheel>", wheel_right)
    for w in (entry_down, row2, lbl_d_txt):
        w.bind("<MouseWheel>", wheel_down)

    entry_right.bind("<Return>", apply_entry_right)
    entry_right.bind("<FocusOut>", apply_entry_right)
    entry_down.bind("<Return>", apply_entry_down)
    entry_down.bind("<FocusOut>", apply_entry_down)

    def on_close():
        global grid_win
        apply_entry_right()
        apply_entry_down()
        if grid_win is not None:
            grid_win.destroy()
            grid_win = None

    tk.Button(row2, text="OK", command=on_close, bg="#0078D7", fg="white", relief=tk.FLAT, width=5).pack(side=tk.RIGHT)

    grid_win.protocol("WM_DELETE_WINDOW", on_close)
    redraw_grid_graphic()

def open_grid_window(icon=None, item=None):
    if HAS_TK and tk_root:
        tk_root.after(0, show_grid_gui_on_main_thread)

def show_drum_gui_on_main_thread():
    global drum_win, color_popup
    if not HAS_TK or not tk_root:
        return

    if drum_win is not None and drum_win.winfo_exists():
        drum_win.lift()
        drum_win.focus_force()
        return

    drum_win = tk.Toplevel(tk_root)
    drum_win.title("LYNX COLD - Edit Drum Pads (RGB)")
    drum_win.geometry("270x340")
    drum_win.resizable(False, False)
    drum_win.configure(bg="#1E1E1E")
    drum_win.attributes("-topmost", True)

    active_bank = {"val": "A"}

    tk.Label(drum_win, text="EDIT DRUM PADS (RGB)", fg="#AAAAAA", bg="#1E1E1E", font=("Segoe UI", 10, "bold")).pack(pady=(12, 2))
    lbl_sub = tk.Label(drum_win, text="Bank A – Pad anklicken", fg="#888888", bg="#1E1E1E", font=("Segoe UI", 8))
    lbl_sub.pack(pady=(0, 8))

    canvas = tk.Canvas(drum_win, width=196, height=208, bg="#1E1E1E", highlightthickness=0)
    canvas.pack()

    pad_rects = []

    def hex_to_tk(hex_col):
        if hex_col == 0:
            return "#1E1E1E"
        return f"#{hex_col:06x}"

    def redraw_pads():
        canvas.delete("all")
        pad_rects.clear()
        colors_list = drum_colors_a if active_bank["val"] == "A" else drum_colors_b

        for r in range(4):
            for c in range(4):
                idx = r * 4 + c
                x = 10 + c * 46
                y = 6 + r * 50
                w, h = 36, 42
                fill_tk = hex_to_tk(colors_list[idx])

                canvas.create_rectangle(x, y, x + w, y + h, fill="#000000", outline="#000000", width=2)
                canvas.create_rectangle(x + 3, y + 3, x + w - 3, y + h - 3, fill=fill_tk, outline="")
                sx1 = x + (w // 2) - 6
                sx2 = x + (w // 2) + 6
                canvas.create_rectangle(sx1, y + 7, sx2, y + 10, fill="#111111", outline="")
                pad_rects.append((x, y, x + w, y + h, idx))

    def open_cold_color_picker(pad_idx):
        global color_popup
        if color_popup is not None and color_popup.winfo_exists():
            color_popup.destroy()

        drum_win.update_idletasks()
        px = drum_win.winfo_x() + drum_win.winfo_width() + 6
        py = drum_win.winfo_y()

        color_popup = tk.Toplevel(drum_win)
        color_popup.title(f"COLD FARBPALETTE (BANK {active_bank['val']})")
        color_popup.geometry(f"270x340+{px}+{py}")
        color_popup.resizable(False, False)
        color_popup.configure(bg="#1E1E1E")
        color_popup.attributes("-topmost", True)

        is_picking_custom = {"active": False}

        tk.Label(color_popup, text=f"COLD FARBPALETTE (BANK {active_bank['val']})", fg="#AAAAAA", bg="#1E1E1E", font=("Segoe UI", 10, "bold")).pack(pady=(10, 0))
        tk.Label(color_popup, text=f"Auswahl für (PAD {pad_idx + 1})", fg="#888888", bg="#1E1E1E", font=("Segoe UI", 9)).pack(pady=(0, 6))

        pal_frame = tk.Frame(color_popup, bg="#1E1E1E")
        pal_frame.pack(pady=(2, 4))

        def apply_hex_color(hex_val, is_custom=False):
            global color_popup
            if is_custom and hex_val not in COLD_PALETTE and hex_val not in custom_palette_slots:
                custom_palette_slots.insert(0, hex_val)
                custom_palette_slots.pop()

            if active_bank["val"] == "A":
                drum_colors_a[pad_idx] = hex_val
            else:
                drum_colors_b[pad_idx] = hex_val
            save_drum_colors()
            redraw_pads()
            refresh_all_pads()
            if color_popup is not None and color_popup.winfo_exists():
                color_popup.destroy()
                color_popup = None

        def pick_custom_rgb():
            is_picking_custom["active"] = True
            cur = drum_colors_a[pad_idx] if active_bank["val"] == "A" else drum_colors_b[pad_idx]
            res = colorchooser.askcolor(color=hex_to_tk(cur), parent=color_popup, title="Eigene RGB Farbe")
            is_picking_custom["active"] = False
            if res and res[0]:
                rr, gg, bb = int(res[0][0]), int(res[0][1]), int(res[0][2])
                apply_hex_color((rr << 16) | (gg << 8) | bb, is_custom=True)
            elif color_popup is not None and color_popup.winfo_exists():
                color_popup.focus_force()

        # Exakt 31 Pixel hohe Farbkacheln (4x4 Hauptpalette)
        for i, h_col in enumerate(COLD_PALETTE):
            r, c = divmod(i, 4)
            btn_bg = hex_to_tk(h_col)
            cell = tk.Frame(pal_frame, width=48, height=31, bg="#1E1E1E")
            cell.pack_propagate(False)
            cell.grid(row=r, column=c, padx=3, pady=2)
            tk.Button(
                cell,
                bg=btn_bg,
                activebackground=btn_bg,
                relief=tk.FLAT,
                bd=0,
                highlightthickness=1,
                highlightbackground="#444444",
                command=lambda col=h_col: apply_hex_color(col, is_custom=False)
            ).pack(fill=tk.BOTH, expand=True)

        # 5. Zeile: 4 gespeicherte eigene Farben (ebenfalls exakt 31 Pixel hoch)
        for c, h_col in enumerate(custom_palette_slots):
            btn_bg = hex_to_tk(h_col)
            cell = tk.Frame(pal_frame, width=48, height=31, bg="#1E1E1E")
            cell.pack_propagate(False)
            cell.grid(row=4, column=c, padx=3, pady=(4, 2))
            tk.Button(
                cell,
                bg=btn_bg,
                activebackground=btn_bg,
                relief=tk.FLAT,
                bd=0,
                highlightthickness=1,
                highlightbackground="#666666",
                command=lambda col=h_col: apply_hex_color(col, is_custom=False)
            ).pack(fill=tk.BOTH, expand=True)

        tk.Button(color_popup, text="Eigene RGB-Farbe...", command=pick_custom_rgb, bg="#333333", fg="white", relief=tk.FLAT, width=28, font=("Segoe UI", 9)).pack(pady=(6, 6))

        hex_frame = tk.Frame(color_popup, bg="#1E1E1E")
        hex_frame.pack(pady=(0, 8))

        cur_col = drum_colors_a[pad_idx] if active_bank["val"] == "A" else drum_colors_b[pad_idx]
        hex_var = tk.StringVar(value=f"#{cur_col:06X}")

        tk.Label(hex_frame, text="Hex:", fg="#AAAAAA", bg="#1E1E1E", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 6))
        entry_hex = tk.Entry(hex_frame, textvariable=hex_var, fg="#00FFFF", bg="#2A2A2A", insertbackground="white",
                             justify="center", width=11, relief=tk.FLAT, font=("Consolas", 10, "bold"))
        entry_hex.pack(side=tk.LEFT, padx=(0, 8), ipady=3)

        def apply_hex_entry(event=None):
            txt = hex_var.get().strip().lstrip("#")
            if len(txt) == 6:
                try:
                    apply_hex_color(int(txt, 16), is_custom=True)
                    return
                except ValueError:
                    pass
            hex_var.set(f"#{cur_col:06X}")

        entry_hex.bind("<Return>", apply_hex_entry)
        tk.Button(hex_frame, text="OK", command=apply_hex_entry, bg="#0078D7", fg="white", relief=tk.FLAT, width=6, font=("Segoe UI", 10)).pack(side=tk.LEFT)

        def on_popup_focus_out(event=None):
            if is_picking_custom["active"]:
                return
            def _verify():
                global color_popup
                if color_popup is None or not color_popup.winfo_exists() or is_picking_custom["active"]:
                    return
                f = color_popup.focus_displayof()
                if f is None or f.winfo_toplevel() != color_popup:
                    color_popup.destroy()
                    color_popup = None
            color_popup.after(70, _verify)

        color_popup.bind("<FocusOut>", on_popup_focus_out)
        color_popup.focus_force()

    def on_canvas_click(event):
        for (x1, y1, x2, y2, idx) in pad_rects:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                open_cold_color_picker(idx)
                break

    canvas.bind("<Button-1>", on_canvas_click)

    btn_frame = tk.Frame(drum_win, bg="#1E1E1E")
    btn_frame.pack(pady=(8, 8))

    btn_a = tk.Button(btn_frame, text="A", bg="#333333", fg="#00FFFF", relief=tk.FLAT, width=6, font=("Segoe UI", 10, "bold"))
    btn_b = tk.Button(btn_frame, text="B", bg="#333333", fg="#FFFFFF", relief=tk.FLAT, width=6, font=("Segoe UI", 10, "bold"))

    def switch_bank(b_name):
        active_bank["val"] = b_name
        btn_a.config(fg="#00FFFF" if b_name == "A" else "#FFFFFF")
        btn_b.config(fg="#00FFFF" if b_name == "B" else "#FFFFFF")
        lbl_sub.config(text=f"Bank {b_name} – Pad anklicken")
        redraw_pads()

    def reset_bank(b_name):
        if b_name == "A":
            drum_colors_a[:] = list(DEFAULT_BANK_A_COLORS)
        else:
            drum_colors_b[:] = list(DEFAULT_BANK_B_COLORS)
        save_drum_colors()
        switch_bank(b_name)
        refresh_all_pads()

    btn_a.config(command=lambda: switch_bank("A"))
    btn_b.config(command=lambda: switch_bank("B"))
    btn_a.bind("<Button-3>", lambda e: reset_bank("A"))
    btn_b.bind("<Button-3>", lambda e: reset_bank("B"))

    btn_a.pack(side=tk.LEFT, padx=5)
    btn_b.pack(side=tk.LEFT, padx=5)

    def on_close():
        global drum_win, color_popup
        if color_popup is not None and color_popup.winfo_exists():
            color_popup.destroy()
            color_popup = None
        if drum_win is not None:
            drum_win.destroy()
            drum_win = None

    tk.Button(btn_frame, text="OK", command=on_close, bg="#0078D7", fg="white", relief=tk.FLAT, width=6, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)

    drum_win.protocol("WM_DELETE_WINDOW", on_close)
    redraw_pads()

def open_drum_window(icon=None, item=None):
    if HAS_TK and tk_root:
        tk_root.after(0, show_drum_gui_on_main_thread)

# =============================================================================
# 9. TASKLEISTEN-AGENT
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
    if HAS_TK and tk_root:
        try:
            tk_root.after(0, tk_root.quit)
        except Exception:
            pass

def toggle_color_from_tray(icon, item):
    if current_mode == "STEP":
        toggle_step_color_scheme()
    elif current_mode == "DRUM":
        toggle_drum_layout()
    else:
        toggle_color_scheme()

def make_scale_callback(val):
    def _cb(icon, item):
        global lynx_scale
        lynx_scale = val
    return _cb

def make_scale_checked(val):
    def _chk(item):
        return lynx_scale == val
    return _chk

scale_menu_items = [
    pystray.MenuItem(f"{int(round(s * 100))}%", make_scale_callback(s), checked=make_scale_checked(s), radio=True)
    for s in [0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0, 2.5]
]

def show_about_dialog(icon, item):
    def _msg():
        about_msg = (
            "LYNX COLD ❄️ MIDI CONTROLLER\n"
            "Version 1.6.6 nov. 2026\n\n"
            "Autor: @oneDMB\n\n"
            "🦊 https://github.com/oneDMB\n"
            "🤠 https://github.com/deftivity\n\n"
            "Features: 999x160 Step, Dual Keyboard, RGB Drum Pads & Clock Sync!\n"
            "Entwickelt für Lynx Share"
        )
        user32.MessageBoxW(0, about_msg, "Über LYNX COLD ❄️", 0x40)
    threading.Thread(target=_msg, daemon=True).start()

tray = pystray.Icon(
    "LynxCold",
    create_tray_icon(),
    "Lynx Cold MIDI Controller",
    menu=pystray.Menu(
        pystray.MenuItem("Lynx Cold ❄️ v1.6.6", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Edit Tempo (BPM)...", open_tempo_window),
        pystray.MenuItem("Edit Grid (Raster)...", open_grid_window),
        pystray.MenuItem("Edit Drum Pads (RGB)...", open_drum_window),
        pystray.MenuItem("Farbschema / Layout wechseln", toggle_color_from_tray),
        pystray.MenuItem("LYNX SHARE Skalierung", pystray.Menu(*scale_menu_items)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Über / About ℹ️", show_about_dialog),
        pystray.MenuItem("🦊 GitHub @oneDMB", lambda icon, item: webbrowser.open("https://github.com/oneDMB")),
        pystray.MenuItem("🤠 GitHub @deftivity", lambda icon, item: webbrowser.open("https://github.com/deftivity")),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Beenden", quit_agent)
    )
)

if HAS_TK and tk_root:
    tray.run_detached()
    tk_root.mainloop()
else:
    tray.run()

# =============================================================================
# CLEANUP BEIM BEENDEN
# =============================================================================
running = False
set_pad_leds([(p, 0, 0, 0) for p in range(64)])
for b in (0x2C, 0x2D, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x1B, 0x21, 0x1F, 0x20, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x2E, 0x2F):
    set_button_led(b, 0)

if winmm:
    try:
        winmm.timeEndPeriod(1)
    except Exception:
        pass

try:
    if lynx_midi_out:
        vm_dll.virtualMIDIClosePort(lynx_midi_out)
    fire_in.close()
    fire_out.close()
except Exception:
    pass

if mutex_handle:
    try:
        kernel32.CloseHandle(mutex_handle)
    except Exception:
        pass

sys.exit(0)