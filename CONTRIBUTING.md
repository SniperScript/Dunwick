# Contributing to Chronicles of Dunwick: Defying Fate (1924)

Welcome to the **Chronicles of Dunwick** development team! This guide explains how to set up your local development environment, collaborate with git branches, and submit Pull Requests cleanly.

---

## 1. Quick Setup for Collaborators

### Prerequisites
- **Python 3.10+** (Python 3.12 or 3.14 recommended)
- **Git**
- Optional: Google Gemini or OpenAI API Key (the game includes an offline simulation broker if you don't have one).

### Initial Clone & Virtual Environment
```bash
# 1. Clone the repository
git clone https://github.com/SniperScript/Dunwick.git
cd Dunwick

# 2. Create an isolated Python virtual environment
python3 -m venv .venv

# 3. Activate the virtual environment
source .venv/bin/activate       # On Linux / macOS
# Or on Windows PowerShell:
# .venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Launch the game
./run_game.sh
# Or directly via Python:
# python main.py
```

---

## 2. Git Collaboration Workflow

To avoid overwriting each other's code and ensure smooth merges, **never push experimental code directly to `main`**.

### Standard Feature Branch Workflow
```bash
# Always start from the latest main
git checkout main
git pull origin main

# Create a dedicated feature branch
git checkout -b feature/your-feature-name
# Examples:
#   git checkout -b feature/tudor-inn-interior
#   git checkout -b feature/ambience-audio-loop
#   git checkout -b feature/day3-butterfly-dialogue
```

### Making & Testing Changes
1. Edit code or add assets in their respective directories.
2. Run the game locally to verify:
   ```bash
   python main.py
   ```
3. Test in headless mode before committing:
   ```bash
   python main.py --test-headless
   ```

### Committing & Pushing
```bash
git add .
git commit -m "Feat: Brief description of the new mechanic or asset"
git push -u origin feature/your-feature-name
```

### Opening a Pull Request (PR)
1. Navigate to [github.com/SniperScript/Dunwick/pulls](https://github.com/SniperScript/Dunwick/pulls).
2. Click **"New pull request"**.
3. Select your feature branch and compare against `main`.
4. Add a brief summary of what you implemented and request review from your teammates.
5. Once approved, merge the Pull Request!

---

## 3. Project Architecture Overview

| Module | Purpose |
| :--- | :--- |
| [`main.py`](file:///home/xczn/Documents/Coding backup/Loop/Game/main.py) | Game loop, Bloodborne gothic main menu, R.E.P.O. settings matrix, modals, camera controller, and interaction dispatch. |
| [`config.py`](file:///home/xczn/Documents/Coding backup/Loop/Game/config.py) | Screen dimensions (1360x860), 1920s medieval-steampunk palette tokens, scenario definitions, and default settings. |
| [`simulation_world.py`](file:///home/xczn/Documents/Coding backup/Loop/Game/simulation_world.py) | Overworld & interior buildings, 7-day calendar, 3 cosmic decrees, butterfly hazard simulation, and NPC schedule manager. |
| [`skeletal_engine.py`](file:///home/xczn/Documents/Coding backup/Loop/Game/skeletal_engine.py) | 8-frame seamless 2.5D isometric walk cycles (`SW`, `SE`, `NW`, `NE`), multi-joint character animations, and sprite slicing. |
| [`art_engine_25d.py`](file:///home/xczn/Documents/Coding backup/Loop/Game/art_engine_25d.py) | Isometric building facades, steam-wagons, lampposts, cobblestone pavement, and interior room cutaways. |
| [`yarn_engine.py`](file:///home/xczn/Documents/Coding backup/Loop/Game/yarn_engine.py) | YarnSpinner dialogue loader, choice parsing, branching narrative state, and local interaction scripting. |
| [`vector_memory.py`](file:///home/xczn/Documents/Coding backup/Loop/Game/vector_memory.py) | Subconscious dream echoes and cross-loop memory embeddings. |

---

## 4. Best Practices for Game Dev Collaboration

- **Coordinate Binary Asset Changes:** Git cannot automatically merge changes to `.png` spritesheets, `.jpg` backgrounds, or `.ttf` fonts. If you plan to update or replace an asset, communicate with teammates beforehand.
- **Keep API Keys Private:** `llm_config.json` is strictly ignored by `.gitignore`. Never commit API keys or private credentials into git.
- **Word-Bounded UI:** When adding new dialogue or modal text, always use `self._render_wrapped_text()` to prevent text from overflowing card borders.
- **Consistent Gothic Style:** All new buttons, cards, and dialogue panels should use the gothic stone and iron palette (`COLORS["gothic_gold"]`, `COLORS["gothic_border"]`, `COLORS["blood_crimson"]`) and `_draw_flush_gothic_brackets`.

Happy loop-breaking! Defy Fate together.
