# DomainClicker v3.0

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)](https://github.com/DomainAbyss/domain-clicker)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Advanced macro recorder and player for Windows. Record mouse movements, clicks, and keyboard combos, then replay with speed control and infinite loops.

## Features

- **Mouse** — clicks, double-clicks, drag, scroll, and raw movement capture
- **Keyboard** — all keys including combos (Win+I, Ctrl+C, Shift+Alt)
- **Smooth Playback** — batched move interpolation for fluid cursor motion
- **Loop** — configurable count or infinite, with delay between loops
- **Speed Control** — 0.25x to 10x playback speed
- **Save / Load** — macros stored as JSON, built-in file manager
- **Action Editor** — delete, reorder, edit delays, insert waits
- **Dark GUI** — built with CustomTkinter
- **Failsafe** — move mouse to any screen corner to emergency-stop

## Quick Start

### Prerequisites
- Python 3.10 or higher
- Windows

### Install

```bash
# Clone
git clone https://github.com/DomainAbyss/domain-clicker.git
cd domain-clicker

# Install dependencies
pip install -r requirements.txt
```

No API keys. No accounts. Just Python.

## Usage

### Recording
1. Click **RECORD** or press 
2. Perform your mouse and keyboard actions
3. Click **STOP** or press  again

### Playback
- Click **PLAY** or press  — replays actions exactly as recorded
- Press  to stop at any time
- Set **Loop** and **Speed** before playing

### Hotkeys

| Key | Action |
|-----|--------|
|  | Start / Stop Recording |
|  | Play |
|  | Stop Playback |
|  | Save Macro |
|  | File Manager |

### Key Combos
Hold any modifier (, , , ) and press another key — combo recorded automatically.
Example:  +  → saved as , replayed correctly.

## Build Standalone EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name DomainClicker domainclicker.py
```

Output:  — no Python required to run.

## File Storage

Macros saved to  as  files.

## License

MIT — do whatever you want.
