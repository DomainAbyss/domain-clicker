# DomainClicker v3.0

Advanced macro recorder and player for Windows.

## Features
- Mouse: clicks, drag, scroll, movement (unlimited FPS)
- Keyboard: all keys including combos (Win+I, Ctrl+C)
- Smooth playback with batched move interpolation
- Loop with configurable delay, up to infinite
- Speed control: 0.25x to 10x
- Save/Load macros as JSON, file manager
- Action Editor: delete, reorder, edit delays
- Dark GUI built with CustomTkinter
- Failsafe: move mouse to corner to stop

## Quick Start

```bash
git clone git@github.com:DomainAbyss/domain-clicker.git
cd domain-clicker
pip install -r requirements.txt
python domainclicker.py
```

## Hotkeys

| Key | Action |
|-----|--------|
| F1 | Start/Stop Recording |
| F2 | Play |
| F3 | Stop |
| F4 | Save |
| F5 | File Manager |

## Build EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name DomainClicker domainclicker.py
```

## Notes
- Clicks on own window are not recorded
- Key combos auto-detected (hold Ctrl, press C = ctrl+c)
- Failsafe: move cursor to any screen corner to stop
