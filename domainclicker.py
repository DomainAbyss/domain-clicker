#!/usr/bin/env python3
"""
GT Auto Recorder v3.0 — Advanced macro recorder & player
Features:
  - Mouse clicks, drags, moves (throttled), keyboard (all keys incl. special)
  - Multi-file manager with rename/delete
  - Action list editor (select & delete individual actions)
  - Loop with delay between loops
  - Speed control (0.25x–10x)
  - Relative/absolute coordinate mode
  - Progress bar + loop counter
  - System tray-style floating mini bar during playback
  - Configurable move throttle (reduce event spam)
  - Drag recording (mousedown + move + mouseup)
  - Per-action delay editing
  - Export as readable script
  - Persistent settings
"""

import json, time, threading, os, sys
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog
import tkinter as tk

# ── Auto-install deps ──────────────────────────────────────────────────────────
def _install(*pkgs):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", *pkgs, "-q"])

try:
    import customtkinter as ctk
except ImportError:
    _install("customtkinter"); import customtkinter as ctk
try:
    from pynput import mouse as pmouse, keyboard as pkeyboard
except ImportError:
    _install("pynput"); from pynput import mouse as pmouse, keyboard as pkeyboard
try:
    import pyautogui
except ImportError:
    _install("pyautogui"); import pyautogui
try:
    import keyboard as kb
    HAS_KB = True
except ImportError:
    try:
        _install("keyboard"); import keyboard as kb; HAS_KB = True
    except:
        HAS_KB = False

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Constants ──────────────────────────────────────────────────────────────────
SAVE_DIR = Path.home() / ".gt_recorder"
SAVE_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = SAVE_DIR / "settings.json"

SPECIAL_KEY_MAP = {
    "Key.cmd": "windows", "Key.cmd_l": "windows", "Key.cmd_r": "windows",
    "Key.ctrl": "ctrl",   "Key.ctrl_l": "ctrl",   "Key.ctrl_r": "ctrl",
    "Key.alt": "alt",     "Key.alt_l": "alt",      "Key.alt_r": "alt",
    "Key.shift": "shift", "Key.shift_l": "shift",  "Key.shift_r": "shift",
    "Key.enter": "enter", "Key.tab": "tab",         "Key.space": "space",
    "Key.esc": "escape",  "Key.backspace": "backspace",
    "Key.delete": "delete", "Key.home": "home",    "Key.end": "end",
    "Key.page_up": "page up", "Key.page_down": "page down",
    "Key.up": "up",       "Key.down": "down",
    "Key.left": "left",   "Key.right": "right",
    "Key.f1": "f1",  "Key.f2": "f2",  "Key.f3": "f3",  "Key.f4": "f4",
    "Key.f5": "f5",  "Key.f6": "f6",  "Key.f7": "f7",  "Key.f8": "f8",
    "Key.f9": "f9",  "Key.f10": "f10","Key.f11": "f11","Key.f12": "f12",
    "Key.caps_lock": "caps lock", "Key.num_lock": "num lock",
    "Key.print_screen": "print screen",
}

IGNORED_HOTKEYS = {"f1", "f2", "f3", "f4", "f5", "f6"}

ACTION_ICONS = {
    "click": "🖱",
    "rclick": "🖱",
    "dclick": "🖱🖱",
    "drag": "↔",
    "move": "➜",
    "key": "⌨",
    "wait": "⏱",
    "scroll": "↕",
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def fmt_time(s):
    if s < 60: return f"{s:.2f}s"
    return f"{int(s//60)}m{s%60:.1f}s"

def action_label(a):
    t = a.get("t", "?")
    d = a.get("d", 0)
    if t == "click":
        return f"{ACTION_ICONS['click']} Click {a.get('b','L')} @ ({a['x']},{a['y']})  [{fmt_time(d)}]"
    if t == "rclick":
        return f"{ACTION_ICONS['rclick']} Right-click @ ({a['x']},{a['y']})  [{fmt_time(d)}]"
    if t == "dclick":
        return f"{ACTION_ICONS['dclick']} Double-click @ ({a['x']},{a['y']})  [{fmt_time(d)}]"
    if t == "drag":
        return f"{ACTION_ICONS['drag']} Drag ({a['x1']},{a['y1']})→({a['x2']},{a['y2']})  [{fmt_time(d)}]"
    if t == "move":
        return f"{ACTION_ICONS['move']} Move → ({a['x']},{a['y']})  [{fmt_time(d)}]"
    if t == "key":
        return f"{ACTION_ICONS['key']} Key: {a.get('k','?')}  [{fmt_time(d)}]"
    if t == "scroll":
        dir_ = "↑" if a.get("dy", 0) > 0 else "↓"
        return f"{ACTION_ICONS['scroll']} Scroll {dir_} @ ({a['x']},{a['y']})  [{fmt_time(d)}]"
    if t == "wait":
        return f"{ACTION_ICONS['wait']} Wait {a.get('sec',1)}s  [{fmt_time(d)}]"
    return f"? {t}  [{fmt_time(d)}]"


# ══════════════════════════════════════════════════════════════════════════════
class Settings:
    DEFAULTS = {
        "move_throttle_ms": 0,
        "loop_delay_s": 0.5,
        "speed": "1.0x",
        "loops": "1",
        "record_moves": True,
        "record_keyboard": True,
        "coord_mode": "absolute",  # or "relative"
        "last_file": "",
    }

    def __init__(self):
        self.data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        if SETTINGS_FILE.exists():
            try:
                self.data.update(json.loads(SETTINGS_FILE.read_text()))
            except: pass

    def save(self):
        SETTINGS_FILE.write_text(json.dumps(self.data, indent=2))

    def __getitem__(self, k): return self.data.get(k, self.DEFAULTS.get(k))
    def __setitem__(self, k, v): self.data[k] = v; self.save()


# ══════════════════════════════════════════════════════════════════════════════
class MiniBar(ctk.CTkToplevel):
    """Floating mini toolbar visible during playback."""
    def __init__(self, master):
        super().__init__(master)
        self.title("")
        self.geometry("260x56+10+10")
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.configure(fg_color="#1a1a2e")
        self._drag_x = self._drag_y = 0

        fr = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=12)
        fr.pack(fill="both", expand=True, padx=2, pady=2)

        self.lbl = ctk.CTkLabel(fr, text="▶ Playing...", font=("Consolas", 11, "bold"),
                                 text_color="#4ade80")
        self.lbl.pack(side="left", padx=10)

        ctk.CTkButton(fr, text="■ Stop", width=64, height=26,
                      fg_color="#ef4444", hover_color="#dc2626",
                      font=("Arial", 10, "bold"),
                      command=master.stop_play).pack(side="right", padx=6, pady=8)

        fr.bind("<ButtonPress-1>", self._drag_start)
        fr.bind("<B1-Motion>", self._drag)
        self.lbl.bind("<ButtonPress-1>", self._drag_start)
        self.lbl.bind("<B1-Motion>", self._drag)

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.winfo_x()
        self._drag_y = e.y_root - self.winfo_y()

    def _drag(self, e):
        self.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    def set_status(self, txt):
        self.lbl.configure(text=txt)


# ══════════════════════════════════════════════════════════════════════════════
class ActionEditor(ctk.CTkToplevel):
    """Dialog to view/edit/delete individual recorded actions."""
    def __init__(self, master, actions, on_save):
        super().__init__(master)
        self.title("Action Editor")
        self.geometry("640x500")
        self.actions = list(actions)
        self.on_save = on_save
        self._build()
        self.grab_set()

    def _build(self):
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(top, text="Action Editor", font=("Arial", 14, "bold")).pack(side="left")
        ctk.CTkLabel(top, text=f"{len(self.actions)} actions",
                     text_color="gray").pack(side="left", padx=12)

        # Listbox area
        lf = ctk.CTkFrame(self)
        lf.pack(fill="both", expand=True, padx=10, pady=4)

        sb = ctk.CTkScrollbar(lf)
        sb.pack(side="right", fill="y")

        self.lb = tk.Listbox(lf, selectmode="extended", bg="#1a1a2e", fg="#e2e8f0",
                              font=("Consolas", 10), activestyle="none",
                              selectbackground="#3b82f6", borderwidth=0,
                              highlightthickness=0, yscrollcommand=sb.set)
        self.lb.pack(fill="both", expand=True)
        sb.configure(command=self.lb.yview)

        for a in self.actions:
            self.lb.insert("end", action_label(a))

        # Bottom bar
        bf = ctk.CTkFrame(self)
        bf.pack(fill="x", padx=10, pady=8)

        ctk.CTkButton(bf, text="🗑 Delete Selected", width=130,
                      fg_color="#ef4444", hover_color="#dc2626",
                      command=self._delete).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="⬆ Move Up", width=90,
                      command=self._move_up).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="⬇ Move Down", width=90,
                      command=self._move_down).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="✏ Edit Delay", width=90,
                      command=self._edit_delay).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="➕ Add Wait", width=90,
                      command=self._add_wait).pack(side="left", padx=4)

        ctk.CTkButton(bf, text="💾 Save & Close", width=110,
                      fg_color="#22c55e", hover_color="#16a34a",
                      command=self._save).pack(side="right", padx=4)
        ctk.CTkButton(bf, text="✖ Cancel", width=80,
                      fg_color="gray30",
                      command=self.destroy).pack(side="right", padx=4)

    def _selected_indices(self):
        return list(self.lb.curselection())

    def _delete(self):
        idxs = sorted(self._selected_indices(), reverse=True)
        if not idxs: return
        for i in idxs:
            del self.actions[i]
            self.lb.delete(i)

    def _move_up(self):
        idxs = self._selected_indices()
        if not idxs or idxs[0] == 0: return
        for i in idxs:
            self.actions[i-1], self.actions[i] = self.actions[i], self.actions[i-1]
            t0 = self.lb.get(i-1); t1 = self.lb.get(i)
            self.lb.delete(i-1, i)
            self.lb.insert(i-1, t1); self.lb.insert(i, t0)
        self.lb.selection_set(idxs[0]-1)

    def _move_down(self):
        idxs = self._selected_indices()
        if not idxs or idxs[-1] >= len(self.actions)-1: return
        for i in reversed(idxs):
            self.actions[i+1], self.actions[i] = self.actions[i], self.actions[i+1]
            t0 = self.lb.get(i); t1 = self.lb.get(i+1)
            self.lb.delete(i, i+1)
            self.lb.insert(i, t1); self.lb.insert(i+1, t0)
        self.lb.selection_set(idxs[-1]+1)

    def _edit_delay(self):
        idxs = self._selected_indices()
        if not idxs: return
        i = idxs[0]
        cur = self.actions[i].get("d", 0)
        val = simpledialog.askfloat("Edit Delay", f"New delay (seconds) for action {i+1}:",
                                     initialvalue=round(cur, 3), parent=self)
        if val is not None:
            self.actions[i]["d"] = round(val, 4)
            self.lb.delete(i)
            self.lb.insert(i, action_label(self.actions[i]))
            self.lb.selection_set(i)

    def _add_wait(self):
        idxs = self._selected_indices()
        insert_at = (idxs[-1] + 1) if idxs else len(self.actions)
        d_ref = self.actions[insert_at-1]["d"] if insert_at > 0 else 0
        sec = simpledialog.askfloat("Add Wait", "Wait duration (seconds):",
                                     initialvalue=1.0, parent=self)
        if sec is None or sec < 0: return
        wa = {"t": "wait", "sec": round(sec, 2), "d": round(d_ref + 0.001, 4)}
        self.actions.insert(insert_at, wa)
        self.lb.insert(insert_at, action_label(wa))

    def _save(self):
        self.on_save(self.actions)
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
class FileManager(ctk.CTkToplevel):
    """Manage saved macro files."""
    def __init__(self, master, on_load):
        super().__init__(master)
        self.title("Macro Files")
        self.geometry("500x400")
        self.on_load = on_load
        self._build()
        self._refresh()
        self.grab_set()

    def _build(self):
        ctk.CTkLabel(self, text="Saved Macros", font=("Arial", 14, "bold")).pack(pady=8)

        lf = ctk.CTkFrame(self)
        lf.pack(fill="both", expand=True, padx=10)
        sb = ctk.CTkScrollbar(lf)
        sb.pack(side="right", fill="y")
        self.lb = tk.Listbox(lf, bg="#1a1a2e", fg="#e2e8f0", font=("Consolas", 10),
                              selectbackground="#3b82f6", borderwidth=0,
                              highlightthickness=0, yscrollcommand=sb.set)
        self.lb.pack(fill="both", expand=True)
        sb.configure(command=self.lb.yview)
        self.lb.bind("<Double-1>", lambda e: self._load())

        bf = ctk.CTkFrame(self); bf.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(bf, text="📂 Load", width=80, command=self._load,
                      fg_color="#3b82f6").pack(side="left", padx=4)
        ctk.CTkButton(bf, text="✏ Rename", width=80, command=self._rename).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="🗑 Delete", width=80, command=self._delete,
                      fg_color="#ef4444", hover_color="#dc2626").pack(side="left", padx=4)
        ctk.CTkButton(bf, text="📤 Export Script", width=100, command=self._export).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="Close", width=70, fg_color="gray30",
                      command=self.destroy).pack(side="right", padx=4)

        self.info = ctk.CTkLabel(self, text="", text_color="gray", font=("Arial", 9))
        self.info.pack()

    def _files(self):
        return sorted(SAVE_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

    def _refresh(self):
        self.lb.delete(0, "end")
        self._flist = self._files()
        for f in self._flist:
            try:
                d = json.loads(f.read_text())
                n = len(d.get("actions", []))
                sz = f.stat().st_size
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m %H:%M")
                self.lb.insert("end", f"  {f.stem}  [{n} actions | {sz//1024}KB | {mtime}]")
            except:
                self.lb.insert("end", f"  {f.stem}  [error]")

    def _sel(self):
        s = self.lb.curselection()
        return self._flist[s[0]] if s else None

    def _load(self):
        f = self._sel()
        if not f: return
        try:
            d = json.loads(f.read_text())
            self.on_load(d["actions"], f.stem)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _rename(self):
        f = self._sel()
        if not f: return
        new = simpledialog.askstring("Rename", "New name:", initialvalue=f.stem, parent=self)
        if new and new.strip():
            new_path = SAVE_DIR / f"{new.strip()}.json"
            if new_path.exists():
                messagebox.showerror("Error", "File already exists"); return
            f.rename(new_path)
            self._refresh()

    def _delete(self):
        f = self._sel()
        if not f: return
        if messagebox.askyesno("Delete", f"Delete '{f.stem}'?"):
            f.unlink()
            self._refresh()

    def _export(self):
        f = self._sel()
        if not f: return
        try:
            d = json.loads(f.read_text())
            lines = [f"# GT Auto Recorder — Exported Script: {f.stem}", ""]
            for i, a in enumerate(d.get("actions", [])):
                t = a.get("t"); delay = a.get("d", 0)
                if t == "click":
                    lines.append(f"pyautogui.click({a['x']}, {a['y']}, button='{a.get('b','left')}')  # t={delay:.3f}s")
                elif t == "dclick":
                    lines.append(f"pyautogui.doubleClick({a['x']}, {a['y']})  # t={delay:.3f}s")
                elif t == "drag":
                    lines.append(f"pyautogui.dragTo({a['x2']}, {a['y2']}, duration=0.3)  # from ({a['x1']},{a['y1']}) t={delay:.3f}s")
                elif t == "move":
                    lines.append(f"pyautogui.moveTo({a['x']}, {a['y']})  # t={delay:.3f}s")
                elif t == "key":
                    lines.append(f"keyboard.write({a['k']!r})  # t={delay:.3f}s")
                elif t == "wait":
                    lines.append(f"time.sleep({a.get('sec',1)})  # t={delay:.3f}s")
                elif t == "scroll":
                    lines.append(f"pyautogui.scroll({a.get('dy',1)}, x={a['x']}, y={a['y']})  # t={delay:.3f}s")
            lines += ["", "# Dependencies: pip install pyautogui keyboard"]
            out = filedialog.asksaveasfilename(defaultextension=".py",
                filetypes=[("Python", "*.py")], initialfile=f"{f.stem}_script.py")
            if out:
                Path(out).write_text("\n".join(lines))
                self.info.configure(text=f"Exported to {Path(out).name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ══════════════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GT Auto Recorder v3.0")
        self.geometry("520x620")
        self.resizable(False, False)
        self.configure(fg_color="#0f0f1a")

        self.settings = Settings()
        self.actions = []
        self.rec = False
        self.play = False
        self.t0 = 0.0
        self._last_move_t = 0.0
        self._drag_start_pos = None
        self._drag_btn = None
        self._drag_cur = (0, 0)
        self._is_dragging = False
        self._last_click_time = 0.0
        self._last_click_pos = (0, 0)
        self.mini_bar = None
        self.cur_file_name = "unsaved"
        self.play_lock = threading.Event()

        self._build_ui()
        self._start_listeners()
        self._register_hotkeys()

    # ── Listeners ────────────────────────────────────────────────────────────
    def _start_listeners(self):
        self._ml = pmouse.Listener(
            on_click=self._on_click,
            on_move=self._on_move,
            on_scroll=self._on_scroll,
        )
        self._ml.start()

        self._kl = pkeyboard.Listener(on_press=self._on_key)
        self._kl.start()

    def _register_hotkeys(self):
        if not HAS_KB: return
        try:
            kb.add_hotkey("f1", self._hk_rec)
            kb.add_hotkey("f2", self._hk_play)
            kb.add_hotkey("f3", self.stop_play)
            kb.add_hotkey("f4", self.save)
            kb.add_hotkey("f5", self._hk_files)
        except: pass

    def _hk_rec(self):   self.after(0, self.toggle_rec)
    def _hk_play(self):  self.after(0, self.start_play)
    def _hk_files(self): self.after(0, self.open_files)

    # ── Own window rect ───────────────────────────────────────────────────────
    def _own_rect(self):
        try:
            x, y = self.winfo_rootx(), self.winfo_rooty()
            return x, y, x + self.winfo_width(), y + self.winfo_height()
        except: return (0, 0, 0, 0)

    def _in_own(self, px, py):
        x1, y1, x2, y2 = self._own_rect()
        return x1 <= px <= x2 and y1 <= py <= y2

    def _in_mini(self, px, py):
        if not self.mini_bar or not self.mini_bar.winfo_exists(): return False
        try:
            x, y = self.mini_bar.winfo_rootx(), self.mini_bar.winfo_rooty()
            return x <= px <= x + self.mini_bar.winfo_width() and y <= py <= y + self.mini_bar.winfo_height()
        except: return False

    # ── Recorder callbacks ────────────────────────────────────────────────────
    def _elapsed(self):
        return round(time.time() - self.t0, 4)

    def _on_move(self, x, y):
        if not self.rec: return
        if not self.settings["record_moves"]: return
        if self._in_own(x, y): return

        now = time.time()
        throttle = self.settings["move_throttle_ms"] / 1000
        if now - self._last_move_t < throttle and self._last_move_t > 0: return
        self._last_move_t = now

        if self._is_dragging and self._drag_start_pos:
            # We'll record drag end on release — just track current pos
            self._drag_cur = (x, y)
            return

        self.actions.append({"t": "move", "x": x, "y": y, "d": self._elapsed()})
        self._refresh_count()

    def _on_click(self, x, y, btn, pressed):
        if not self.rec: return
        if self._in_own(x, y): return
        if self._in_mini(x, y): return

        btn_str = "left" if "left" in str(btn).lower() else "right"
        now = time.time()
        e = self._elapsed()

        if pressed:
            # Double-click detection (within 400ms, same position ±5px)
            if (btn_str == "left" and
                    now - self._last_click_time < 0.4 and
                    abs(x - self._last_click_pos[0]) < 5 and
                    abs(y - self._last_click_pos[1]) < 5):
                # Replace last click with double-click
                if self.actions and self.actions[-1].get("t") == "click":
                    self.actions[-1] = {"t": "dclick", "x": x, "y": y, "d": self.actions[-1]["d"]}
                    self._refresh_count()
                    return

            self._drag_start_pos = (x, y)
            self._drag_btn = btn_str
            self._drag_cur = (x, y)
            self._is_dragging = False
            self._last_click_time = now
            self._last_click_pos = (x, y)
        else:
            # Released — check if drag occurred
            dx = abs((self._drag_cur[0] if self._drag_cur else x) - (self._drag_start_pos[0] if self._drag_start_pos else x))
            dy = abs((self._drag_cur[1] if self._drag_cur else y) - (self._drag_start_pos[1] if self._drag_start_pos else y))
            if (dx > 8 or dy > 8) and self._drag_start_pos:
                sx, sy = self._drag_start_pos
                self.actions.append({"t": "drag", "x1": sx, "y1": sy,
                                     "x2": x, "y2": y, "b": btn_str, "d": e})
            else:
                self.actions.append({"t": "click", "x": x, "y": y,
                                     "b": btn_str, "d": e})
            self._drag_start_pos = None
            self._is_dragging = False
            self._refresh_count()

    def _on_scroll(self, x, y, dx, dy):
        if not self.rec: return
        if self._in_own(x, y): return
        self.actions.append({"t": "scroll", "x": x, "y": y,
                              "dx": dx, "dy": dy, "d": self._elapsed()})
        self._refresh_count()

    def _on_key(self, key):
        if not self.rec: return
        if not self.settings["record_keyboard"]: return
        try:
            if hasattr(key, "name") and key.name in IGNORED_HOTKEYS: return
        except: pass
        
        # Build combo with active modifiers
        k = key.char if hasattr(key, "char") and key.char else str(key)
        
        # Check if the pressed key is itself a modifier
        is_modifier = k in ("Key.cmd", "Key.cmd_l", "Key.cmd_r", "Key.ctrl", "Key.ctrl_l", "Key.ctrl_r",
                            "Key.alt", "Key.alt_l", "Key.alt_r", "Key.shift", "Key.shift_l", "Key.shift_r")
        
        if not is_modifier:
            # Build combo with OTHER active modifiers (not this key)
            modifiers = []
            if HAS_KB:
                if kb.is_pressed("ctrl"): modifiers.append("ctrl")
                if kb.is_pressed("shift"): modifiers.append("shift")
                if kb.is_pressed("alt"): modifiers.append("alt")
                if kb.is_pressed("windows"): modifiers.append("win")
            
            if modifiers:
                k = "+".join(modifiers + [k])  # e.g., "ctrl+c", "win+i"
        
        self.actions.append({"t": "key", "k": k, "d": self._elapsed()})
        self._refresh_count()

    # ── Recording control ─────────────────────────────────────────────────────
    def toggle_rec(self):
        if self.rec:
            self.rec = False
            self._status(f"Stopped — {len(self.actions)} actions", "gray30")
            self.rec_btn.configure(text="⏺  RECORD", fg_color="#dc2626", hover_color="#b91c1c")
            self._refresh_count()
        else:
            if self.play: self.stop_play(); time.sleep(0.15)
            self.rec = True
            self.actions = []
            self.t0 = time.time()
            self._drag_start_pos = None
            self._drag_cur = (0, 0)
            self._is_dragging = False
            self.cur_file_name = "unsaved"
            self._status("● RECORDING", "#dc2626")
            self.rec_btn.configure(text="⏹  STOP REC", fg_color="#7f1d1d", hover_color="#991b1b")
            self._refresh_count()

    # ── Playback ──────────────────────────────────────────────────────────────
    def start_play(self):
        if not self.actions:
            self._status("No actions to play!", "#f59e0b"); return
        if self.play: return
        if self.rec: self.toggle_rec(); time.sleep(0.1)

        self.play = True
        lt = self.loop_var.get()
        inf = self.inf_var.get()
        self.play_loops = 999999 if inf else (int(lt) if lt.isdigit() and int(lt) > 0 else 1)
        try:
            self.play_speed = float(self.speed_var.get().replace("x", ""))
        except: self.play_speed = 1.0
        try:
            self.play_loop_delay = float(self.loop_delay_var.get())
        except: self.play_loop_delay = 0.5

        self._status("▶ Playing...", "#22c55e")
        self.play_btn.configure(text="▶ Playing...", state="disabled")
        self.stop_btn.configure(state="normal")

        # Show mini bar, hide main window
        self.mini_bar = MiniBar(self)
        self.withdraw()

        threading.Thread(target=self._play_thread, daemon=True).start()

    def _play_action(self, a):
        t = a.get("t")
        if t == "click":
            pyautogui.click(a["x"], a["y"], button=a.get("b", "left"))
        elif t == "dclick":
            pyautogui.doubleClick(a["x"], a["y"])
        elif t == "rclick":
            pyautogui.rightClick(a["x"], a["y"])
        elif t == "drag":
            pyautogui.moveTo(a["x1"], a["y1"])
            pyautogui.dragTo(a["x2"], a["y2"], button=a.get("b", "left"), duration=0.3)
        elif t == "move":
            pyautogui.moveTo(a["x"], a["y"], duration=0.0)
        elif t == "scroll":
            pyautogui.scroll(int(a.get("dy", 1)), x=a["x"], y=a["y"])
        elif t == "key":
            if not HAS_KB: return
            k = a.get("k", "")
            
            # Handle combos first: "ctrl+c", "win+i", "shift+alt+a"
            if "+" in k and not k.startswith("Key."):
                parts = k.split("+")
                for mod in parts[:-1]:  # press all modifiers
                    kb.press(mod)
                kb.press_and_release(parts[-1])  # press+release the main key
                for mod in reversed(parts[:-1]):  # release modifiers
                    kb.release(mod)
                return
            
            mapped = SPECIAL_KEY_MAP.get(k)
            if mapped:
                kb.press_and_release(mapped)
            elif k.startswith("Key."):
                kb.press_and_release(k[4:])
            elif len(k) == 1:
                kb.write(k)
            else:
                safe = k.strip("'\"")
                if safe: kb.write(safe)
        elif t == "wait":
            time.sleep(a.get("sec", 1))

    def _play_thread(self):
        for loop_i in range(1, self.play_loops + 1):
            if not self.play: break
            self.after(0, lambda i=loop_i: self.mini_bar and self.mini_bar.winfo_exists() and
                       self.mini_bar.set_status(f"▶ Loop {i}/{self.play_loops if self.play_loops < 999999 else '∞'}"))

            t0 = time.time()
            i = 0
            while i < len(self.actions):
                if not self.play: break
                a = self.actions[i]

                # Batch consecutive moves
                if a["t"] == "move":
                    end = i
                    while end + 1 < len(self.actions) and self.actions[end+1]["t"] == "move":
                        end += 1
                    target = self.actions[end]
                    wait = t0 + (target["d"] / self.play_speed) - time.time()
                    if wait > 0: time.sleep(wait)
                    try: pyautogui.moveTo(target["x"], target["y"], duration=0.0)
                    except: pass
                    i = end + 1
                    continue

                wait = t0 + (a["d"] / self.play_speed) - time.time()
                if wait > 0: time.sleep(wait)
                try:
                    self._play_action(a)
                except pyautogui.FailSafeException:
                    self.play = False
                    self.after(0, lambda: self._status("🛑 Failsafe! Move to corner stopped playback", "#f59e0b"))
                    break
                except Exception:
                    pass
                i += 1

            if self.play and loop_i < self.play_loops:
                time.sleep(self.play_loop_delay)

        self.play = False
        self.after(0, self._play_done)

    def _play_done(self):
        if self.mini_bar and self.mini_bar.winfo_exists():
            self.mini_bar.destroy()
        self.deiconify()
        self._status(f"Done — {self.play_loops if self.play_loops < 999999 else '∞'} loop(s)", "gray30")
        self.play_btn.configure(text="▶  PLAY", state="normal")
        self.stop_btn.configure(state="disabled")

    def stop_play(self):
        self.play = False
        if self.mini_bar and self.mini_bar.winfo_exists():
            self.mini_bar.destroy()
        self.deiconify()
        self._status("Stopped", "gray30")
        self.play_btn.configure(text="▶  PLAY", state="normal")
        self.stop_btn.configure(state="disabled")

    # ── Save / Load ───────────────────────────────────────────────────────────
    def save(self):
        if not self.actions:
            self._status("Nothing to save", "#f59e0b"); return
        name = simpledialog.askstring("Save Macro", "Name for this macro:",
                                       initialvalue=self.cur_file_name if self.cur_file_name != "unsaved"
                                       else datetime.now().strftime("macro_%H%M%S"),
                                       parent=self)
        if not name: return
        p = SAVE_DIR / f"{name.strip()}.json"
        payload = {
            "name": name,
            "created": datetime.now().isoformat(),
            "actions": self.actions
        }
        p.write_text(json.dumps(payload, indent=2))
        self.cur_file_name = name
        self.title(f"GT Auto Recorder v3.0 — {name}")
        self._status(f"Saved: {name}", "#3b82f6")

    def load_macro(self, actions, name):
        self.actions = actions
        self.cur_file_name = name
        self.title(f"GT Auto Recorder v3.0 — {name}")
        self._refresh_count()
        self._status(f"Loaded: {name} ({len(actions)} actions)", "#3b82f6")

    def open_files(self):
        FileManager(self, self.load_macro)

    # ── UI ─────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color="#0d0d1f", corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="GT Auto Recorder", font=("Arial", 20, "bold"),
                     text_color="#818cf8").pack(side="left", padx=18, pady=12)
        ctk.CTkLabel(hdr, text="v3.0", font=("Arial", 10),
                     text_color="#4b5563").pack(side="left")
        ctk.CTkLabel(hdr, text="F1:Rec  F2:Play  F3:Stop  F4:Save  F5:Files",
                     font=("Arial", 9), text_color="#374151").pack(side="right", padx=10)

        # Status bar
        self.status_frame = ctk.CTkFrame(self, fg_color="#111827", height=44, corner_radius=10)
        self.status_frame.pack(fill="x", padx=12, pady=(10, 4))
        self.status_lbl = ctk.CTkLabel(self.status_frame, text="Ready",
                                        font=("Consolas", 12, "bold"), text_color="#9ca3af")
        self.status_lbl.pack(side="left", padx=14, pady=10)
        self.count_lbl = ctk.CTkLabel(self.status_frame, text="",
                                       font=("Consolas", 10), text_color="#6b7280")
        self.count_lbl.pack(side="right", padx=14)

        # Main controls
        ctrl = ctk.CTkFrame(self, fg_color="#111827", corner_radius=10)
        ctrl.pack(fill="x", padx=12, pady=4)

        self.rec_btn = ctk.CTkButton(ctrl, text="⏺  RECORD", width=140, height=44,
                                      font=("Arial", 13, "bold"),
                                      fg_color="#dc2626", hover_color="#b91c1c",
                                      command=self.toggle_rec)
        self.rec_btn.pack(side="left", padx=10, pady=10)

        self.play_btn = ctk.CTkButton(ctrl, text="▶  PLAY", width=110, height=44,
                                       font=("Arial", 13, "bold"),
                                       fg_color="#16a34a", hover_color="#15803d",
                                       command=self.start_play)
        self.play_btn.pack(side="left", padx=4, pady=10)

        self.stop_btn = ctk.CTkButton(ctrl, text="■  STOP", width=100, height=44,
                                       font=("Arial", 13, "bold"),
                                       fg_color="#374151", hover_color="#4b5563",
                                       state="disabled",
                                       command=self.stop_play)
        self.stop_btn.pack(side="left", padx=4, pady=10)

        # Options panel
        opt = ctk.CTkFrame(self, fg_color="#111827", corner_radius=10)
        opt.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(opt, text="OPTIONS", font=("Arial", 9, "bold"),
                     text_color="#4b5563").pack(anchor="w", padx=12, pady=(8,2))

        row1 = ctk.CTkFrame(opt, fg_color="transparent"); row1.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(row1, text="Loops:", width=52, anchor="w").pack(side="left")
        self.loop_var = tk.StringVar(value=self.settings["loops"])
        ctk.CTkEntry(row1, width=52, textvariable=self.loop_var).pack(side="left", padx=4)

        self.inf_var = tk.IntVar(value=0)
        ctk.CTkCheckBox(row1, text="∞ Infinite", variable=self.inf_var,
                         width=90).pack(side="left", padx=8)

        ctk.CTkLabel(row1, text="Loop delay:", anchor="w").pack(side="left", padx=(12,2))
        self.loop_delay_var = tk.StringVar(value=str(self.settings["loop_delay_s"]))
        ctk.CTkEntry(row1, width=48, textvariable=self.loop_delay_var).pack(side="left", padx=2)
        ctk.CTkLabel(row1, text="s", text_color="gray").pack(side="left")

        row2 = ctk.CTkFrame(opt, fg_color="transparent"); row2.pack(fill="x", padx=8, pady=(2,8))
        ctk.CTkLabel(row2, text="Speed:", width=52, anchor="w").pack(side="left")
        self.speed_var = tk.StringVar(value=self.settings["speed"])
        ctk.CTkOptionMenu(row2, values=["0.25x","0.5x","0.75x","1.0x","1.5x","2.0x","3.0x","5.0x","10.0x"],
                           variable=self.speed_var, width=80,
                           command=lambda v: self.settings.__setitem__("speed", v)).pack(side="left", padx=4)

        ctk.CTkLabel(row2, text="Move throttle:", anchor="w").pack(side="left", padx=(12,2))
        self.throttle_var = tk.StringVar(value=str(self.settings["move_throttle_ms"]))
        ctk.CTkEntry(row2, width=40, textvariable=self.throttle_var).pack(side="left", padx=2)
        ctk.CTkLabel(row2, text="ms", text_color="gray").pack(side="left")

        # Recording options
        rec_opt = ctk.CTkFrame(self, fg_color="#111827", corner_radius=10)
        rec_opt.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(rec_opt, text="RECORDING", font=("Arial", 9, "bold"),
                     text_color="#4b5563").pack(anchor="w", padx=12, pady=(8,2))
        row3 = ctk.CTkFrame(rec_opt, fg_color="transparent"); row3.pack(fill="x", padx=8, pady=(2,8))
        self.rec_moves_var = tk.IntVar(value=1 if self.settings["record_moves"] else 0)
        ctk.CTkCheckBox(row3, text="Record mouse moves", variable=self.rec_moves_var).pack(side="left", padx=4)
        self.rec_keys_var = tk.IntVar(value=1 if self.settings["record_keyboard"] else 0)
        ctk.CTkCheckBox(row3, text="Record keyboard", variable=self.rec_keys_var).pack(side="left", padx=20)

        # Action list preview
        prev = ctk.CTkFrame(self, fg_color="#111827", corner_radius=10)
        prev.pack(fill="both", expand=True, padx=12, pady=4)
        ph = ctk.CTkFrame(prev, fg_color="transparent"); ph.pack(fill="x", padx=10, pady=(6,2))
        ctk.CTkLabel(ph, text="ACTIONS", font=("Arial", 9, "bold"),
                     text_color="#4b5563").pack(side="left")
        ctk.CTkButton(ph, text="✏ Edit", width=60, height=22,
                      font=("Arial", 9), fg_color="#374151", hover_color="#4b5563",
                      command=self._open_editor).pack(side="right", padx=2)
        ctk.CTkButton(ph, text="🗑 Clear", width=60, height=22,
                      font=("Arial", 9), fg_color="#7f1d1d", hover_color="#991b1b",
                      command=self._clear).pack(side="right", padx=2)

        lb_fr = ctk.CTkFrame(prev, fg_color="#0d0d1f", corner_radius=8)
        lb_fr.pack(fill="both", expand=True, padx=8, pady=(2,8))
        sb = ctk.CTkScrollbar(lb_fr)
        sb.pack(side="right", fill="y", pady=4)
        self.action_lb = tk.Listbox(lb_fr, bg="#0d0d1f", fg="#6b7280", font=("Consolas", 9),
                                     selectbackground="#1e3a5f", borderwidth=0,
                                     highlightthickness=0, yscrollcommand=sb.set,
                                     height=6)
        self.action_lb.pack(fill="both", expand=True, padx=4, pady=4)
        sb.configure(command=self.action_lb.yview)

        # Bottom bar
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.pack(fill="x", padx=12, pady=(2,10))
        ctk.CTkButton(bot, text="💾 Save", width=90,
                      fg_color="#1d4ed8", hover_color="#1e40af",
                      command=self.save).pack(side="left", padx=4)
        ctk.CTkButton(bot, text="📂 Files", width=90,
                      fg_color="#374151", hover_color="#4b5563",
                      command=self.open_files).pack(side="left", padx=4)
        ctk.CTkButton(bot, text="⚙ Settings", width=90,
                      fg_color="#374151", hover_color="#4b5563",
                      command=self._save_settings).pack(side="left", padx=4)
        ctk.CTkLabel(bot, text="Move mouse to corner to failsafe-stop",
                     font=("Arial", 8), text_color="#374151").pack(side="right", padx=4)

    def _open_editor(self):
        if not self.actions:
            self._status("No actions to edit", "#f59e0b"); return
        ActionEditor(self, self.actions, self._set_actions)

    def _set_actions(self, new_actions):
        self.actions = new_actions
        self._refresh_count()

    def _clear(self):
        if not self.actions: return
        if messagebox.askyesno("Clear", "Clear all recorded actions?"):
            self.actions = []
            self._refresh_count()
            self._status("Cleared", "gray30")

    def _refresh_count(self):
        n = len(self.actions)
        dur = self.actions[-1]["d"] if self.actions else 0
        self.count_lbl.configure(text=f"{n} actions | {fmt_time(dur)}")
        # Update listbox preview (last 8 items)
        self.action_lb.delete(0, "end")
        start = max(0, n - 50)
        for a in self.actions[start:]:
            self.action_lb.insert("end", action_label(a))
        if self.action_lb.size() > 0:
            self.action_lb.see("end")

    def _status(self, txt, color="gray30"):
        self.status_lbl.configure(text=txt)
        self.status_frame.configure(fg_color=color)

    def _save_settings(self):
        self.settings["record_moves"] = bool(self.rec_moves_var.get())
        self.settings["record_keyboard"] = bool(self.rec_keys_var.get())
        self.settings["loops"] = self.loop_var.get()
        self.settings["speed"] = self.speed_var.get()
        try: self.settings["move_throttle_ms"] = int(self.throttle_var.get())
        except: pass
        try: self.settings["loop_delay_s"] = float(self.loop_delay_var.get())
        except: pass
        self._status("Settings saved", "#3b82f6")

    def destroy(self):
        self._save_settings()
        try: self._ml.stop()
        except: pass
        try: self._kl.stop()
        except: pass
        super().destroy()


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    App().mainloop()