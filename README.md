# Chronicles of Dunwick: Defying Fate (1924)
*A 2.5D Medieval-Steampunk 1920s British Time-Loop & Butterfly-Effect Survival RPG*

Set in **Dunwick-on-Severn (Anno Domini 1924)**—a 14th-century Norman stone and Tudor half-timbered British market borough retrofitted with 1920s brass steam-carriages, pneumatic telegraphs, Victorian gaslamps, and the towering **Imperial Aether-Boiler**.

---

## Core Design Pillars

### 1. Three Playable Scenarios of Predetermined Fate (`[F1]`–`[F3]`)
At the start of a campaign, choose which cosmic decree you are fighting against across a full **7-Day Week (Monday through Sunday)**:
1. **Scenario I — The Doomsday Clock ("The World Will End")**:
   - The Imperial Aether-Boiler & Ley-Line Anchor beneath the Clocktower Foundry is fated to rupture and vaporize the world.
   - Foiling Day 1's brass pressure relay causes a **Butterfly Effect**: Day 2 backs coal-gas into the Guildhall Bazaar cellars; Day 3 arcs St. Dunstan's galvanic coils; Day 4 superheats the Brass Kettle steam-urns; Day 5 triggers a Ministry lockdown; Day 6 seizes the Clocktower pendulum; Day 7 brings the Grand Harmonic Convergence.
2. **Scenario II — The Grim Decree ("You Are Going to Die")**:
   - Predetermined Fate has marked **YOU** for death. Every day you survive twists the causal web into a new lethal hazard:
   - *Monday*: Poisoned Earl Grey draught at The Brass Kettle -> *Tuesday*: Runaway Steam-Lorry brake failure on High Street -> *Wednesday*: Choking & suffocation on a hurried plate of spiced mutton pie -> *Thursday*: Falling 300-pound medieval stone gargoyle -> *Friday*: 10,000-volt Galvanic capacitor arc -> *Saturday*: Silent coal-damp flue leak in Ashford Manor -> *Sunday*: The Reaper's Seventh Bell.
3. **Scenario III — The Thread of Fate ("Your Loved One Is Going to Die")**:
   - Someone you cherish (`Arthur -> Lady Elena`, `Elena -> Young Leo`, `Maya -> Chloe`, `Leo -> Sister Maya`) is marked by Fate to die.
   - *Monday*: Clockwork Assassination outside the Teahouse -> *Tuesday*: Shifting their schedule puts them directly into a **Runaway Steam-Carriage Crash** on High Street -> *Wednesday*: Rattled by Tuesday's near-miss, they bolt down lunch and risk **Choking / Suffocating on a Plate of Spiced Mutton Pie** -> *Thursday*: Scalding Steam-Manifold Burst -> *Friday*: Mislabeled Belladonna Tincture at the Apothecary -> *Saturday*: Crumbling Gargoyle Masonry -> *Sunday*: Severing the Fatal Thread.
   - **Only by protecting them across all 7 Days (an entire week) is Fate's grip permanently broken!**

### 2. The "Sole Knower" Law & Real Human Psychology
- You select **1 of the 4 members of the Ashford-Mercer Family** (`Lord Arthur`, `Lady Elena`, `Maya`, or `Leo`).
- **ONLY your chosen character remembers the time loop and knows what is coming!** Even the other three members of your own family are unawakened 1920s humans going about their week.
- **Composure & Credibility Meter (`0–100%`)**: If you run around screaming about "time loops" or "the end of the world" without grounding your warnings in plausible 1924 concerns or physical evidence, townsfolk—and your own family—will think you have contracted **Galvanic Delirium** and have Chief Inspector Miller & Sister Joya confine you!
- Instead, treat every character as a real human: observe their **Daily Behavioral Micro-Tells** (e.g., checking a tarnished pocket-watch, clutching an oilcloth parcel, rushing before the tram bell), share a calming cup of **Earl Grey**, and intervene subtly.

### 3. Why It Can Never Be "Solved" (Dynamic Permutation & AI Subconscious Echoes)
- **Procedural Butterfly Permutation**: Every loop and every day dynamically permutes which NPC is the unwitting catalyst, which witness noticed the tell, how NPC schedules shift, and how your previous day's intervention style ripples into tomorrow.
- **Subconscious Dream Echoes (`vector_memory.py` + `cloud_llm_broker.py`)**: When a loop resets after a death or disaster, NPCs retain faint `[SUBCONSCIOUS DREAM]` vector engrams of the previous loop's tragedy, causing their mood, small-talk, and AI responses to evolve on every single loop.
- **Four Distinct Ways to Foil Every Threat**:
  1. **Physical / Station Disarmament**: Inspect and disarm the hazard at its 2.5D steampunk station.
  2. **Human Schedule Redirection**: Persuade the catalyst or your Loved One to alter their afternoon routine.
  3. **Specialist / Authority Proxy**: Alert the right borough specialist (`Sister Joya`, `Chief Stoker Raj`, `Inspector Miller`, `Constable Rosa`, `Apothecary Lin`, `Professor Clarke`) once you have a concrete observation.
  4. **Aether-Premonition Awakening (`[R]`)**: Awaken a vivid flash of foresight in a key NPC.

---

## Controls

- **`[WASD]` / `[Arrow Keys]`**: Walk across 1924 Dunwick-on-Severn (Overworld & Interior Rooms)
- **`[E]` / `[SPACE]` / Walk into Doorway**:
  - **At a House Front Door (on Overworld)**: Enter the building and switch the scene to its dedicated **2.5D Cutaway Interior Room** (showing the people and stations inside that building!)
  - **At an Interior Exit Door (or press `[BACKSPACE]` / `[ESC]`)**: Step back outside onto the **Dunwick-on-Severn Overworld**
  - **Near a Person or Steampunk Station**: Converse with NPCs or inspect interactive stations
- **`[G]`**: Advance to the Next Day of the 7-Day Week (once today's Fate Vector is foiled!)
- **`[N]`**: Open your **Foresight Journal & 7-Day Butterfly Web**
- **`[F]`**: Open the **Scenario (`[F1–F3]`) & Family Protagonist (`[1–4]`) Selector**
- **`[R]`** *(in dialogue)*: Trigger an **Aether-Premonition** in the NPC
- **`[T]`** *(in dialogue)*: Speak custom free-form text to the AI NPC
- **`[K]`**: Configure optional Google Gemini / OpenAI API Key

## Running the Game

```bash
./run_game.sh
```
