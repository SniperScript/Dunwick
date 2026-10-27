# CHRONICLES OF DUNWICK: DEFYING FATE (1924) // 2:1 Isometric Engine

A complete merge of the **IsoEngine 2:1 Isometric Grid Engine** with all narrative, temporal, neural, and procedural systems of **Chronicles of Dunwick: Defying Fate (1924)**.

---

## Key Features

1. **2:1 Isometric World & Interior Architecture**:
   - Continuous 81×56 isometric overworld (`4560 × 2400` px pre-baked ground canvas with depth-sorted elements).
   - 6 cutaway isometric interior rooms (`home`, `police`, `clocktower`, `cafe`, `laboratory`, `tavern`).
   - 108 true 2:1 isometric sprites (`tiles`, `walls`, `houses`, `props`, `furniture`, `quests`, `vehicles`).
   - 11 4-directional character skeletal sprites projected into isometric screenspace (`SE`, `SW`, `NE`, `NW`).
   - 2:1 angled tram tracks, moving steampunk streetcars, and isometric headlight cones.

2. **Complete Dunwick Narrative & Simulation Systems**:
   - **Three Playable Fate Scenarios**: *The Looming Rupture*, *The Grim Decree*, and *The Threads of Fate*.
   - **Sole-Knower Family Protagonist Selection**: Choose between *Lord Arthur (Father)*, *Lady Elena (Mother)*, *Maya (Sister)*, or *Leo (Brother)*. Only your chosen hero retains memories of the time loop!
   - **7-Day Butterfly Effect & Neural Psyche Web**: Hebbian neural networks across all 24 town citizens track trust, suspicion, receptivity, and subconscious déjà vu ripples across loops.
   - **Full Modal Hierarchy**: Bloodborne-styled Main Menu, Settings Matrix, Character Select, Lore Prologue, Foresight Codex & Journal, and Typewriter Dialogue Box with Premonitions.
   - **Death Cinematics**: 5 distinct fatal failure sequences with temporal rewind back to Monday.

---

## Quick Start

```bash
# Activate virtual environment and run:
.venv/bin/python3 main.py

# Or run headless verification test:
.venv/bin/python3 main.py --test-headless
```

### Requirements
- Python 3.10+ (Fully compatible with Python 3.14+)
- `pygame>=2.6.1`
- `Pillow>=10.0.0`
- Pure-Python fallback included for NumPy/vector embeddings.

---

## Gameplay Controls

| Key / Input | Action |
| :--- | :--- |
| **`W`, `A`, `S`, `D`** or **Arrows** | Walk in 2:1 isometric space (NW, NE, SW, SE) |
| **Left Click** | Click-to-move waypoint navigation / UI interaction |
| **Middle Click Drag** | Pan isometric camera freely |
| **`E`** | Interact with NPCs, stations, or doorway portals |
| **`Backspace`** | Exit interior building back to overworld street |
| **`N`** | Open Foresight Codex & 7-Day Butterfly Journal |
| **`G`** | Advance to next day once today's hazard is foiled |
| **`F1` - `F5`** | Trigger Death / Loop reset cinematics |
| **`F11`** | Toggle Fullscreen |
| **`ESC`** | In-game pause / Back / Cancel |
