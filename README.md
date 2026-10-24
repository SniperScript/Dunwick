# Maplewood Loop // 2.5D Family Time-Loop Mystery RPG

A playable 2.5D psychological time-loop detective RPG built with `pygame-ce` and `numpy`, featuring **4 playable members of the Mercer Family** (`Arthur`, `Elena`, `Maya`, and `Leo`) and **20 autonomous neighborhood NPCs** living out a `5:00 PM` to `6:00 PM` afternoon routine across 6 town buildings.

## Open-Source Architectural Blueprints Integrated

1. **Tiny Life (`Ellpeck/TinyLife`) — Multi-Character Household & Daily Schedules**:
   - Switch seamlessly in real time between **Arthur (`[1]`)**, **Elena (`[2]`)**, **Maya (`[3]`)**, and **Leo (`[4]`)** without resetting the loop.
   - Inactive family members and all 20 townspeople follow a `5:00 PM` to `6:00 PM` schedule, commuting across buildings (including the secret **Saboteur**, who physically walks to the Market around `5:16 PM`, passes the Sunrise Cafe around `5:32 PM`, and sneaks toward the Power Room at `5:44 PM`).
   - 2D tile matrix object interactions and `YSort` depth sorting (`main.py`, `skeletal_engine.py`).

2. **IsoCity (`victorqribeiro/isocity`) — Weighted Tile-Grid A* Navigation & Street Traffic**:
   - `TileGridEngine` (`tile_grid_engine.py`) models an `81x56` tile matrix (`TILE_SIZE = 32`) with grass, sidewalks, asphalt roads, pedestrian crosswalks, wide 5-tile open doorways, perimeter walls, and furniture footprints.
   - Sub-tile movement with automatic corner-rounding (`move_with_sliding`) guarantees smooth walking through doorways and around furniture.
   - Moving `StreetVehicle` cars and buses drive along Main Street and automatically yield when pedestrians use the crosswalks.

3. **Unknown Horizons (`unknown-horizons/unknown-horizons`) — Cross-Zone State Persistence**:
   - `SimulationWorld.zone_state` (`simulation_world.py`) routes persistent actions across zones:
     - **Mercer Home Research Terminal** syncs anomaly timing notes to your Case File.
     - **Town Market Hardware & Chemical Register** logs the restricted sabotage item and flags the buyer.
     - **High School Science Scanner** calibrates the trace frequency and unlocks the **Town Office Security Mainframe**.
     - **Police Evidence & Dispatch Terminal / Chief Miller** in the **Town Park** detains the Saboteur once you seize physical evidence and radios **Guard Hank** to open the **Town Office Power Room**.

4. **IslandEscape — Per-Character Relationship & Grudge Memory Tables**:
   - Every NPC maintains an individual relationship score (`0–100%`) and grudge set for each of the 4 Mercer family members (`Arthur`, `Elena`, `Maya`, `Leo`).
   - **False Accusation Consequence**: Confronting/accusing an innocent NPC causes them to form a **Grudge** against that family member, refusing further cooperation unless you switch to another family member (`[1–4]`), offer a **Warm Espresso** from the Sunrise Cafe, or awaken their cross-loop memory with a **Deja-Vu Pulse (`[R]`)**.

5. **OpenPixel-RPG — Starting Lore Prologue & Bottom RPG Dialogue Box**:
   - Selecting a character opens the **Starting Lore Prologue (`LORE_PROLOGUE`)** screen detailing the 6:00 PM Aether-Core anomaly and that character's personal perspective and specialty.
   - Classic bottom RPG dialogue window with a framed `135x135` character bust portrait, animated talking expression, relationship badge, and typewriter-revealed dialogue.

## Running the Game

```bash
"/home/xczn/Documents/Coding backup/INVENTIONS ahh/.venv/bin/python" "/home/xczn/Documents/Coding backup/INVENTIONS ahh/Game?/main.py"
```
