"""
Configuration for MAPLEWOOD CHRONICLES:
- Clean, Simple Plain-English Interface (No background image clutter, no missing emoji glyphs)
- Playable Family of 4 (Dad Arthur, Mom Elena, Sister Maya, Brother Leo)
- 20 Lively Neighborhood NPCs (24 total characters across Home, School, Office, Cafe, Market, Park/Police)
- Dynamic 5-Chapter Mystery Progression that changes suspects & codes every campaign!
"""

import os
import json

SCREEN_WIDTH = 1360
SCREEN_HEIGHT = 860
FPS = 60
TITLE = "MAPLEWOOD LOOP // Family Time-Loop Mystery RPG"

# Spacious, uncluttered town dimensions (Camera smoothly follows your character)
WORLD_WIDTH = 2600
WORLD_HEIGHT = 1800

# 4 minutes per loop so you have plenty of time to explore, talk, and investigate across chapters
LOOP_DURATION_SECONDS = 240.0

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_config.json")

COLORS = {
    "grass": (68, 122, 74),
    "grass_patch": (58, 108, 64),
    "road": (72, 76, 86),
    "road_line": (235, 205, 90),
    "sidewalk": (182, 180, 174),
    "water": (75, 165, 225),
    "ui_dark": (18, 22, 32),
    "ui_panel": (26, 32, 46),
    "ui_card": (36, 44, 62),
    "ui_border": (225, 185, 95),
    "ui_border_soft": (90, 108, 140),
    "gold": (255, 215, 75),
    "cyan": (85, 220, 255),
    "green": (80, 230, 140),
    "red": (255, 85, 95),
    "white": (248, 248, 245),
    "text_dim": (185, 192, 208),
    "text_muted": (125, 134, 152),
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
# 6 CLEAN NEIGHBORHOOD BUILDINGS (Connected by Main Street at y=800..980)
# ==============================================================================
BUILDINGS = [
    {
        "id": "home",
        "name": "MERCER FAMILY HOME",
        "rect": (120, 120, 660, 620),
        "floor_color": (225, 198, 162),
        "roof_color": (185, 75, 65),
        "door_x": 450,
        "door_y": 740,
        "furniture": [
            {"rect": (160, 190, 220, 60), "color": (135, 90, 60), "name": "Kitchen Counter"},
            {"rect": (480, 200, 220, 95), "color": (85, 125, 165), "name": "Living Room Sofa"},
            {"rect": (160, 480, 180, 110), "color": (110, 120, 135), "name": "Family Study Desk"},
        ],
    },
    {
        "id": "cafe",
        "name": "SUNRISE CAFE & PARLOR",
        "rect": (960, 120, 660, 620),
        "floor_color": (238, 220, 222),
        "roof_color": (215, 95, 135),
        "door_x": 1290,
        "door_y": 740,
        "furniture": [
            {"rect": (1020, 190, 360, 65), "color": (195, 80, 115), "name": "Coffee & Ice Cream Bar"},
            {"rect": (1040, 380, 110, 90), "color": (215, 175, 145), "name": "Cafe Table 1"},
            {"rect": (1360, 380, 110, 90), "color": (215, 175, 145), "name": "Cafe Table 2"},
        ],
    },
    {
        "id": "office",
        "name": "TOWN OFFICE & POWER ROOM",
        "rect": (1800, 120, 680, 620),
        "floor_color": (188, 202, 218),
        "roof_color": (65, 105, 160),
        "door_x": 2140,
        "door_y": 740,
        "furniture": [
            {"rect": (1850, 200, 220, 65), "color": (85, 105, 135), "name": "Reception Desk"},
            {"rect": (1850, 420, 200, 80), "color": (75, 95, 125), "name": "Dad's Office Desk"},
            {"rect": (2180, 190, 250, 340), "color": (58, 66, 82), "name": "Main Town Power Generator"},
        ],
    },
    {
        "id": "school",
        "name": "MAPLEWOOD HIGH SCHOOL",
        "rect": (120, 1020, 660, 660),
        "floor_color": (205, 215, 222),
        "roof_color": (75, 140, 195),
        "door_x": 450,
        "door_y": 1020,
        "furniture": [
            {"rect": (160, 1120, 240, 110), "color": (75, 135, 150), "name": "Science Lab Bench"},
            {"rect": (480, 1120, 240, 110), "color": (155, 125, 90), "name": "Main Classroom"},
            {"rect": (200, 1420, 460, 160), "color": (185, 125, 80), "name": "School Gym Court"},
        ],
    },
    {
        "id": "market",
        "name": "TOWN MARKET & SHOPS",
        "rect": (960, 1020, 660, 660),
        "floor_color": (218, 205, 182),
        "roof_color": (215, 145, 55),
        "door_x": 1290,
        "door_y": 1020,
        "furniture": [
            {"rect": (1010, 1120, 230, 75), "color": (195, 130, 65), "name": "Hardware & Tools Stall"},
            {"rect": (1320, 1120, 240, 75), "color": (215, 95, 85), "name": "Fresh Bakery Stall"},
            {"rect": (1010, 1400, 250, 80), "color": (85, 165, 145), "name": "Pharmacy & Chemist Counter"},
        ],
    },
    {
        "id": "park",
        "name": "TOWN PARK & POLICE POST",
        "rect": (1800, 1020, 680, 660),
        "floor_color": (82, 142, 88),
        "roof_color": (60, 145, 95),
        "door_x": 2140,
        "door_y": 1020,
        "furniture": [
            {"rect": (1850, 1120, 240, 95), "color": (55, 85, 145), "name": "Police Station Desk"},
            {"rect": (2160, 1300, 180, 180), "color": (75, 175, 230), "name": "Town Park Fountain"},
        ],
    },
]

# Interactive Objects in the Buildings (Placed on accessible front edges for smooth tile interaction)
WORLD_OBJECTS = [
    {
        "id": "study_notebook",
        "name": "Family Research Terminal (Study Desk)",
        "building": "home",
        "x": 250,
        "y": 602,
        "color": (255, 215, 75),
        "desc": "Cross-references family notes on the 5:00 PM - 6:00 PM Aether-Core anomaly.",
    },
    {
        "id": "cafe_counter",
        "name": "Sunrise Cafe Espresso Counter",
        "building": "cafe",
        "x": 1200,
        "y": 272,
        "color": (255, 140, 175),
        "desc": "Pick up a Warm Espresso (+15 Rapport with townspeople when you talk to them!).",
    },
    {
        "id": "school_lab_table",
        "name": "High School Science Scanner",
        "building": "school",
        "x": 280,
        "y": 1248,
        "color": (80, 235, 195),
        "desc": "Analyzes physical/chemical residue & transmits calibration data to the Town Office computer!",
    },
    {
        "id": "market_ledger",
        "name": "Market Hardware & Chemical Register",
        "building": "market",
        "x": 1125,
        "y": 1212,
        "color": (255, 200, 75),
        "desc": "Logs afternoon tool/chemical purchases and flags suspicious serial numbers for Police Dispatch.",
    },
    {
        "id": "office_records",
        "name": "Office Security Mainframe",
        "building": "office",
        "x": 1950,
        "y": 282,
        "color": (90, 205, 255),
        "desc": "Compiles the emergency Generator Shutdown Code once School Lab & Market data are synced.",
    },
    {
        "id": "police_dispatch",
        "name": "Police Evidence & Dispatch Terminal",
        "building": "park",
        "x": 1970,
        "y": 1232,
        "color": (95, 165, 255),
        "desc": "Logs sabotage evidence with Chief Miller and radios Guard Hank at the Power Room.",
    },
    {
        "id": "power_generator",
        "name": "Main Town Power Generator Console",
        "building": "office",
        "x": 2305,
        "y": 542,
        "color": (255, 90, 85),
        "desc": "The Aether-Core Control Console! Requires Police Clearance and the Shutdown Code to disarm.",
    },
]

# ==============================================================================
# STARTING LORE & CHARACTER PROLOGUES (Displayed after Character Selection)
# ==============================================================================
TOWN_LORE_PROLOGUE = [
    "THE ANOMALY OF MAPLEWOOD HEIGHTS (5:00 PM - 6:00 PM):",
    "Beneath the quiet streets of Maplewood Heights hums the experimental Aether-Core Generator—",
    "a high-output municipal reactor housed inside the Town Office Power Room.",
    "",
    "Today at 5:00 PM, the afternoon bells rang across Main Street. Exactly sixty minutes later,",
    "at 6:00 PM, someone secretly sabotaged the Aether-Core. Instead of merely blacking out the",
    "town, the overloaded core fractured local spacetime—rewinding every street, vehicle, and",
    "resident back to 5:00 PM sharp.",
    "",
    "Only the four members of the Mercer Family—connected by Arthur's home diagnostic receiver",
    "and Maya's temporal resonance coil—retain their awareness across loops. Everyone else in town",
    "is living out their normal 5:00 PM to 6:00 PM routine, completely unaware that the world",
    "ends at the top of the hour.",
]

FAMILY_LORE_PROLOGUES = {
    "arthur": {
        "headline": "ARTHUR MERCER (DAD) — THE ARCHITECT'S BURDEN",
        "story": (
            "You helped design the Aether-Core's safety interlocks three years ago, though Director Vance "
            "overruled your warnings about manual bypass relays. When the 6:00 PM flash consumed the sky, "
            "you woke up standing in your living room at 5:00 PM with the blueprint hum still ringing in "
            "your ears. Office staff, engineers, and Police Chief Miller respect your authority—use that "
            "access to uncover who is tampering with your life's work."
        ),
        "specialty": "Official Authority: +20 Starting Rapport with Town Office staff, Engineers, and Police.",
    },
    "elena": {
        "headline": "ELENA MERCER (MOM) — THE REPORTER'S INSTINCT",
        "story": (
            "As lead investigative journalist for the Maplewood Gazette, you spent the past week tracking "
            "rumors of off-the-books shipments arriving at the Town Market. Seconds before the 6:00 PM "
            "detonation, you glimpsed a shadowy figure slipping out of the Town Office alley. Shopkeepers, "
            "waitstaff, and cafe regulars trust you—if someone saw an unusual face or sold a restricted component "
            "this afternoon, they will tell you first."
        ),
        "specialty": "Press Rapport: +20 Starting Rapport with Sunrise Cafe & Town Market residents.",
    },
    "maya": {
        "headline": "MAYA MERCER (SISTER, 17) — THE SCIENCE PRODIGY",
        "story": (
            "You were calibrating your robotics frequency scanner in the Maplewood High Science Lab when "
            "the 6:00 PM shockwave hit. Your homemade coil absorbed a fraction of the chronos pulse, "
            "anchoring our entire family's memories across time loops! You can operate the High School "
            "Science Scanner to analyze chemical/electronic traces and synthesize extra Deja-Vu pulses."
        ),
        "specialty": "Lab Mastery: Instant Science Scanner calibration & +20 Rapport with School/Tech peers.",
    },
    "leo": {
        "headline": "LEO MERCER (BROTHER, 11) — THE STREET SCOUT",
        "story": (
            "Nobody pays attention to an eleven-year-old kid on sneakers—and that is your biggest weapon. "
            "You were racing Toby near the schoolyard when the sky turned violet at 6:00 PM. You move 25% "
            "faster than any adult in Maplewood, making you the best choice for shadowing suspects as they "
            "walk between the Market, the Cafe, and the Power Room before 6:00 PM."
        ),
        "specialty": "Fleet Footed: 25% Faster Movement Speed & +20 Rapport with Street/Park locals.",
    },
}

# ==============================================================================
# 24 NAMED CHARACTERS (4 Playable Family Members + 20 Lively Town NPCs!)
# ==============================================================================
CHARACTER_SPECS = [
    # --- PLAYABLE FAMILY OF 4 ---
    {
        "id": "arthur",
        "name": "Arthur Mercer (Dad)",
        "role": "Playable Dad — Systems Architect",
        "is_family": True,
        "building": "home",
        "x": 380,
        "y": 340,
        "shirt": (65, 135, 225),
        "pants": (40, 52, 75),
        "hair": (75, 52, 38),
        "skin": (245, 212, 188),
        "accessory": "glasses_tie",
        "scale": 1.05,
        "perk": "Respected by Police & Office Staff; knows the Town Office layout.",
        "bio": "Loving father of Maya & Leo. Works at the Town Office.",
    },
    {
        "id": "elena",
        "name": "Elena Mercer (Mom)",
        "role": "Playable Mom — Town Reporter",
        "is_family": True,
        "building": "home",
        "x": 540,
        "y": 340,
        "shirt": (225, 95, 145),
        "pants": (65, 48, 72),
        "hair": (125, 55, 35),
        "skin": (248, 216, 192),
        "accessory": "scarf",
        "scale": 1.0,
        "perk": "Everyone in town trusts her; people share secrets on the first ask!",
        "bio": "Investigative reporter for the Maplewood Gazette and devoted mom.",
    },
    {
        "id": "maya",
        "name": "Maya Mercer (Sister, 17)",
        "role": "Playable Sister — High School Whiz",
        "is_family": True,
        "building": "school",
        "x": 340,
        "y": 1310,
        "shirt": (55, 205, 185),
        "pants": (45, 62, 85),
        "hair": (42, 34, 52),
        "skin": (245, 212, 188),
        "accessory": "headphones",
        "scale": 0.95,
        "perk": "Can analyze clues at the School Science Lab & craft Deja-Vu charges!",
        "bio": "17-year-old science & robotics star at Maplewood High.",
    },
    {
        "id": "leo",
        "name": "Leo Mercer (Brother, 11)",
        "role": "Playable Brother — Fast Kid Scout",
        "is_family": True,
        "building": "school",
        "x": 520,
        "y": 1480,
        "shirt": (95, 210, 110),
        "pants": (52, 75, 95),
        "hair": (95, 65, 42),
        "skin": (245, 212, 188),
        "accessory": "cap",
        "scale": 0.82,
        "perk": "Runs 25% faster than everyone else & overhears clues kids notice!",
        "bio": "Energetic 11-year-old brother who knows every shortcut in town.",
    },
    # --- 20 LIVELY NEIGHBORHOOD NPCS ---
    # Cafe & Parlor NPCs (4)
    {
        "id": "sal",
        "name": "Barista Sal",
        "role": "Owner of Sunrise Cafe",
        "is_family": False,
        "building": "cafe",
        "x": 1150,
        "y": 310,
        "shirt": (235, 155, 75),
        "pants": (75, 55, 42),
        "hair": (55, 42, 35),
        "skin": (235, 198, 172),
        "accessory": "apron",
        "scale": 1.02,
        "bio": "Serves coffee to the whole town and hears every rumor.",
    },
    {
        "id": "mia",
        "name": "Waitress Mia",
        "role": "Cafe Server",
        "is_family": False,
        "building": "cafe",
        "x": 1255,
        "y": 435,
        "shirt": (245, 135, 165),
        "pants": (60, 50, 68),
        "hair": (215, 165, 75),
        "skin": (248, 218, 195),
        "accessory": "apron",
        "scale": 0.96,
        "bio": "Saw a nervous customer drop a strange note near Table 2.",
    },
    {
        "id": "jenkins",
        "name": "Old Man Jenkins",
        "role": "Retired Watchmaker",
        "is_family": False,
        "building": "cafe",
        "x": 1060,
        "y": 510,
        "shirt": (145, 135, 115),
        "pants": (70, 68, 62),
        "hair": (210, 212, 218),
        "skin": (238, 205, 182),
        "accessory": "glasses_tie",
        "scale": 0.98,
        "bio": "Watches the street all afternoon from his favorite cafe table.",
    },
    {
        "id": "mayor",
        "name": "Mayor Thornton",
        "role": "Mayor of Maplewood",
        "is_family": False,
        "building": "cafe",
        "x": 1490,
        "y": 340,
        "shirt": (155, 95, 215),
        "pants": (48, 42, 65),
        "hair": (185, 185, 195),
        "skin": (242, 208, 185),
        "accessory": "glasses_tie",
        "scale": 1.05,
        "bio": "Can order the Police and Town Office to open the Power Room.",
    },
    # Market & Shops NPCs (4)
    {
        "id": "sam",
        "name": "Shopkeeper Sam",
        "role": "Hardware Store Owner",
        "is_family": False,
        "building": "market",
        "x": 1120,
        "y": 1270,
        "shirt": (215, 145, 65),
        "pants": (65, 75, 95),
        "hair": (85, 55, 38),
        "skin": (225, 185, 155),
        "accessory": "cap",
        "scale": 1.03,
        "bio": "Keeps the sales register of everyone who bought tools today.",
    },
    {
        "id": "martha",
        "name": "Baker Martha",
        "role": "Market Pastry Chef",
        "is_family": False,
        "building": "market",
        "x": 1440,
        "y": 1260,
        "shirt": (235, 115, 95),
        "pants": (85, 60, 55),
        "hair": (165, 95, 65),
        "skin": (245, 212, 188),
        "accessory": "apron",
        "scale": 1.0,
        "bio": "Friendly baker who knows all the families in Maplewood.",
    },
    {
        "id": "lin",
        "name": "Pharmacist Lin",
        "role": "Town Chemist",
        "is_family": False,
        "building": "market",
        "x": 1140,
        "y": 1520,
        "shirt": (75, 195, 175),
        "pants": (50, 65, 75),
        "hair": (35, 35, 42),
        "skin": (245, 218, 195),
        "accessory": "glasses_tie",
        "scale": 0.98,
        "bio": "Noticed someone ordering industrial cooling acid this afternoon.",
    },
    {
        "id": "zack",
        "name": "Courier Zack",
        "role": "Express Delivery Driver",
        "is_family": False,
        "building": "market",
        "x": 1460,
        "y": 1500,
        "shirt": (95, 175, 235),
        "pants": (55, 62, 78),
        "hair": (110, 75, 45),
        "skin": (238, 205, 180),
        "accessory": "cap",
        "scale": 1.0,
        "bio": "Delivers crates between the Market and the Town Office.",
    },
    # High School NPCs (4)
    {
        "id": "clarke",
        "name": "Mr. Clarke",
        "role": "High School Science Teacher",
        "is_family": False,
        "building": "school",
        "x": 240,
        "y": 1290,
        "shirt": (75, 175, 195),
        "pants": (55, 60, 72),
        "hair": (95, 72, 55),
        "skin": (242, 210, 185),
        "accessory": "glasses_tie",
        "scale": 1.04,
        "bio": "Helps Maya and Leo run tests on the Science Lab Scanner.",
    },
    {
        "id": "higgins",
        "name": "Principal Higgins",
        "role": "High School Principal",
        "is_family": False,
        "building": "school",
        "x": 580,
        "y": 1280,
        "shirt": (125, 95, 165),
        "pants": (48, 45, 62),
        "hair": (155, 155, 165),
        "skin": (238, 202, 178),
        "accessory": "glasses_tie",
        "scale": 1.05,
        "bio": "Keeps strict order at Maplewood High.",
    },
    {
        "id": "chloe",
        "name": "Chloe (Student)",
        "role": "Maya's Best Friend",
        "is_family": False,
        "building": "school",
        "x": 420,
        "y": 1350,
        "shirt": (235, 130, 195),
        "pants": (55, 68, 95),
        "hair": (225, 175, 85),
        "skin": (248, 218, 195),
        "accessory": "headphones",
        "scale": 0.94,
        "bio": "Studies robotics with Maya and saw someone near the power shed.",
    },
    {
        "id": "toby",
        "name": "Toby (Kid Student)",
        "role": "Leo's Classmate",
        "is_family": False,
        "building": "school",
        "x": 320,
        "y": 1520,
        "shirt": (245, 165, 65),
        "pants": (55, 72, 92),
        "hair": (85, 55, 38),
        "skin": (242, 210, 185),
        "accessory": "cap",
        "scale": 0.82,
        "bio": "Plays basketball with Leo and trades neighborhood clues.",
    },
    # Town Office & Power Room NPCs (4)
    {
        "id": "vance",
        "name": "Director Vance",
        "role": "Dad's Boss at Town Office",
        "is_family": False,
        "building": "office",
        "x": 1960,
        "y": 480,
        "shirt": (185, 95, 235),
        "pants": (45, 38, 62),
        "hair": (55, 48, 65),
        "skin": (242, 208, 185),
        "accessory": "glasses_tie",
        "scale": 1.05,
        "bio": "Refuses to shut off the 6:00 PM Power Test until shown hard proof.",
    },
    {
        "id": "pam",
        "name": "Secretary Pam",
        "role": "Office Receptionist",
        "is_family": False,
        "building": "office",
        "x": 1950,
        "y": 320,
        "shirt": (95, 195, 225),
        "pants": (52, 60, 78),
        "hair": (175, 85, 65),
        "skin": (248, 218, 195),
        "accessory": "scarf",
        "scale": 0.98,
        "bio": "Keeps the visitor log at the Town Office reception desk.",
    },
    {
        "id": "raj",
        "name": "Engineer Raj",
        "role": "Power Grid Technician",
        "is_family": False,
        "building": "office",
        "x": 2250,
        "y": 540,
        "shirt": (75, 165, 235),
        "pants": (48, 58, 75),
        "hair": (32, 32, 38),
        "skin": (198, 152, 118),
        "accessory": "cap",
        "scale": 1.02,
        "bio": "Monitors the Main Town Power Generator gauges.",
    },
    {
        "id": "hank",
        "name": "Guard Hank",
        "role": "Power Room Security Guard",
        "is_family": False,
        "building": "office",
        "x": 2140,
        "y": 360,
        "shirt": (65, 115, 185),
        "pants": (35, 45, 68),
        "hair": (75, 65, 55),
        "skin": (235, 198, 175),
        "accessory": "cop_hat",
        "scale": 1.06,
        "bio": "Guards the Main Power Generator. Only lets authorized people disarm it.",
    },
    # Park, Police & Main Street NPCs (4)
    {
        "id": "miller",
        "name": "Chief Miller (Police)",
        "role": "Town Police Chief",
        "is_family": False,
        "building": "park",
        "x": 1960,
        "y": 1270,
        "shirt": (65, 135, 245),
        "pants": (32, 48, 85),
        "hair": (65, 55, 48),
        "skin": (238, 202, 178),
        "accessory": "cop_hat",
        "scale": 1.05,
        "bio": "Arrests the Saboteur once you complete the investigation chapters!",
    },
    {
        "id": "rosa",
        "name": "Officer Rosa",
        "role": "Street Patrol Officer",
        "is_family": False,
        "building": "street",
        "x": 1290,
        "y": 880,
        "shirt": (65, 135, 245),
        "pants": (32, 48, 85),
        "hair": (42, 32, 38),
        "skin": (222, 182, 152),
        "accessory": "cop_hat",
        "scale": 1.0,
        "bio": "Patrols Main Street between the Cafe, Market, and Park.",
    },
    {
        "id": "joya",
        "name": "Nurse Joya",
        "role": "Park First-Aid Nurse",
        "is_family": False,
        "building": "park",
        "x": 2250,
        "y": 1520,
        "shirt": (245, 115, 145),
        "pants": (235, 238, 245),
        "hair": (65, 42, 55),
        "skin": (242, 210, 185),
        "accessory": "scarf",
        "scale": 0.98,
        "bio": "Looks after kids and families in the Town Park.",
    },
    {
        "id": "dan",
        "name": "Coach Dan",
        "role": "Neighborhood Athletics Coach",
        "is_family": False,
        "building": "street",
        "x": 680,
        "y": 880,
        "shirt": (235, 95, 75),
        "pants": (55, 62, 72),
        "hair": (85, 62, 42),
        "skin": (235, 198, 172),
        "accessory": "cap",
        "scale": 1.05,
        "bio": "Jogs along Main Street and sees everyone coming and going.",
    },
]
