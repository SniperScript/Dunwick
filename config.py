"""
Configuration for CHRONICLES OF DUNWICK: DEFYING FATE (1924)
A 2.5D Medieval-Steampunk 1920s British Time-Loop & Butterfly-Effect Survival RPG.

Core Pillars:
1. THREE SCENARIOS OF FATE:
   - Scenario 1 ("WORLD_END"): The Imperial Aether-Boiler & Ley-Line will rupture and end the world.
   - Scenario 2 ("SELF_DEATH"): Fate has marked YOU for death through a relentless 7-day Butterfly Effect.
   - Scenario 3 ("LOVED_ONE"): Fate has marked your Loved One/Friend for death (Assassination -> Steam-Carriage
     Crash -> Choking on Food -> Boiler Valve Burst -> Nightshade Tincture -> Gargoyle Collapse -> Final Reckoning).
2. SOLE-KNOWER ISOLATION:
   - You choose 1 of the 4 members of the Ashford-Mercer Family (Arthur, Elena, Maya, Leo).
   - ONLY the character you play as remembers the loops and knows the impending doom! Even your own family
     members are oblivious humans living their daily lives.
3. NON-REPETITIVE BUTTERFLY ENGINE:
   - Protecting the target for an entire 7-Day Week (Monday to Sunday) is required to break Fate's hold.
   - Every intervention mutates the causal web for the next day, and every loop permutes catalysts, moods,
     and conversational tells so the game can NEVER be 'solved' by rote memorization.
"""

import os
import json

SCREEN_WIDTH = 1360
SCREEN_HEIGHT = 860
FPS = 60
TITLE = "CHRONICLES OF DUNWICK (1924) // 7-Day Butterfly-Effect Time-Loop RPG"

# Spacious 2.5D Borough of Dunwick-on-Severn
WORLD_WIDTH = 2600
WORLD_HEIGHT = 1800

# Each day of the 7-day week runs a 90-second afternoon/evening crisis window (or press [G] once foiled!)
DAY_DURATION_SECONDS = 95.0
LOOP_DURATION_SECONDS = DAY_DURATION_SECONDS  # Alias for compatibility
TOTAL_DAYS_IN_WEEK = 7

WEEK_DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_config.json")
SETTINGS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings_config.json")

DEFAULT_SETTINGS = {
    "display_mode": "FULLSCREEN",
    "menu_background": "DUNWICK_MARKET",
    "darkness_vignette": "BLOODBORNE_DARK",
    "atmospheric_particles": True,
    "target_fps": 60,
    "master_volume": 80,
    "sfx_volume": 75,
    "ambient_bells": True,
    "typewriter_speed": "NORMAL",
    "camera_smoothing": "SMOOTH",
    "lethal_traffic": True,
    "ai_provider": "gemini",
}

# 1920s British Medieval-Steampunk Palette (Gaslight Amber, Tarnished Brass, Prussian Velvet, Cobblestone Slate)
COLORS = {
    "grass": (62, 104, 64),
    "grass_patch": (50, 88, 54),
    "road": (68, 66, 72),
    "road_line": (218, 178, 82),
    "sidewalk": (168, 160, 148),
    "water": (58, 138, 178),
    "ui_dark": (16, 18, 26),
    "ui_panel": (24, 26, 38),
    "ui_card": (34, 36, 52),
    "ui_border": (218, 172, 78),
    "ui_border_soft": (102, 92, 78),
    "gold": (242, 198, 82),
    "brass": (208, 154, 62),
    "cyan": (105, 218, 235),
    "green": (92, 222, 142),
    "red": (238, 82, 82),
    "crimson": (175, 42, 52),
    "blood_dark": (28, 8, 12),
    "blood_crimson": (142, 28, 38),
    "blood_bright": (195, 38, 48),
    "gothic_charcoal": (10, 11, 15),
    "gothic_slate": (16, 18, 24),
    "gothic_panel": (22, 25, 34),
    "gothic_border": (74, 68, 62),
    "purple": (185, 128, 242),
    "white": (245, 240, 228),
    "parchment": (236, 224, 198),
    "text_dim": (188, 182, 170),
    "text_muted": (128, 122, 114),
}


def load_llm_config():
    default_cfg = {
        "provider": "gemini",
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
        "gemini_model": "gemini-2.5-flash",
        "openai_model": "gpt-4o-mini",
    }
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
                for k, v in saved.items():
                    if v:
                        default_cfg[k] = v
        except Exception:
            pass
    if default_cfg["openai_api_key"] and not default_cfg["gemini_api_key"]:
        default_cfg["provider"] = "openai"
    return default_cfg


def save_llm_config(cfg):
    try:
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# ==============================================================================
# THE 3 FATE SCENARIOS (Selectable Game Modes)
# ==============================================================================
SCENARIO_MODES = {
    "WORLD_END": {
        "id": "WORLD_END",
        "short_title": "SCENARIO I: THE DOOMSDAY CLOCK",
        "subtitle": "The World Is Going to End",
        "badge_color": (238, 82, 82),
        "summary": (
            "Beneath the medieval cobbles of Dunwick-on-Severn, the High-Pressure Central Steam-Boiler "
            "and Municipal Coal-Gas Network is fated to rupture, demolishing the borough and collapsing "
            "the Town Clocktower. ONLY YOU remember the cataclysm. Every time you avert one mechanical "
            "or structural trigger, the Butterfly Effect shifts the strain across all 7 days of the week."
        ),
        "victory_condition": "Prevent the High-Pressure Boiler Cataclysm across all 7 Days (Monday through Sunday).",
    },
    "SELF_DEATH": {
        "id": "SELF_DEATH",
        "short_title": "SCENARIO II: THE GRIM DECREE",
        "subtitle": "You Are Going to Die",
        "badge_color": (185, 128, 242),
        "summary": (
            "You witnessed your own death in a clockwork premonition. Predetermined Fate has marked YOU "
            "to die. If you dodge a poisoned cup of Earl Grey on Monday, Fate swerves a runaway steam-lorry "
            "at you on Tuesday, drops a medieval stone gargoyle on Wednesday, or arcs a galvanic coil on "
            "Thursday. Outwit Destiny for 7 consecutive days to shatter your death mark!"
        ),
        "victory_condition": "Defy your predetermined death across all 7 Days without losing your life or sanity.",
    },
    "LOVED_ONE": {
        "id": "LOVED_ONE",
        "short_title": "SCENARIO III: THE THREAD OF FATE",
        "subtitle": "Your Loved One Is Going to Die",
        "badge_color": (105, 218, 235),
        "summary": (
            "Someone you love deeply is marked by Fate to die this week. Save them from an assassination on "
            "Monday, and the Butterfly Effect puts them in the path of a runaway steam-carriage crash on "
            "Tuesday; save them from that, and they may choke and suffocate on a plate of spiced mutton pie "
            "on Wednesday! Protect them across an entire 7-day week without making them think you are mad."
        ),
        "victory_condition": "Keep your Loved One alive across all 7 Days as Fate escalates its Butterfly chain.",
    },
}

# Default Loved One mapping per protagonist for Scenario 3 (each family member protects someone dear to them)
PROTAGONIST_LOVED_ONE = {
    "arthur": {
        "target_id": "elena",
        "relation": "Your Beloved Wife, Lady Elena",
        "bond_desc": "Elena's fearless Fleet Street inquiries have placed her in the crosshairs of Fate.",
    },
    "elena": {
        "target_id": "leo",
        "relation": "Your Youngest Son, Leo (11)",
        "bond_desc": "Leo's reckless curiosity across the cobblestones of Dunwick draws lethal danger at every turn.",
    },
    "maya": {
        "target_id": "chloe",
        "relation": "Your Best Friend & Lab Partner, Chloe",
        "bond_desc": "Chloe shares every afternoon with you between St. Dunstan's Polytechnic and the Brass Kettle.",
    },
    "leo": {
        "target_id": "maya",
        "relation": "Your Older Sister, Maya (17)",
        "bond_desc": "Maya always looks out for you—now only you saw the vision of her untimely demise.",
    },
}


# ==============================================================================
# 6 MEDIEVAL-STEAMPUNK 1920s BRITISH BOROUGH LANDMARKS
# ==============================================================================
BUILDINGS = [
    {
        "id": "home",
        "name": "ASHFORD-MERCER TUDOR MANOR",
        "rect": (120, 120, 660, 620),
        "floor_color": (198, 168, 132),
        "roof_color": (148, 58, 48),
        "door_x": 450,
        "door_y": 740,
        "furniture": [
            {"rect": (160, 190, 220, 60), "color": (122, 78, 48), "name": "Victorian Coal-Range & Pantry"},
            {"rect": (480, 200, 220, 95), "color": (118, 48, 58), "name": "Chesterfield Parlour Sofa"},
            {"rect": (160, 480, 180, 110), "color": (96, 76, 58), "name": "Brass Orrery & Study Desk"},
        ],
    },
    {
        "id": "cafe",
        "name": "THE BRASS KETTLE TEAHOUSE",
        "rect": (960, 120, 660, 620),
        "floor_color": (218, 198, 178),
        "roof_color": (168, 72, 88),
        "door_x": 1290,
        "door_y": 740,
        "furniture": [
            {"rect": (1020, 190, 360, 65), "color": (164, 92, 58), "name": "Copper Steam-Urn & Tea Bar"},
            {"rect": (1040, 380, 110, 90), "color": (152, 108, 72), "name": "Teahouse Table 1"},
            {"rect": (1360, 380, 110, 90), "color": (152, 108, 72), "name": "Teahouse Table 2"},
        ],
    },
    {
        "id": "office",
        "name": "BOROUGH FOUNDRY & CLOCKTOWER",
        "rect": (1800, 120, 680, 620),
        "floor_color": (168, 174, 184),
        "roof_color": (58, 78, 112),
        "door_x": 2140,
        "door_y": 740,
        "furniture": [
            {"rect": (1850, 200, 220, 65), "color": (92, 82, 68), "name": "Chancery Pneumatic Desk"},
            {"rect": (1850, 420, 200, 80), "color": (78, 68, 58), "name": "Lord Architect's Drafting Desk"},
            {"rect": (2180, 190, 250, 340), "color": (64, 58, 54), "name": "Central Steam-Boiler & Pumping Engine"},
        ],
    },
    {
        "id": "school",
        "name": "ST. DUNSTAN'S POLYTECHNIC",
        "rect": (120, 1020, 660, 660),
        "floor_color": (186, 182, 172),
        "roof_color": (68, 104, 128),
        "door_x": 450,
        "door_y": 1020,
        "furniture": [
            {"rect": (160, 1120, 240, 110), "color": (68, 118, 114), "name": "Galvanic & Alchemical Bench"},
            {"rect": (480, 1120, 240, 110), "color": (132, 98, 68), "name": "Collegiate Lecture Hall"},
            {"rect": (200, 1420, 460, 160), "color": (158, 128, 92), "name": "School Gym Court (Fencing Yard)"},
        ],
    },
    {
        "id": "market",
        "name": "GUILDHALL BAZAAR & APOTHECARY",
        "rect": (960, 1020, 660, 660),
        "floor_color": (202, 184, 156),
        "roof_color": (188, 124, 48),
        "door_x": 1290,
        "door_y": 1020,
        "furniture": [
            {"rect": (1010, 1120, 230, 75), "color": (168, 112, 54), "name": "Clockwork Ironmonger Stall"},
            {"rect": (1320, 1120, 240, 75), "color": (188, 84, 68), "name": "Crown Bakehouse & Pie Stall"},
            {"rect": (1010, 1400, 250, 80), "color": (72, 138, 118), "name": "Apothecary & Tincture Counter"},
        ],
    },
    {
        "id": "park",
        "name": "SEVERN COMMONS & CONSTABULARY",
        "rect": (1800, 1020, 680, 660),
        "floor_color": (72, 118, 74),
        "roof_color": (52, 108, 78),
        "door_x": 2140,
        "door_y": 1020,
        "furniture": [
            {"rect": (1850, 1120, 240, 95), "color": (52, 68, 108), "name": "Scotland Yard Constabulary Desk"},
            {"rect": (2160, 1300, 180, 180), "color": (68, 148, 188), "name": "Medieval Gargoyle Fountain"},
        ],
    },
]

# Alias SECTORS for nav_pathing compatibility
SECTORS = BUILDINGS

# Interactive Steampunk Stations & World Objects
WORLD_OBJECTS = [
    {
        "id": "study_notebook",
        "name": "Ashford Brass Orrery & Chronometer Log",
        "building": "home",
        "x": 250,
        "y": 602,
        "color": (242, 198, 82),
        "desc": "Cross-references family behavioral habits, coal-gas dampers, and the 7-Day Fate Web.",
    },
    {
        "id": "cafe_counter",
        "name": "Brass Kettle Darjeeling & Pie Counter",
        "building": "cafe",
        "x": 1200,
        "y": 272,
        "color": (235, 145, 115),
        "desc": "Pour a Cup of Earl Grey (+18 Rapport / calms nerves) or inspect today's plated meals & teacups.",
    },
    {
        "id": "school_lab_table",
        "name": "St. Dunstan's Galvanic & Alchemical Analyzer",
        "building": "school",
        "x": 280,
        "y": 1248,
        "color": (92, 228, 188),
        "desc": "Synthesizes antidotes, tests chemical/metallurgical traces, and tests grounding switches.",
    },
    {
        "id": "market_ledger",
        "name": "Guildhall Ironmonger & Apothecary Ledger",
        "building": "market",
        "x": 1125,
        "y": 1212,
        "color": (238, 188, 72),
        "desc": "Audits clockwork parts, steam-carriage brake pins, and apothecary tincture bottles.",
    },
    {
        "id": "office_records",
        "name": "Ministry Difference Engine & Valve Manifold",
        "building": "office",
        "x": 1950,
        "y": 282,
        "color": (105, 205, 245),
        "desc": "Regulates borough steam-pressure lines, masonry stress logs, and emergency valve overrides.",
    },
    {
        "id": "police_dispatch",
        "name": "Scotland Yard Telegraph & Warrant Desk",
        "building": "park",
        "x": 1970,
        "y": 1232,
        "color": (95, 165, 255),
        "desc": "Files verified hazard dispatches, cancels forged warrants, and stations Constables on patrol.",
    },
    {
        "id": "power_generator",
        "name": "Central Steam-Boiler & Clocktower Regulator",
        "building": "office",
        "x": 2305,
        "y": 542,
        "color": (238, 88, 82),
        "desc": "The beating industrial heart of Dunwick-on-Severn! Regulates central steam pressure & town clockwork gears.",
    },
]

# ==============================================================================
# STARTING LORE & PROTAGONIST PROLOGUES (Medieval-Steampunk 1924 Britain)
# ==============================================================================
TOWN_LORE_PROLOGUE = [
    "DUNWICK-ON-SEVERN, ANNO DOMINI 1924 — THE CLOCKWORK BOROUGH:",
    "Built atop a 14th-century Norman abbey and walled market square, the British borough of",
    "Dunwick-on-Severn hums with 1920s brass steam-carriages, pneumatic telegraphs, and the",
    "towering Central Steam-Boiler beneath the Clocktower Foundry.",
    "",
    "Last night, as the Clocktower struck the seventh bell, a violent crimson fissure tore across",
    "the sky—and you awoke back on MONDAY MORNING. Whether Fate has decreed the end of the world,",
    "your own demise, or the death of someone you love, one terrifying law governs this loop:",
    "",
    "ONLY YOU REMEMBER. Even the other three members of your own family are completely unaware.",
    "And Fate is relentless: every time you foil one catastrophe, the Butterfly Effect twists your",
    "intervention into a new lethal hazard the next day. Survive all 7 Days (Monday–Sunday) to win!",
]

FAMILY_LORE_PROLOGUES = {
    "arthur": {
        "headline": "LORD ARTHUR MERCER-ASHFORD (FATHER) — CHIEF CLOCKWORK ARCHITECT",
        "story": (
            "As Senior Fellow of the Royal Mint Foundry, you designed Dunwick's pressurized brass manifolds "
            "and steam-lock regulators. Nobody else in Ashford Manor knows why you woke up drenched in cold "
            "sweat with a vision of impending ruin. Ministry officials, engineers, and Chief Inspector Miller "
            "respect your rank—use your mechanical mastery and quiet dignity to outmaneuver Fate."
        ),
        "specialty": "Ministry Authority & Mechanical Mastery: +20 Rapport with Chancery, Engineers & Police; can override steam-manifolds directly.",
    },
    "elena": {
        "headline": "LADY ELENA MERCER-ASHFORD (MOTHER) — FLEET STREET INVESTIGATOR",
        "story": (
            "A seasoned investigative columnist for the Dunwick Chronicle, you possess an uncanny eye for "
            "human micro-expressions, nervous habits, and whispered rumors in the Brass Kettle Teahouse. "
            "You alone carry the burden of the temporal vision. Because townsfolk confide their daily "
            "troubles in you, you can subtly redirect their routines before Fate's trap snaps shut."
        ),
        "specialty": "Human Insight & Social Persuasion: +20 Rapport at Teahouse & Bazaar; uncovers hidden human behavioral tells on the first ask.",
    },
    "maya": {
        "headline": "MAYA MERCER-ASHFORD (ELDEST DAUGHTER, 17) — ALCHEMICAL PRODIGY",
        "story": (
            "While calibrating an electrical induction coil at St. Dunstan's Polytechnic, your mind was seared with "
            "a vision of the week's tragedy. Neither your parents nor little Leo suspect a thing. You can "
            "detect chemical poisons, neutralize electrical surges, and analyze mechanical stress at the "
            "Polytechnic Lab—though pompous officials will dismiss you unless you bring irrefutable proof."
        ),
        "specialty": "Alchemical & Electrical Genius: Instant Lab synthesis, poison/metallurgy detection & +20 Rapport with Scholars/Chemists.",
    },
    "leo": {
        "headline": "LEO MERCER-ASHFORD (YOUNGEST SON, 11) — COBBLESTONE SCOUT",
        "story": (
            "In 1924 Dunwick, grown-ups rarely notice an eleven-year-old boy in a flat cap darting past "
            "steam-lorries and market barrels. You alone saw the vision of doom! Because no adult will "
            "believe a child's dire warnings, you must rely on your 25% faster speed, eavesdropping on "
            "unfiltered adult conversations, and physically tampering with hazards before they strike."
        ),
        "specialty": "Fleet-Footed Eavesdropper: 25% Faster Speed, overhears unguarded adult secrets & slips past mechanical hazards.",
    },
}

# ==============================================================================
# 24 NAMED CHARACTERS (4 Ashford-Mercer Family + 20 1920s British Borough NPCs)
# ==============================================================================
CHARACTER_SPECS = [
    # --- THE 4 ASHFORD-MERCER FAMILY MEMBERS (Only the chosen one knows!) ---
    {
        "id": "arthur",
        "name": "Lord Arthur (Father)",
        "role": "Chief Clockwork Architect",
        "is_family": True,
        "building": "home",
        "x": 380,
        "y": 340,
        "shirt": (58, 98, 152),
        "pants": (38, 44, 58),
        "hair": (72, 50, 36),
        "skin": (245, 212, 188),
        "accessory": "glasses_tie",
        "scale": 1.05,
        "perk": "Commands Ministry & Police respect; masters steam & clockwork mechanisms.",
        "bio": "Distinguished 1920s clockwork architect. Habits: Takes afternoon Darjeeling and inspects the Foundry gauges.",
    },
    {
        "id": "elena",
        "name": "Lady Elena (Mother)",
        "role": "Chronicle Investigative Writer",
        "is_family": True,
        "building": "home",
        "x": 540,
        "y": 340,
        "shirt": (178, 68, 98),
        "pants": (58, 44, 62),
        "hair": (122, 52, 34),
        "skin": (248, 216, 192),
        "accessory": "scarf",
        "scale": 1.0,
        "perk": "Reads human behavioral tells & persuades townsfolk to alter their daily routines.",
        "bio": "Sharp-witted Fleet Street journalist. Habits: Interviews patrons at the Brass Kettle and browses the Bazaar.",
    },
    {
        "id": "maya",
        "name": "Maya (Sister, 17)",
        "role": "St. Dunstan's Alchemical Scholar",
        "is_family": True,
        "building": "school",
        "x": 340,
        "y": 1310,
        "shirt": (52, 158, 148),
        "pants": (42, 54, 72),
        "hair": (42, 34, 52),
        "skin": (245, 212, 188),
        "accessory": "headphones",
        "scale": 0.95,
        "perk": "Analyzes poisons, metallurgy & galvanic surges; crafts Aether-Tuning charges.",
        "bio": "Brilliant 17-year-old alchemical & galvanic scholar. Habits: Experiments in St. Dunstan's Lab with Chloe.",
    },
    {
        "id": "leo",
        "name": "Leo (Brother, 11)",
        "role": "Cobblestone Urchin & Scout",
        "is_family": True,
        "building": "school",
        "x": 520,
        "y": 1480,
        "shirt": (88, 158, 82),
        "pants": (52, 66, 82),
        "hair": (95, 65, 42),
        "skin": (245, 212, 188),
        "accessory": "cap",
        "scale": 0.82,
        "perk": "Runs 25% faster, eavesdrops on unguarded adults & spots street-level traps.",
        "bio": "Quick-footed 11-year-old brother in a tweed flat cap. Habits: Races along High Street and the Gargoyle Fountain.",
    },
    # --- 20 LIVELY 1920s BRITISH BOROUGH NPCS ---
    {
        "id": "sal",
        "name": "Proprietor Sal",
        "role": "Master of The Brass Kettle Teahouse",
        "is_family": False,
        "building": "cafe",
        "x": 1150,
        "y": 310,
        "shirt": (188, 118, 58),
        "pants": (68, 50, 38),
        "hair": (55, 42, 35),
        "skin": (235, 198, 172),
        "accessory": "apron",
        "scale": 1.02,
        "bio": "Brews Darjeeling and spiced espresso from a pressurized copper urn; hears every whisper in Dunwick.",
    },
    {
        "id": "mia",
        "name": "Parlourmaid Mia",
        "role": "Teahouse Server",
        "is_family": False,
        "building": "cafe",
        "x": 1255,
        "y": 435,
        "shirt": (212, 112, 138),
        "pants": (56, 46, 62),
        "hair": (215, 165, 75),
        "skin": (248, 218, 195),
        "accessory": "apron",
        "scale": 0.96,
        "bio": "Attentive server who notices who tampers with teacups, who eats too quickly, and who loiters by the window.",
    },
    {
        "id": "jenkins",
        "name": "Horologist Jenkins",
        "role": "Retired Guild Watchmaker",
        "is_family": False,
        "building": "cafe",
        "x": 1060,
        "y": 510,
        "shirt": (132, 118, 98),
        "pants": (66, 62, 56),
        "hair": (210, 212, 218),
        "skin": (238, 205, 182),
        "accessory": "glasses_tie",
        "scale": 0.98,
        "bio": "Adjusts his brass pocket-chronometer by the Teahouse window and logs every steam-carriage on High Street.",
    },
    {
        "id": "mayor",
        "name": "Lord Mayor Thornton",
        "role": "Lord Mayor of Dunwick-on-Severn",
        "is_family": False,
        "building": "cafe",
        "x": 1490,
        "y": 340,
        "shirt": (135, 78, 168),
        "pants": (46, 40, 58),
        "hair": (185, 185, 195),
        "skin": (242, 208, 185),
        "accessory": "glasses_tie",
        "scale": 1.05,
        "bio": "Pompous Edwardian magistrate who values decorum and official seals above all else.",
    },
    {
        "id": "sam",
        "name": "Ironmonger Sam",
        "role": "Guildhall Brass & Toolsmith",
        "is_family": False,
        "building": "market",
        "x": 1120,
        "y": 1270,
        "shirt": (185, 122, 52),
        "pants": (58, 66, 82),
        "hair": (85, 55, 38),
        "skin": (225, 185, 155),
        "accessory": "cap",
        "scale": 1.03,
        "bio": "Forges brass valves, brake cotter-pins, and clockwork spanners at the Guildhall Bazaar.",
    },
    {
        "id": "martha",
        "name": "Mistress Martha",
        "role": "Crown Bakehouse Matron",
        "is_family": False,
        "building": "market",
        "x": 1440,
        "y": 1260,
        "shirt": (205, 98, 78),
        "pants": (78, 56, 50),
        "hair": (165, 95, 65),
        "skin": (245, 212, 188),
        "accessory": "apron",
        "scale": 1.0,
        "bio": "Bakes thick-crusted mutton pies, plum tarts, and crumpets for the Teahouse and Bazaar.",
    },
    {
        "id": "lin",
        "name": "Apothecary Lin",
        "role": "Master of Tinctures & Remedies",
        "is_family": False,
        "building": "market",
        "x": 1140,
        "y": 1520,
        "shirt": (62, 158, 142),
        "pants": (48, 60, 68),
        "hair": (35, 35, 42),
        "skin": (245, 218, 195),
        "accessory": "glasses_tie",
        "scale": 0.98,
        "bio": "Compounds laudanum, smelling salts, and belladonna tinctures; keeps a strict poison register.",
    },
    {
        "id": "zack",
        "name": "Steam-Driver Zack",
        "role": "Royal Parcel & Lorry Driver",
        "is_family": False,
        "building": "market",
        "x": 1460,
        "y": 1500,
        "shirt": (78, 138, 188),
        "pants": (52, 58, 72),
        "hair": (110, 75, 45),
        "skin": (238, 205, 180),
        "accessory": "cap",
        "scale": 1.0,
        "bio": "Hauls pressurized coal-cylinders and heavy crates along High Street in his brass steam-lorry.",
    },
    {
        "id": "clarke",
        "name": "Professor Clarke",
        "role": "Chair of Natural Philosophy",
        "is_family": False,
        "building": "school",
        "x": 240,
        "y": 1290,
        "shirt": (68, 142, 162),
        "pants": (52, 56, 68),
        "hair": (95, 72, 55),
        "skin": (242, 210, 185),
        "accessory": "glasses_tie",
        "scale": 1.04,
        "bio": "Oversees St. Dunstan's Galvanic & Alchemical Lab; mentor to Maya.",
    },
    {
        "id": "higgins",
        "name": "Headmaster Higgins",
        "role": "Provost of St. Dunstan's",
        "is_family": False,
        "building": "school",
        "x": 580,
        "y": 1280,
        "shirt": (108, 82, 142),
        "pants": (46, 42, 58),
        "hair": (155, 155, 165),
        "skin": (238, 202, 178),
        "accessory": "glasses_tie",
        "scale": 1.05,
        "bio": "Strict traditionalist who guards the ancient medieval abbey vaults beneath the Polytechnic.",
    },
    {
        "id": "chloe",
        "name": "Chloe Sterling",
        "role": "Apprentice Alchemist (Maya's Friend)",
        "is_family": False,
        "building": "school",
        "x": 420,
        "y": 1350,
        "shirt": (198, 108, 158),
        "pants": (52, 62, 86),
        "hair": (225, 175, 85),
        "skin": (248, 218, 195),
        "accessory": "headphones",
        "scale": 0.94,
        "bio": "Maya's dearest friend; often rushes between the Galvanic Lab, the Bakehouse, and the Teahouse.",
    },
    {
        "id": "toby",
        "name": "Toby Finch",
        "role": "Choirboy & Street Runner (Leo's Friend)",
        "is_family": False,
        "building": "school",
        "x": 320,
        "y": 1520,
        "shirt": (215, 142, 58),
        "pants": (52, 66, 84),
        "hair": (85, 55, 38),
        "skin": (242, 210, 185),
        "accessory": "cap",
        "scale": 0.82,
        "bio": "Leo's best mate; climbs scaffolding and spots rooftop figures or loose gargoyle stones.",
    },
    {
        "id": "vance",
        "name": "Lord Director Vance",
        "role": "Controller of the Borough Steam-Works",
        "is_family": False,
        "building": "office",
        "x": 1960,
        "y": 480,
        "shirt": (148, 78, 188),
        "pants": (42, 36, 56),
        "hair": (55, 48, 65),
        "skin": (242, 208, 185),
        "accessory": "glasses_tie",
        "scale": 1.05,
        "bio": "Ruthless industrialist pushing the Borough Steam-Boilers to maximum pressure for the Crown.",
    },
    {
        "id": "pam",
        "name": "Clerk Pamela",
        "role": "Chancery Cipher & Telegraphist",
        "is_family": False,
        "building": "office",
        "x": 1950,
        "y": 320,
        "shirt": (82, 162, 188),
        "pants": (50, 56, 72),
        "hair": (175, 85, 65),
        "skin": (248, 218, 195),
        "accessory": "scarf",
        "scale": 0.98,
        "bio": "Logs every pneumatic dispatch tube and visitor passing through the Borough Chancery.",
    },
    {
        "id": "raj",
        "name": "Chief Stoker Raj",
        "role": "Master Steam & Turbine Engineer",
        "is_family": False,
        "building": "office",
        "x": 2250,
        "y": 540,
        "shirt": (68, 138, 195),
        "pants": (46, 54, 68),
        "hair": (32, 32, 38),
        "skin": (198, 152, 118),
        "accessory": "cap",
        "scale": 1.02,
        "bio": "Watches the brass pressure needles on the Borough Steam-Boiler and coal-gas mains.",
    },
    {
        "id": "hank",
        "name": "Warden Hank",
        "role": "Foundry Iron-Gate Yeoman",
        "is_family": False,
        "building": "office",
        "x": 2140,
        "y": 360,
        "shirt": (58, 98, 158),
        "pants": (34, 42, 62),
        "hair": (75, 65, 55),
        "skin": (235, 198, 175),
        "accessory": "cop_hat",
        "scale": 1.06,
        "bio": "Former Royal Sapper who guards the Clocktower Boiler chamber with unwavering discipline.",
    },
    {
        "id": "miller",
        "name": "Chief Inspector Miller",
        "role": "Scotland Yard Borough Inspector",
        "is_family": False,
        "building": "park",
        "x": 1960,
        "y": 1270,
        "shirt": (52, 108, 198),
        "pants": (30, 44, 78),
        "hair": (65, 55, 48),
        "skin": (238, 202, 178),
        "accessory": "cop_hat",
        "scale": 1.05,
        "bio": "Pragmatic detective who demands tangible proof; will detain anyone causing public hysteria.",
    },
    {
        "id": "rosa",
        "name": "Constable Rosa",
        "role": "High Street Beat Constable",
        "is_family": False,
        "building": "street",
        "x": 1290,
        "y": 880,
        "shirt": (52, 108, 198),
        "pants": (30, 44, 78),
        "hair": (42, 32, 38),
        "skin": (222, 182, 152),
        "accessory": "cop_hat",
        "scale": 1.0,
        "bio": "Blows her brass whistle to halt runaway steam-carriages and keeps order on High Street.",
    },
    {
        "id": "joya",
        "name": "Sister Joya",
        "role": "Infirmary & Red Cross Matron",
        "is_family": False,
        "building": "park",
        "x": 2250,
        "y": 1520,
        "shirt": (218, 98, 124),
        "pants": (232, 232, 238),
        "hair": (65, 42, 55),
        "skin": (242, 210, 185),
        "accessory": "scarf",
        "scale": 0.98,
        "bio": "Skilled in the Heimlich maneuver, antidotes, and emergency triage by the Gargoyle Fountain.",
    },
    {
        "id": "dan",
        "name": "Sergeant-Major Dan",
        "role": "Borough Fencing & Athletics Master",
        "is_family": False,
        "building": "street",
        "x": 680,
        "y": 880,
        "shirt": (198, 82, 64),
        "pants": (52, 58, 68),
        "hair": (85, 62, 42),
        "skin": (235, 198, 172),
        "accessory": "cap",
        "scale": 1.05,
        "bio": "Briskly marches along High Street and spots anyone acting out of their daily rhythm.",
    },
]
