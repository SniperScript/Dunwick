"""
Dynamic 3-Scenario, 7-Day Butterfly-Effect & Human Routine Simulation Engine
for CHRONICLES OF DUNWICK: DEFYING FATE (1924).

Core Mechanics:
1. THREE PLAYABLE SCENARIOS:
   - "WORLD_END"  (Scenario 1: The World Is Going to End — Imperial Aether-Boiler Cataclysm)
   - "SELF_DEATH" (Scenario 2: You Are Going to Die — Final-Destination Personal Fate Web)
   - "LOVED_ONE"  (Scenario 3: Your Loved One Is Going to Die — Assassination -> Carriage Crash -> Suffocation on Food -> ...)
2. SOLE-KNOWER ISOLATION:
   - Only the single chosen family protagonist (Arthur, Elena, Maya, or Leo) knows about the time loop
     and impending doom. Even the other 3 family members are autonomous human NPCs who do NOT know!
3. 7-DAY BUTTERFLY EFFECT & ANTI-WALKTHROUGH PERMUTATION:
   - Every intervention on Day d physically alters Dunwick's causal web, spawning a mutated threat on Day d+1.
   - Only by surviving/protecting across all 7 Days (Monday–Sunday) is Fate broken.
   - Every loop dynamically permutes Catalyst NPCs, Witness NPCs, Behavioral Tells, and Subconscious Dream Echoes
     so the game can NEVER be 'solved' by rote memorization.
"""

import math
import os
import random
from config import (
    BUILDINGS,
    CHARACTER_SPECS,
    DAY_DURATION_SECONDS,
    PROTAGONIST_LOVED_ONE,
    SCENARIO_MODES,
    TOTAL_DAYS_IN_WEEK,
    WEEK_DAYS,
    WORLD_HEIGHT,
    WORLD_OBJECTS,
    WORLD_WIDTH,
)
from skeletal_engine import ParticleSystem2D, SkeletalRig2D
from tile_grid_engine import TileGridEngine
from vector_memory import VectorMemoryStore
from butterfly_nn import DunwickButterflyEcosystem
from yarn_engine import YarnDialogueEngine


# Social spheres for per-protagonist starting rapport in 1924 Dunwick-on-Severn
SOCIAL_AFFINITY = {
    "arthur": {"vance", "pam", "raj", "hank", "miller", "mayor", "jenkins"},
    "elena": {"sal", "mia", "sam", "martha", "lin", "mayor", "joya"},
    "maya": {"clarke", "higgins", "chloe", "zack", "lin", "joya", "raj"},
    "leo": {"toby", "dan", "rosa", "jenkins", "sal", "martha", "chloe"},
}

# 1924 Dunwick-on-Severn Daily Routine Waypoints
SCHEDULE_LOCATIONS = {
    "home_living": (520.0, 360.0, "In Ashford Manor Parlour"),
    "home_study": (260.0, 560.0, "At the Manor Brass Orrery Desk"),
    "cafe_bar": (1180.0, 320.0, "At The Brass Kettle Steam-Urn"),
    "cafe_tables": (1380.0, 490.0, "Taking tea & pie at The Brass Kettle"),
    "cafe_patio": (1290.0, 785.0, "Outside The Brass Kettle awning"),
    "office_lobby": (1950.0, 340.0, "At Royal Aether-Works Chancery"),
    "office_desk": (1960.0, 510.0, "Drafting in the Ministry Chancery"),
    "power_room": (2215.0, 540.0, "By the Imperial Aether-Boiler"),
    "school_lab": (265.0, 1285.0, "In St. Dunstan's Galvanic Lab"),
    "school_class": (560.0, 1285.0, "In St. Dunstan's Lecture Hall"),
    "school_gym": (420.0, 1510.0, "In St. Dunstan's Fencing Yard"),
    "market_tools": (1135.0, 1255.0, "At Guildhall Ironmonger Stall"),
    "market_bakery": (1435.0, 1255.0, "At Crown Bakehouse & Pie Stall"),
    "market_chem": (1145.0, 1515.0, "At Guildhall Apothecary Counter"),
    "park_police": (1965.0, 1275.0, "At Scotland Yard Constabulary Post"),
    "park_fountain": (2245.0, 1515.0, "Near the Medieval Gargoyle Fountain"),
    "street_west": (680.0, 880.0, "Walking along West High Street"),
    "street_center": (1290.0, 880.0, "Crossing Central High Street"),
    "street_east": (1920.0, 880.0, "Walking along East High Street"),
}

# Human Behavioral Micro-Tells (shuffled & assigned dynamically each loop/day)
HUMAN_DAILY_TELLS = [
    "repeatedly checking a tarnished brass pocket-watch with trembling fingers",
    "glancing over their shoulder toward the Clocktower gargoyles",
    "wiping coal-soot from their sleeves while muttering about a late delivery",
    "clutching an unsealed parcel wrapped in oilcloth",
    "coughing slightly from the sulfur-damp rolling off the Severn",
    "tapping a brass sovereign nervously against their teacup",
    "hurrying their steps to beat the five-o'clock steam-tram bell",
    "squinting at a smudged apothecary receipt",
]


# ==============================================================================
# 7-DAY BUTTERFLY EFFECT BLUEPRINTS FOR ALL 3 SCENARIOS
# Every Day (1..7) defines the Fate Vector theme, while the engine permutes
# the specific Catalyst NPC, Witness NPC, Specialist Ally, and Causal Ripple!
# ==============================================================================
SCENARIO_DAY_BLUEPRINTS = {
    "WORLD_END": [
        {
            "day": 1,
            "title": "THE SABOTEUR'S PRESSURE RELAY",
            "hazard_type": "BOILER_SABOTAGE",
            "hazard_obj": "market_ledger",
            "alt_obj": "power_generator",
            "catalyst_pool": ["zack", "sam", "raj", "dan"],
            "witness_pool": ["mia", "sal", "jenkins", "rosa"],
            "specialist_id": "miller",
            "hazard_loc_key": "power_room",
            "base_cause": "An unwitting courier was paid in Crown sovereigns to swap a high-pressure brass relay at the Foundry.",
            "symptom_hint": "someone carrying an unlogged brass pressure relay from the Guildhall Bazaar toward the Foundry",
            "counter_item": "Calibrated Brass Governor",
        },
        {
            "day": 2,
            "title": "THE BAZAAR COAL-GAS BACKFLOW",
            "hazard_type": "COAL_GAS_SURGE",
            "hazard_obj": "market_ledger",
            "alt_obj": "office_records",
            "catalyst_pool": ["sam", "martha", "lin", "zack"],
            "witness_pool": ["sal", "rosa", "dan", "toby"],
            "specialist_id": "raj",
            "hazard_loc_key": "market_tools",
            "base_cause": "Butterfly Effect: Blocking Monday's relay diverted excess steam pressure into the medieval coal-gas mains beneath the Bazaar!",
            "symptom_hint": "the cast-iron cellar grates beneath the Guildhall Bazaar hissing with volatile coal-damp",
            "counter_item": "Copper Venting Spanner",
        },
        {
            "day": 3,
            "title": "ST. DUNSTAN'S GALVANIC RESONANCE",
            "hazard_type": "GALVANIC_ARC",
            "hazard_obj": "school_lab_table",
            "alt_obj": "office_records",
            "catalyst_pool": ["clarke", "higgins", "chloe", "lin"],
            "witness_pool": ["toby", "dan", "mia", "jenkins"],
            "specialist_id": "clarke",
            "hazard_loc_key": "school_lab",
            "base_cause": "Butterfly Effect: Venting the Bazaar gas mains induced a violent electromagnetic surge in St. Dunstan's ley-line coils!",
            "symptom_hint": "blue galvanic sparks jumping across the gothic ironwork at St. Dunstan's Polytechnic",
            "counter_item": "Grounded Ley-Capacitor",
        },
        {
            "day": 4,
            "title": "THE TEAHOUSE STEAM-MAIN RUPTURE",
            "hazard_type": "STEAM_PIPE_BURST",
            "hazard_obj": "cafe_counter",
            "alt_obj": "office_records",
            "catalyst_pool": ["sal", "mia", "mayor", "jenkins"],
            "witness_pool": ["martha", "rosa", "sam", "zack"],
            "specialist_id": "raj",
            "hazard_loc_key": "cafe_bar",
            "base_cause": "Butterfly Effect: Grounding the Polytechnic coils drove superheated steam into the Brass Kettle's copper urn pipes!",
            "symptom_hint": "the copper steam-urn at The Brass Kettle shrieking at twice its safe pressure limit",
            "counter_item": "Chancery Bleed-Valve Key",
        },
        {
            "day": 5,
            "title": "THE MINISTRY LOCKDOWN OVERLOAD",
            "hazard_type": "MINISTRY_OVERLOAD",
            "hazard_obj": "office_records",
            "alt_obj": "police_dispatch",
            "catalyst_pool": ["vance", "pam", "mayor", "hank"],
            "witness_pool": ["raj", "jenkins", "sal", "clarke"],
            "specialist_id": "vance",
            "hazard_loc_key": "office_desk",
            "base_cause": "Butterfly Effect: Alarmed by four days of pressure anomalies, Lord Vance ordered all relief valves sealed for a max-load test!",
            "symptom_hint": "a sealed Ministry dispatch ordering the Imperial Boiler governors bolted shut at dusk",
            "counter_item": "Royal Architect's Writ",
        },
        {
            "day": 6,
            "title": "THE CLOCKTOWER PENDULUM SEIZURE",
            "hazard_type": "GARGOYLE_COLLAPSE",
            "hazard_obj": "study_notebook",
            "alt_obj": "power_generator",
            "catalyst_pool": ["jenkins", "hank", "raj", "sam"],
            "witness_pool": ["toby", "rosa", "dan", "joya"],
            "specialist_id": "jenkins",
            "hazard_loc_key": "power_room",
            "base_cause": "Butterfly Effect: Overriding the Ministry lockdown threw the Great Clocktower gear-train out of synchronization!",
            "symptom_hint": "the main Clocktower escapement grinding violently above the Aether-Boiler chamber",
            "counter_item": "Horologist's Escapement Gear",
        },
        {
            "day": 7,
            "title": "THE GRAND HARMONIC CONVERGENCE",
            "hazard_type": "FINAL_CONVERGENCE",
            "hazard_obj": "power_generator",
            "alt_obj": "school_lab_table",
            "catalyst_pool": ["vance", "raj", "clarke", "lin"],
            "witness_pool": ["miller", "sal", "jenkins", "rosa"],
            "specialist_id": "miller",
            "hazard_loc_key": "power_room",
            "base_cause": "Seventh-Day Reckoning: Every deflected causal wave from Monday through Saturday converges on the Imperial Aether-Boiler!",
            "symptom_hint": "the Imperial Aether-Boiler glowing violet as all seven ley-line conduits reach harmonic peak",
            "counter_item": "Seventh-Day Harmonic Key",
        },
    ],
    "SELF_DEATH": [
        {
            "day": 1,
            "title": "THE POISONED CUP AT THE BRASS KETTLE",
            "hazard_type": "ASSASSINATION_POISON",
            "hazard_obj": "cafe_counter",
            "alt_obj": "market_ledger",
            "catalyst_pool": ["mia", "sal", "lin", "zack"],
            "witness_pool": ["jenkins", "martha", "rosa", "mayor"],
            "specialist_id": "lin",
            "hazard_loc_key": "cafe_tables",
            "base_cause": "Predetermined Fate: A bitter-almond aconite draught has been slipped into the teacup meant for you at The Brass Kettle.",
            "symptom_hint": "a faint scent of bitter almonds rising from a porcelain cup near the Teahouse counter",
            "counter_item": "Apothecary Charcoal Draught",
        },
        {
            "day": 2,
            "title": "THE RUNAWAY STEAM-LORRY ON HIGH STREET",
            "hazard_type": "CARRIAGE_CRASH",
            "hazard_obj": "market_ledger",
            "alt_obj": "police_dispatch",
            "catalyst_pool": ["zack", "sam", "dan", "rosa"],
            "witness_pool": ["jenkins", "toby", "sal", "hank"],
            "specialist_id": "rosa",
            "hazard_loc_key": "street_center",
            "base_cause": "Butterfly Effect: Because you survived Monday's poisoned tea, Fate sheared a brake cotter-pin on a heavy Steam-Lorry heading straight for your crosswalk!",
            "symptom_hint": "a brass Steam-Lorry on High Street with a sheared brake pin and screeching iron wheels",
            "counter_item": "Forged Iron Brake-Pin",
        },
        {
            "day": 3,
            "title": "SUFFOCATION ON SPICED MUTTON PIE",
            "hazard_type": "FOOD_CHOKING",
            "hazard_obj": "cafe_counter",
            "alt_obj": "market_ledger",
            "catalyst_pool": ["martha", "sal", "mia", "joya"],
            "witness_pool": ["jenkins", "mayor", "chloe", "toby"],
            "specialist_id": "joya",
            "hazard_loc_key": "cafe_bar",
            "base_cause": "Butterfly Effect: Rattled by Tuesday's runaway lorry, your hurried meal from the Bakehouse contains an unboned splinter/dense crust fated to suffocate you!",
            "symptom_hint": "a hastily baked batch of thick-crusted mutton pies served piping hot without proper slicing",
            "counter_item": "Sister Joya's Triage Kit",
        },
        {
            "day": 4,
            "title": "THE FALLING MEDIEVAL STONE GARGOYLE",
            "hazard_type": "GARGOYLE_COLLAPSE",
            "hazard_obj": "office_records",
            "alt_obj": "police_dispatch",
            "catalyst_pool": ["hank", "raj", "toby", "sam"],
            "witness_pool": ["toby", "dan", "rosa", "jenkins"],
            "specialist_id": "hank",
            "hazard_loc_key": "park_fountain",
            "base_cause": "Butterfly Effect: The vibrations from earlier in the week cracked the mortar of a 300-pound Norman stone gargoyle right above your path!",
            "symptom_hint": "crumbling medieval mortar raining down from the gothic cornice near the Commons",
            "counter_item": "Sapper's Shoring Clamp",
        },
        {
            "day": 5,
            "title": "THE GALVANIC CAPACITOR DISCHARGE",
            "hazard_type": "GALVANIC_ARC",
            "hazard_obj": "school_lab_table",
            "alt_obj": "power_generator",
            "catalyst_pool": ["clarke", "chloe", "raj", "higgins"],
            "witness_pool": ["chloe", "pam", "lin", "toby"],
            "specialist_id": "clarke",
            "hazard_loc_key": "school_lab",
            "base_cause": "Butterfly Effect: Stepping aside from Thursday's falling stonework routes you past an ungrounded 10,000-volt Galvanic Coil set to arc into your chest!",
            "symptom_hint": "an uninsulated copper induction coil humming with lethal static at St. Dunstan's",
            "counter_item": "Rubberized Earthing Rod",
        },
        {
            "day": 6,
            "title": "THE MANOR COAL-GAS DAMPER LEAK",
            "hazard_type": "COAL_GAS_SURGE",
            "hazard_obj": "study_notebook",
            "alt_obj": "office_records",
            "catalyst_pool": ["pam", "sam", "zack", "raj"],
            "witness_pool": ["sal", "jenkins", "martha", "rosa"],
            "specialist_id": "sam",
            "hazard_loc_key": "home_study",
            "base_cause": "Butterfly Effect: Seeking refuge inside Ashford Manor after five near-deaths, a jammed flue damper floods the study with odourless coal-damp!",
            "symptom_hint": "the brass flue-damper in Ashford Manor's hearth sticking shut while coal-gas pressure rises",
            "counter_item": "Brass Flue-Draft Key",
        },
        {
            "day": 7,
            "title": "DEFYING THE REAPER'S SEVENTH BELL",
            "hazard_type": "FINAL_CONVERGENCE",
            "hazard_obj": "power_generator",
            "alt_obj": "police_dispatch",
            "catalyst_pool": ["vance", "zack", "lin", "dan"],
            "witness_pool": ["miller", "rosa", "jenkins", "sal"],
            "specialist_id": "miller",
            "hazard_loc_key": "power_room",
            "base_cause": "Seventh-Day Reckoning: Fate's unseen agent corners you near the Clocktower Boiler for one final lethal strike before Sunday's last bell!",
            "symptom_hint": "a shadowy figure in a tweed cape tampering with the Clocktower steam-lock as the 7th bell nears",
            "counter_item": "Scotland Yard Arrest Writ",
        },
    ],
    "LOVED_ONE": [
        {
            "day": 1,
            "title": "THE CLOCKWORK ASSASSINATION",
            "hazard_type": "ASSASSINATION_POISON",
            "hazard_obj": "police_dispatch",
            "alt_obj": "cafe_counter",
            "catalyst_pool": ["zack", "dan", "lin", "vance"],
            "witness_pool": ["mia", "sal", "jenkins", "rosa"],
            "specialist_id": "miller",
            "hazard_loc_key": "cafe_patio",
            "base_cause": "Predetermined Fate: A shadowy assassin with a pneumatic dart/poisoned cup has targeted your Loved One outside The Brass Kettle Teahouse!",
            "symptom_hint": "a suspicious stranger loitering near The Brass Kettle awning watching your Loved One's table",
            "counter_item": "Constabulary Protective Detail",
        },
        {
            "day": 2,
            "title": "THE RUNAWAY STEAM-CARRIAGE CRASH",
            "hazard_type": "CARRIAGE_CRASH",
            "hazard_obj": "market_ledger",
            "alt_obj": "office_records",
            "catalyst_pool": ["zack", "sam", "dan", "mayor"],
            "witness_pool": ["rosa", "jenkins", "toby", "sal"],
            "specialist_id": "rosa",
            "hazard_loc_key": "street_center",
            "base_cause": "Butterfly Effect: Because you foiled Monday's assassination, your Loved One's schedule shifted by 15 minutes—putting them directly in front of a Runaway Steam-Carriage on High Street!",
            "symptom_hint": "a heavy brass Steam-Carriage barrels down High Street with a snapped brake-chain right where your Loved One crosses",
            "counter_item": "Emergency Tramway Brake-Wedge",
        },
        {
            "day": 3,
            "title": "SUFFOCATING ON A PLATE OF FOOD",
            "hazard_type": "FOOD_CHOKING",
            "hazard_obj": "cafe_counter",
            "alt_obj": "market_ledger",
            "catalyst_pool": ["martha", "mia", "sal", "mayor"],
            "witness_pool": ["mia", "sal", "jenkins", "joya"],
            "specialist_id": "joya",
            "hazard_loc_key": "cafe_tables",
            "base_cause": "Butterfly Effect: Shaken by Tuesday's near-crash on High Street, your Loved One bolts down a plate of spiced mutton pie at the Teahouse and is fated to choke and suffocate!",
            "symptom_hint": "Mistress Martha's rushed mutton pie platter at the Teahouse—your Loved One is eating far too quickly to catch the 5:30 bell",
            "counter_item": "Sliced Meal & Sister Joya's Aid",
        },
        {
            "day": 4,
            "title": "THE SCALDING STEAM-MANIFOLD BURST",
            "hazard_type": "STEAM_PIPE_BURST",
            "hazard_obj": "office_records",
            "alt_obj": "power_generator",
            "catalyst_pool": ["raj", "sam", "hank", "pam"],
            "witness_pool": ["pam", "jenkins", "zack", "clarke"],
            "specialist_id": "raj",
            "hazard_loc_key": "office_lobby",
            "base_cause": "Butterfly Effect: Surviving Wednesday's choking crisis sends your Loved One on an afternoon errand past the Chancery just as a corroded brass steam-pipe ruptures!",
            "symptom_hint": "a hairline fracture in the high-pressure brass steam manifold along the Chancery corridor",
            "counter_item": "Riveted Brass Pipe-Collar",
        },
        {
            "day": 5,
            "title": "THE TAINTED APOTHECARY REMEDY",
            "hazard_type": "APOTHECARY_POISON",
            "hazard_obj": "school_lab_table",
            "alt_obj": "market_ledger",
            "catalyst_pool": ["lin", "martha", "clarke", "chloe"],
            "witness_pool": ["sam", "joya", "mia", "toby"],
            "specialist_id": "lin",
            "hazard_loc_key": "market_chem",
            "base_cause": "Butterfly Effect: Startled by Thursday's steam blast, your Loved One requests a calming draught from the Apothecary—where a bottle of lethal belladonna was misfiled!",
            "symptom_hint": "two identical amber phials on the Apothecary shelf—one soothing valerian, the other concentrated belladonna",
            "counter_item": "Alchemical Litmus & Antidote",
        },
        {
            "day": 6,
            "title": "THE GARGOYLE MASONRY COLLAPSE",
            "hazard_type": "GARGOYLE_COLLAPSE",
            "hazard_obj": "study_notebook",
            "alt_obj": "police_dispatch",
            "catalyst_pool": ["toby", "hank", "sam", "dan"],
            "witness_pool": ["toby", "rosa", "joya", "jenkins"],
            "specialist_id": "hank",
            "hazard_loc_key": "park_fountain",
            "base_cause": "Butterfly Effect: Taking fresh air in Severn Commons after Friday's close call places your Loved One directly beneath a loosened medieval stone gargoyle!",
            "symptom_hint": "a cracked stone gargoyle wobbling above the Severn Commons archway as steam-trams rumble past",
            "counter_item": "Cordoned Masonry Barrier",
        },
        {
            "day": 7,
            "title": "SEVERING THE FATAL THREAD",
            "hazard_type": "FINAL_CONVERGENCE",
            "hazard_obj": "power_generator",
            "alt_obj": "school_lab_table",
            "catalyst_pool": ["vance", "clarke", "raj", "miller"],
            "witness_pool": ["sal", "jenkins", "rosa", "joya"],
            "specialist_id": "joya",
            "hazard_loc_key": "park_fountain",
            "base_cause": "Seventh-Day Reckoning: Fate lashes out with a combined galvanic & steam surge where your Loved One walks on Sunday evening. Protect them through the 7th bell!",
            "symptom_hint": "an ominous galvanic charge building between the Clocktower spire and the Commons fountain",
            "counter_item": "Aether-Grounded Ward",
        },
    ],
}


class SimCharacter:
    def __init__(self, spec: dict, is_player: bool = False):
        self.id = spec["id"]
        self.name = spec["name"]
        self.role = spec["role"]
        self.is_family = spec.get("is_family", False)
        self.home_building = spec["building"]
        self.spawn_x = float(spec["x"])
        self.spawn_y = float(spec["y"])
        self.perk = spec.get("perk", "Borough Resident")
        self.bio = spec.get("bio", "")
        self.spec = spec

        self.x = self.spawn_x
        self.y = self.spawn_y
        self.vx = 0.0
        self.vy = 0.0
        self.base_speed = 268.0 if self.id == "leo" else (228.0 if self.is_family else 148.0)
        self.is_player = is_player

        self.rig = SkeletalRig2D(spec)
        self.memory_store = VectorMemoryStore(agent_id=self.id, baseline_memories=[self.bio])

        self.relationships: dict[str, int] = {}
        self.grudges: set[str] = set()
        self.init_relationships()

        self.trust = 85 if self.is_family else 55
        self.speech_bubble = ""
        self.speech_timer = 0.0
        self.path_waypoints: list[tuple[float, float]] = []
        self.current_schedule_label = "Following 1924 borough routine"
        self.daily_tell = "going about their afternoon duties"
        self.schedule_shifted_today = False
        self.schedule_recalc_timer = random.uniform(0.5, 2.0)
        self.step_timer = 0.0
        self.stuck_timer = 0.0
        self.arrested = False

    def init_relationships(self):
        for fam_id in ("arthur", "elena", "maya", "leo"):
            if self.is_family:
                self.relationships[fam_id] = 88
            elif self.id in SOCIAL_AFFINITY.get(fam_id, set()):
                self.relationships[fam_id] = 74
            else:
                self.relationships[fam_id] = 52
        self.grudges.clear()

    def get_rapport(self, fam_id: str) -> int:
        if fam_id in self.grudges:
            return 12
        return self.relationships.get(fam_id, 52)

    def get_relationship_status(self, fam_id: str) -> str:
        if fam_id in self.grudges:
            return "SKEPTICAL / ALARMED"
        if self.is_family:
            return "UNAWAKENED FAMILY"
        r = self.get_rapport(fam_id)
        if r >= 75:
            return "CONFIDANT"
        if r >= 60:
            return "CORDIAL"
        return "GUARDED"

    def modify_rapport(self, fam_id: str, delta: int):
        cur = self.relationships.get(fam_id, 52)
        self.relationships[fam_id] = max(5, min(100, cur + delta))
        self.trust = self.relationships[fam_id]

    def add_grudge(self, fam_id: str):
        self.grudges.add(fam_id)
        self.relationships[fam_id] = 12
        self.trust = 12

    def clear_grudges(self):
        self.grudges.clear()
        for fam_id in ("arthur", "elena", "maya", "leo"):
            self.relationships[fam_id] = max(85, self.relationships.get(fam_id, 52))
        self.trust = 90

    def say(self, text: str, duration: float = 5.0):
        self.speech_bubble = text
        self.speech_timer = duration


class SimulationWorld:
    def __init__(self, llm_broker):
        self.llm_broker = llm_broker
        self.particles = ParticleSystem2D()
        self.grid_engine = TileGridEngine()

        # Butterfly Neural Ecosystem (adapted from The-Butterfly-)
        self.butterfly_eco = DunwickButterflyEcosystem(CHARACTER_SPECS)

        # Yarn Spinner Dialogue Engine (adapted from YarnSpinner)
        self.yarn_engine = YarnDialogueEngine()
        yarn_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "dialogue", "dunwick_fate.yarn")
        if os.path.exists(yarn_path):
            self.yarn_engine.load_yarn_file(yarn_path)

        # Core Campaign Parameters - Defaulting to SELF_DEATH ("You are gonna die!")
        self.scenario_mode = "SELF_DEATH"  # "WORLD_END", "SELF_DEATH", "LOVED_ONE"
        self.player_char_id = "arthur"
        self.loop_id = 1
        self.current_day = 1  # 1 (Monday) .. 7 (Sunday)
        self.campaign_seed = random.randint(1000, 999999)

        # Sole-Knower Death Journal across loops
        self.death_journal: list[dict] = []
        self.pending_fatal_death: bool = False
        self.fatal_death_type: str = ""

        # Build all 24 characters
        self.specs_by_id = {s["id"]: s for s in CHARACTER_SPECS}
        self.characters: dict[str, SimCharacter] = {}
        for spec in CHARACTER_SPECS:
            c = SimCharacter(spec, is_player=(spec["id"] == self.player_char_id))
            c.spawn_x, c.spawn_y = self.grid_engine.snap_to_nearest_walkable(c.spawn_x, c.spawn_y)
            c.x, c.y = c.spawn_x, c.spawn_y
            self.characters[spec["id"]] = c

        self.objects = {obj["id"]: dict(obj) for obj in WORLD_OBJECTS}
        self.buildings = {b["id"]: b for b in BUILDINGS}

        # Dynamic Butterfly Effect State for the Current Day
        self.scenario = {}  # Active day's permuted Butterfly threat dict
        self.butterfly_history: list[dict] = []  # Records how each day's intervention mutated the next day
        self.last_intervention_style = "Initial Premonition"

        # Detective & Survival State
        self.shutdown_code = ""
        self.chapter = 1
        self.notebook_clues: list[str] = []
        self.discovered_flags: set[str] = set()
        self.zone_state: dict[str, bool] = {}
        self.deja_vu_charges = 2
        self.has_warm_coffee = False  # Earl Grey Tea cup
        self.held_counter_item: str | None = None
        self.credibility = 100  # Social Composure (0..100%). If 0%, detained for Aether-Fever!

        self.elapsed_time = 0.0
        self.time_remaining = DAY_DURATION_SECONDS
        self.outcome_state = None  # None, "DAY_SAVED", "TIME_UP", "VICTORY"
        self.outcome_reason = ""
        self.chatter_timer = 2.8

        # Active 2.5D Scene: "OVERWORLD" (exterior houses & streets) or a building_id ("home", "cafe", etc.)
        self.active_scene = "OVERWORLD"
        self.scene_transition_cooldown = 0.0
        self.scene_banner_text = ""
        self.scene_banner_timer = 0.0

        self.start_new_campaign(player_char_id="arthur", scenario_mode="SELF_DEATH")

    def get_protected_target_id(self) -> str:
        """Returns who Fate is trying to kill/destroy in the current Scenario."""
        if self.scenario_mode == "SELF_DEATH":
            return self.player_char_id
        if self.scenario_mode == "LOVED_ONE":
            info = PROTAGONIST_LOVED_ONE.get(self.player_char_id, PROTAGONIST_LOVED_ONE["arthur"])
            return info["target_id"]
        return "arthur"

    def get_protected_target_label(self) -> str:
        if self.scenario_mode == "WORLD_END":
            return "Dunwick-on-Severn (The World)"
        if self.scenario_mode == "SELF_DEATH":
            return f"Yourself ({self.get_player().name})"
        info = PROTAGONIST_LOVED_ONE.get(self.player_char_id, PROTAGONIST_LOVED_ONE["arthur"])
        return info["relation"]

    def get_day_name(self, day_num: int = None) -> str:
        d = day_num if day_num is not None else self.current_day
        return WEEK_DAYS[(max(1, min(7, d)) - 1)]

    def _reset_daily_zone_state(self):
        """Resets daily investigation milestones when advancing to a new day or new loop."""
        self.zone_state = {
            "home_research_synced": False,
            "witness_interviewed": False,
            "market_manifest_logged": False,
            "saboteur_identified": False,
            "school_lab_calibrated": False,
            "office_code_unlocked": False,
            "evidence_confiscated": False,
            "police_clearance_granted": False,
            # Butterfly-Effect Daily Resolution Flags
            "threat_deduced": False,
            "counter_item_crafted": False,
            "schedule_redirected": False,
            "specialist_alerted": False,
            "day_threat_foiled": False,
        }
        self.held_counter_item = None

    def _generate_daily_butterfly_node(self, day_num: int):
        """
        Procedurally permutes Day `day_num`'s Butterfly Threat based on:
        - `self.scenario_mode` ("WORLD_END", "SELF_DEATH", "LOVED_ONE")
        - `self.campaign_seed`, `self.loop_id`, `day_num`, `self.player_char_id`
        - `self.last_intervention_style` (The Butterfly Effect from the previous day!)
        This guarantees the game can NEVER be solved with a static walkthrough!
        """
        blueprints = SCENARIO_DAY_BLUEPRINTS.get(self.scenario_mode, SCENARIO_DAY_BLUEPRINTS["WORLD_END"])
        bp = blueprints[max(0, min(len(blueprints) - 1, day_num - 1))]

        rng = random.Random(f"{self.campaign_seed}_{self.loop_id}_{day_num}_{self.player_char_id}_{self.last_intervention_style}")
        protected_id = self.get_protected_target_id()

        # Pick a Catalyst NPC (cannot be the player or the protected loved one)
        valid_catalysts = [
            cid for cid in bp["catalyst_pool"] if cid != self.player_char_id and cid != protected_id
        ]
        if not valid_catalysts:
            valid_catalysts = ["zack", "sam", "sal", "raj"]
        catalyst_id = rng.choice(valid_catalysts)
        catalyst_char = self.characters[catalyst_id]

        # Pick a Witness NPC (distinct from player, protected target, and catalyst)
        valid_witnesses = [
            wid
            for wid in bp["witness_pool"]
            if wid not in (self.player_char_id, protected_id, catalyst_id)
        ]
        if not valid_witnesses:
            valid_witnesses = ["jenkins", "mia", "rosa"]
        witness_id = rng.choice(valid_witnesses)
        witness_char = self.characters[witness_id]

        specialist_id = bp["specialist_id"]
        if specialist_id in (self.player_char_id, catalyst_id):
            specialist_id = "joya" if specialist_id != "joya" else "miller"
        specialist_char = self.characters[specialist_id]

        # Assign fresh human behavioral tells to all NPCs for today
        for cid, ch in self.characters.items():
            ch.schedule_shifted_today = False
            if cid == catalyst_id:
                ch.daily_tell = f"acting unusually hurried and {rng.choice(HUMAN_DAILY_TELLS)}"
            elif cid == witness_id:
                ch.daily_tell = f"watching the street closely while {rng.choice(HUMAN_DAILY_TELLS)}"
            else:
                ch.daily_tell = rng.choice(HUMAN_DAILY_TELLS)

        # Toggle runaway vehicle hazard on High Street if today is a Steam-Carriage Crash day!
        is_crash_day = bp["hazard_type"] == "CARRIAGE_CRASH"
        for idx, veh in enumerate(self.grid_engine.vehicles):
            veh.runaway_hazard = is_crash_day and (idx == 0)

        # Build the dynamic Butterfly Causal link text
        if day_num == 1:
            butterfly_origin = f"Initial Premonition (Loop #{self.loop_id}): {bp['base_cause']}"
        else:
            prev_day_name = self.get_day_name(day_num - 1)
            butterfly_origin = (
                f"Because you foiled {prev_day_name}'s threat via [{self.last_intervention_style}], "
                f"{bp['base_cause']}"
            )

        self.shutdown_code = f"AETHER-{rng.randint(100, 999)}"
        self.scenario = {
            "day": day_num,
            "day_name": self.get_day_name(day_num),
            "title": bp["title"],
            "hazard_type": bp["hazard_type"],
            "hazard_obj": bp["hazard_obj"],
            "alt_obj": bp["alt_obj"],
            "saboteur_id": catalyst_id,
            "saboteur_name": catalyst_char.name,
            "saboteur_hint": f"{catalyst_char.role.lower()} ({catalyst_char.daily_tell.split(' and ')[0]})",
            "witness_id": witness_id,
            "witness_name": witness_char.name,
            "market_id": specialist_id,
            "market_name": specialist_char.name,
            "analyst_id": "clarke" if self.player_char_id != "clarke" else "lin",
            "analyst_name": self.characters["clarke"].name,
            "item_clue": bp["counter_item"],
            "trace_type": bp["symptom_hint"],
            "motive": butterfly_origin,
            "hazard_loc_key": bp["hazard_loc_key"],
        }

    def start_new_campaign(self, player_char_id: str = None, scenario_mode: str = None):
        """Starts a fresh 7-Day Week Campaign in the selected Scenario Mode and Protagonist."""
        if player_char_id in ("arthur", "elena", "maya", "leo"):
            self.player_char_id = player_char_id
        if scenario_mode in SCENARIO_MODES:
            self.scenario_mode = scenario_mode

        self.campaign_seed = random.randint(1000, 999999)
        self.loop_id = 1
        self.current_day = 1
        self.chapter = 1
        self.notebook_clues = []
        self.discovered_flags.clear()
        self.butterfly_history.clear()
        self.last_intervention_style = "Initial Premonition"
        self.deja_vu_charges = 2
        self.has_warm_coffee = False
        self.credibility = 100

        for c in self.characters.values():
            c.init_relationships()
            c.memory_store.reset_for_new_loop(loop_id=1, full_wipe=True)

        sc_info = SCENARIO_MODES[self.scenario_mode]
        p_name = self.characters[self.player_char_id].name
        self.add_clue(
            "campaign_start",
            f"{sc_info['short_title']}: Playing as {p_name}. ONLY YOU remember the vision. Protect {self.get_protected_target_label()} from Monday to Sunday!",
        )
        self.start_loop(player_char_id=self.player_char_id, is_new_loop=False, reset_to_monday=True)

    def add_clue(self, flag_key: str, text: str):
        if flag_key not in self.discovered_flags:
            self.discovered_flags.add(flag_key)
            self.notebook_clues.append(text)
        elif text not in self.notebook_clues:
            self.notebook_clues.append(text)

    def start_loop(self, player_char_id: str = None, is_new_loop: bool = True, reset_to_monday: bool = True):
        """
        Starts or rewinds a time loop.
        When rewinding after a failure (`is_new_loop=True`):
        - Injects Subconscious Dream Echoes into NPCs so their dialogue & behavior shift on the new loop!
        - Permutes the Butterfly seed so the player cannot rely on rote memorization!
        """
        if player_char_id in ("arthur", "elena", "maya", "leo"):
            self.player_char_id = player_char_id

        if is_new_loop:
            failed_day_name = self.get_day_name(self.current_day)
            failed_title = self.scenario.get("title", "the catastrophe")
            self.loop_id += 1

            # Inject haunting subconscious echoes into NPC vector memories so the next loop feels fresh!
            for c in self.characters.values():
                c.memory_store.reset_for_new_loop(loop_id=self.loop_id, full_wipe=False)
                if not c.is_player:
                    c.memory_store.inject_subconscious_echo(
                        f"Dreamt of {failed_title.lower()} striking on {failed_day_name}",
                        loop_id=self.loop_id,
                    )
                    if not c.memory_store.has_anchored_memory():
                        c.grudges.clear()

        if reset_to_monday:
            self.current_day = 1
            self.butterfly_history.clear()
            self.last_intervention_style = f"Loop #{self.loop_id} Divergence"

        self._setup_current_day()

    def advance_to_next_day(self) -> str:
        """
        Advances from Day d to Day d+1 after foiling Day d's threat!
        Triggers the Butterfly Effect: Day d's intervention mutates into Day d+1's new hazard!
        """
        if not self.zone_state.get("day_threat_foiled", False):
            return f"You must foil {self.get_day_name()}'s Fate Vector before advancing to the next day!"

        if self.current_day >= TOTAL_DAYS_IN_WEEK:
            self.outcome_state = "VICTORY"
            self.outcome_reason = (
                f"ALL 7 DAYS SURVIVED (MONDAY TO SUNDAY)! Across {self.loop_id} loop(s), "
                f"{self.get_player().name} outwitted every Butterfly Effect twist in Dunwick-on-Severn "
                f"and permanently saved {self.get_protected_target_label()} from predetermined Fate!"
            )
            return "SEVENTH DAY COMPLETE! YOU DEFIED FATE!"

        self.current_day += 1
        self._setup_current_day()
        new_day = self.get_day_name()
        return (
            f"DAWN OF DAY {self.current_day}/7 ({new_day.upper()})! "
            f"Butterfly Effect triggered: {self.scenario['title']}!"
        )

    def _setup_current_day(self):
        self._reset_daily_zone_state()
        self._generate_daily_butterfly_node(self.current_day)

        self.elapsed_time = 0.0
        self.time_remaining = DAY_DURATION_SECONDS
        self.outcome_state = None
        self.outcome_reason = ""
        self.has_warm_coffee = False
        self.credibility = min(100, max(75, self.credibility + 20))
        self.particles.particles.clear()
        self.active_scene = "OVERWORLD"
        self.scene_transition_cooldown = 0.35

        for cid, char in self.characters.items():
            char.is_player = cid == self.player_char_id
            if char.is_player:
                # Place the player on the Overworld right in front of the Ashford-Mercer Tudor Manor steps!
                home_b = self.buildings.get(char.home_building, self.buildings["home"])
                is_north = home_b["door_y"] > home_b["rect"][1] + home_b["rect"][3] // 2
                char.x = float(home_b["door_x"])
                char.y = float(home_b["door_y"] + 28) if is_north else float(home_b["door_y"] - 28)
            else:
                sx, sy = self.grid_engine.snap_to_nearest_walkable(
                    char.spawn_x + random.uniform(-12, 12),
                    char.spawn_y + random.uniform(-12, 12),
                )
                char.x, char.y = sx, sy
            char.vx = 0.0
            char.vy = 0.0
            char.path_waypoints.clear()
            char.speech_bubble = ""
            char.speech_timer = 0.0
            char.arrested = False

        day_key = f"loop{self.loop_id}_day{self.current_day}_intro"
        self.add_clue(
            day_key,
            f"Day {self.current_day}/7 ({self.get_day_name()} — {self.scenario['title']}): {self.scenario['motive']}",
        )

    def get_char_scene(self, char: SimCharacter) -> str:
        """
        Returns which scene a character currently belongs to:
        - `"OVERWORLD"`: Outside on the streets, sidewalks, wynds, and courtyards of Dunwick-on-Severn.
        - `building_id` (`"home"`, `"cafe"`, `"office"`, `"school"`, `"market"`, `"park"`): Inside that building.
        """
        if char.is_player:
            return self.active_scene
        for b in BUILDINGS:
            rx, ry, rw, rh = b["rect"]
            if (rx + 12) <= char.x <= (rx + rw - 12) and (ry + 12) <= char.y <= (ry + rh - 12):
                return b["id"]
        return "OVERWORLD"

    def get_occupants(self, building_id: str) -> list[SimCharacter]:
        """Returns all non-player characters currently inside `building_id`."""
        return [
            c
            for c in self.characters.values()
            if not c.is_player and not c.arrested and self.get_char_scene(c) == building_id
        ]

    def enter_building(self, building_id: str) -> str:
        """
        Transitions the active scene from `"OVERWORLD"` into the dedicated 2.5D Interior Room Scene
        for `building_id`, showing the interior architecture and only the people within that building.
        """
        b = self.buildings.get(building_id)
        if not b:
            return ""
        self.active_scene = building_id
        self.scene_transition_cooldown = 0.45

        player = self.get_player()
        rx, ry, rw, rh = b["rect"]
        is_north = b["door_y"] > ry + rh // 2
        player.x = float(b["door_x"])
        player.y = float(b["door_y"] - 48) if is_north else float(b["door_y"] + 58)
        player.vx = 0.0
        player.vy = 0.0
        player.rig.facing = "N" if is_north else "S"

        self.particles.emit_burst(player.x, player.y - 16, (248, 206, 92), count=18, speed=95.0)
        occupants = self.get_occupants(building_id)
        if occupants:
            occ_names = ", ".join(c.name.split("(")[0].strip() for c in occupants[:4])
            if len(occupants) > 4:
                occ_names += f" +{len(occupants) - 4}"
            occ_desc = f"People Inside ({len(occupants)}): {occ_names}"
        else:
            occ_desc = "Currently unoccupied — inspect stations or step back outside [Bksp]"

        self.scene_banner_text = f"INSIDE: {b['name']}  •  {occ_desc}"
        self.scene_banner_timer = 4.2
        return f"Entered {b['name']}! ({occ_desc}) — Walk to Door or press [BACKSPACE] to Step Outside."

    def exit_building(self) -> str:
        """
        Transitions the active scene from an Interior Room back to the 2.5D `"OVERWORLD"` outside
        that building's front steps.
        """
        if self.active_scene == "OVERWORLD":
            return "You are already outside on the Dunwick Overworld!"
        b = self.buildings.get(self.active_scene)
        self.active_scene = "OVERWORLD"
        self.scene_transition_cooldown = 0.45

        player = self.get_player()
        if b:
            rx, ry, rw, rh = b["rect"]
            is_north = b["door_y"] > ry + rh // 2
            player.x = float(b["door_x"])
            player.y = float(b["door_y"] + 28) if is_north else float(b["door_y"] - 28)
            player.rig.facing = "S" if is_north else "N"
            b_name = b["name"]
        else:
            b_name = "the building"
        player.vx = 0.0
        player.vy = 0.0

        self.particles.emit_burst(player.x, player.y - 16, (108, 224, 245), count=16, speed=85.0)
        self.scene_banner_text = "DUNWICK-ON-SEVERN OVERWORLD  •  HIGH STREET & BOROUGH ESTATES"
        self.scene_banner_timer = 3.2
        return f"Stepped outside {b_name} onto Dunwick-on-Severn Overworld!"

    def switch_active_family_member(self, new_char_id: str, allow_mid_run: bool = False) -> str:
        """
        SOLE-KNOWER RULE:
        During an active campaign, ONLY your chosen character remembers the time loop!
        Your other 3 family members are unawakened human NPCs living their own routines.
        Switching protagonist starts a fresh campaign from their unique perspective if chosen from the menu.
        """
        if new_char_id not in ("arthur", "elena", "maya", "leo"):
            return ""
        if not allow_mid_run and new_char_id != self.player_char_id:
            other_name = self.characters[new_char_id].name
            return (
                f"SOLE-KNOWER LAW: {other_name} does NOT know about the loop! "
                f"Only {self.get_player().name} remembers—talk to {other_name} in-world or press [F] to start a campaign as them!"
            )

        self.player_char_id = new_char_id
        for cid, char in self.characters.items():
            char.is_player = cid == new_char_id
            if char.is_player:
                char.path_waypoints.clear()
                char.vx = 0.0
                char.vy = 0.0
        p = self.get_player()
        self.particles.emit_burst(p.x, p.y - 15, (242, 198, 82), count=16)
        return f"Playing as {p.name} ({self.get_building_name_at(p.x, p.y)})!"

    def get_player(self) -> SimCharacter:
        return self.characters[self.player_char_id]

    def get_in_game_minutes(self) -> int:
        """Maps 0..DAY_DURATION_SECONDS to 0..60 minutes past 5:00 PM (the fatal evening hour)."""
        pct = max(0.0, min(1.0, self.elapsed_time / DAY_DURATION_SECONDS))
        return int(pct * 60.0)

    def get_clock_string(self) -> str:
        mins = self.get_in_game_minutes()
        if mins >= 60:
            return "6:00 PM"
        return f"5:{mins:02d} PM"

    def get_building_name_at(self, x: float, y: float) -> str:
        for b in BUILDINGS:
            rx, ry, rw, rh = b["rect"]
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return b["name"]
        return "HIGH STREET & COBBLESTONE WYNDS"

    def _sync_chapter_from_progress(self):
        zs = self.zone_state
        if zs.get("day_threat_foiled"):
            self.chapter = 5
        elif zs.get("counter_item_crafted") or zs.get("schedule_redirected") or zs.get("specialist_alerted"):
            self.chapter = 4
        elif zs.get("saboteur_identified"):
            self.chapter = 3
        elif zs.get("threat_deduced") or zs.get("witness_interviewed"):
            self.chapter = 2
        else:
            self.chapter = 1

    def get_current_objective(self) -> dict:
        """
        Returns a rich, non-spoiler 1924 Detective & Butterfly Fate summary for the Top HUD.
        Never hands out a mechanical checklist—encourages observing human routines and deducing the threat!
        """
        self._sync_chapter_from_progress()
        zs = self.zone_state
        sc = self.scenario
        day_hdr = f"DAY {self.current_day}/7 ({self.get_day_name().upper()}) • {sc['title']}"

        if zs.get("day_threat_foiled"):
            if self.current_day < TOTAL_DAYS_IN_WEEK:
                return {
                    "chapter_title": f"{day_hdr} — FATE VECTOR FOILED!",
                    "instruction": f"You averted {self.get_day_name()}'s tragedy! Press [G] to advance to {self.get_day_name(self.current_day + 1)} (watch for the Butterfly Effect!).",
                }
            return {
                "chapter_title": f"{day_hdr} — FULL WEEK SURVIVED!",
                "instruction": "Press [G] or [SPACE] to claim your victory over Fate!",
            }

        if not zs.get("threat_deduced"):
            return {
                "chapter_title": f"{day_hdr} — OBSERVE DAILY PATTERNS",
                "instruction": (
                    f"Target: {self.get_protected_target_label()}. Listen to townsfolk conversations & behavioral tells "
                    f"to uncover how Fate strikes before 6:00 PM!"
                ),
            }

        if not zs.get("saboteur_identified"):
            return {
                "chapter_title": f"{day_hdr} — TRACE THE CATALYST",
                "instruction": (
                    f"Rumor: Look for {sc['trace_type']}. Question witnesses ({sc['witness_name']}) or inspect "
                    f"borough stations to identify today's unwitting catalyst!"
                ),
            }

        return {
            "chapter_title": f"{day_hdr} — INTERVENE BEFORE 6:00 PM!",
            "instruction": (
                f"Catalyst: {sc['saboteur_name']}. Foil via: (1) Prepare/Use '{sc['item_clue']}', "
                f"(2) Persuade {sc['saboteur_name']} or Target to shift routine, or (3) Alert {sc['market_name']}!"
            ),
        }

    def _record_day_foiled(self, method_label: str, detail_msg: str):
        """Marks today's Butterfly threat as neutralized and logs the causal ripple for tomorrow!"""
        if self.zone_state.get("day_threat_foiled"):
            return
        self.zone_state["day_threat_foiled"] = True
        self.zone_state["police_clearance_granted"] = True
        self.last_intervention_style = method_label
        for veh in self.grid_engine.vehicles:
            veh.runaway_hazard = False

        self.butterfly_history.append(
            {
                "day": self.current_day,
                "day_name": self.get_day_name(),
                "threat": self.scenario["title"],
                "method": method_label,
                "summary": detail_msg,
            }
        )
        self.add_clue(
            f"foiled_day_{self.current_day}_loop_{self.loop_id}",
            f"{self.get_day_name()} Foiled ({method_label}): {detail_msg}",
        )
        p = self.get_player()
        self.particles.emit_burst(p.x, p.y - 20, (92, 228, 152), count=28, speed=130.0)

        if self.current_day >= TOTAL_DAYS_IN_WEEK:
            self.outcome_state = "VICTORY"
            self.outcome_reason = (
                f"SEVEN DAYS DEFIED (MONDAY TO SUNDAY)! By countering {self.scenario['title']} on Sunday via "
                f"[{method_label}], {p.name} broke the 7-day Butterfly curse on Loop #{self.loop_id} and saved "
                f"{self.get_protected_target_label()}!"
            )

    # =========================================================================
    # 1924 DUNWICK HUMAN DAILY SCHEDULES & BUTTERFLY ROUTE MUTATION
    # =========================================================================
    def _get_scheduled_destination(self, char: SimCharacter, minute: int) -> tuple[float, float, str]:
        sc = self.scenario
        cid = char.id
        protected_id = self.get_protected_target_id()

        # If this NPC was persuaded to shift their schedule today, they stay safely at a calm spot!
        if char.schedule_shifted_today:
            return (char.spawn_x, char.spawn_y, "Altered afternoon routine after your warning")

        # 1. Protected Loved One (in Scenario 3) walks toward today's fatal Butterfly hazard unless redirected!
        if self.scenario_mode == "LOVED_ONE" and cid == protected_id:
            if minute < 18:
                return (char.spawn_x, char.spawn_y, "Starting afternoon routine")
            if minute < 36:
                x, y, lbl = SCHEDULE_LOCATIONS["cafe_tables"]
                return (x, y, f"{lbl} (Unaware of impending danger)")
            haz_key = sc.get("hazard_loc_key", "street_center")
            hx, hy, hlbl = SCHEDULE_LOCATIONS.get(haz_key, SCHEDULE_LOCATIONS["street_center"])
            return (hx, hy, f"{hlbl} [FATE TARGET ZONE!]")

        # 2. Today's Unwitting Catalyst NPC moves between their post, the Bazaar/Cafe, and the Hazard Zone
        if cid == sc.get("saboteur_id"):
            if minute < 14:
                return (char.spawn_x, char.spawn_y, f"At usual post ({char.daily_tell})")
            if minute < 32:
                x, y, _ = SCHEDULE_LOCATIONS["market_tools"]
                return (x + 20.0, y + 12.0, f"Handling {sc['item_clue']} materials at Guildhall Bazaar")
            haz_key = sc.get("hazard_loc_key", "power_room")
            hx, hy, hlbl = SCHEDULE_LOCATIONS.get(haz_key, SCHEDULE_LOCATIONS["power_room"])
            return (hx + 18.0, hy - 12.0, f"Near {hlbl} ({char.daily_tell})")

        # 3. Other Unawakened Family Members live their human 1924 lives
        if char.is_family:
            if cid == "arthur":
                return SCHEDULE_LOCATIONS["home_living"] if minute < 22 else SCHEDULE_LOCATIONS["office_desk"]
            if cid == "elena":
                return SCHEDULE_LOCATIONS["home_study"] if minute < 20 else SCHEDULE_LOCATIONS["cafe_tables"]
            if cid == "maya":
                return SCHEDULE_LOCATIONS["school_lab"] if minute < 35 else SCHEDULE_LOCATIONS["cafe_bar"]
            if cid == "leo":
                return SCHEDULE_LOCATIONS["school_gym"] if minute < 25 else SCHEDULE_LOCATIONS["park_fountain"]

        # 4. Borough Townspeople Schedules (varied slightly by day of the week!)
        day_mod = self.current_day % 2
        if cid == "chloe":
            return SCHEDULE_LOCATIONS["school_lab"] if minute < (20 + day_mod * 6) else SCHEDULE_LOCATIONS["cafe_tables"]
        if cid == "toby":
            return SCHEDULE_LOCATIONS["school_gym"] if minute < 18 else SCHEDULE_LOCATIONS["park_fountain"]
        if cid == "mayor":
            return SCHEDULE_LOCATIONS["cafe_tables"] if minute < 28 else SCHEDULE_LOCATIONS["office_lobby"]
        if cid == "martha":
            return SCHEDULE_LOCATIONS["market_bakery"] if minute < 36 else SCHEDULE_LOCATIONS["cafe_bar"]
        if cid == "jenkins":
            return SCHEDULE_LOCATIONS["cafe_tables"] if minute < 38 else SCHEDULE_LOCATIONS["park_fountain"]
        if cid == "rosa":
            if minute < 20:
                return SCHEDULE_LOCATIONS["street_west"]
            if minute < 40:
                return SCHEDULE_LOCATIONS["street_center"]
            return SCHEDULE_LOCATIONS["street_east"]
        if cid == "dan":
            return SCHEDULE_LOCATIONS["street_east"] if (minute // 15) % 2 == 1 else SCHEDULE_LOCATIONS["street_west"]

        return (char.spawn_x, char.spawn_y, f"At {char.home_building.title()}")

    def update(self, dt: float, move_dir: tuple[float, float]):
        if self.outcome_state is not None:
            return

        self.elapsed_time += dt
        self.time_remaining = max(0.0, DAY_DURATION_SECONDS - self.elapsed_time)

        # Drain async Cloud LLM responses
        for resp in self.llm_broker.poll_responses():
            aid = resp.get("agent_id")
            if aid in self.characters and resp.get("dialogue"):
                npc = self.characters[aid]
                npc.say(resp["dialogue"], duration=6.5)
                act = resp.get("action", "RESUME_ROUTINE")
                if act == "QUESTION_SANITY":
                    self.credibility = max(0, self.credibility - 15)
                elif act in ("SHIFT_SCHEDULE", "ESCORT_PROTECTED", "PREPARE_COUNTERMEASURE", "SURRENDER_CATALYST"):
                    npc.schedule_shifted_today = True
                    if aid in (self.scenario.get("saboteur_id"), self.get_protected_target_id(), self.scenario.get("market_id")):
                        self._record_day_foiled(
                            "AI Persuasion & Routine Shift",
                            f"Persuaded {npc.name} via natural conversation to alter their {self.get_day_name()} routine!",
                        )

        # Update 1920s Steam-Carriages & Omni-Trams
        for veh in self.grid_engine.vehicles:
            veh.update(dt, self.characters)

        # Active Road Traffic Hazard: If player collides with moving steamcars on High Street, Fate strikes!
        if self.active_scene == "OVERWORLD" and not self.pending_fatal_death:
            p = self.get_player()
            for veh in self.grid_engine.vehicles:
                vw = 88 if veh.vtype == "car" else 118
                vh = 38
                if abs(p.x - veh.x) < (vw * 0.5 + 16.0) and abs(p.y - veh.y) < (vh * 0.5 + 18.0):
                    self.trigger_death_sequence("CARRIAGE_CRASH")
                    self.outcome_reason = (
                        f"CRUSHED BY STEAM-CARRIAGE ON HIGH STREET! You stepped directly into the path of an "
                        f"oncoming 4-ton brass steam vehicle moving along the cobblestones. "
                        f"Your consciousness snaps back to Monday Morning (Loop #{self.loop_id + 1})!"
                    )
                    break

        if self.scene_transition_cooldown > 0.0:
            self.scene_transition_cooldown = max(0.0, self.scene_transition_cooldown - dt)
        if self.scene_banner_timer > 0.0:
            self.scene_banner_timer = max(0.0, self.scene_banner_timer - dt)

        # Player Movement & Automatic Doorway Scene-Switching
        player = self.get_player()
        dx, dy = move_dir
        mag = math.hypot(dx, dy)
        if mag > 0.01:
            dx /= mag
            dy /= mag
            player.vx = dx * player.base_speed
            player.vy = dy * player.base_speed
            player.x, player.y = self.grid_engine.move_player_in_scene(
                player.x,
                player.y,
                player.vx * dt,
                player.vy * dt,
                active_scene=self.active_scene,
                radius=11.0,
            )

            # Check if the player walked directly into an Exterior House Door or Interior Exit Door
            if self.scene_transition_cooldown <= 0.0:
                if self.active_scene == "OVERWORLD":
                    for b in BUILDINGS:
                        is_north = b["door_y"] > b["rect"][1] + b["rect"][3] // 2
                        if abs(player.x - b["door_x"]) <= 44.0 and abs(player.y - b["door_y"]) <= 24.0:
                            if (is_north and dy < -0.15) or (not is_north and dy > 0.15):
                                self.enter_building(b["id"])
                                break
                else:
                    b = self.buildings.get(self.active_scene)
                    if b:
                        is_north = b["door_y"] > b["rect"][1] + b["rect"][3] // 2
                        if abs(player.x - b["door_x"]) <= 52.0 and abs(player.y - b["door_y"]) <= 38.0:
                            if (is_north and dy > 0.15) or (not is_north and dy < -0.15):
                                self.exit_building()
        else:
            player.vx = 0.0
            player.vy = 0.0

        # Ambient 1924 Dunwick Chatter (drops organic hints about daily habits & the active Butterfly threat!)
        self.chatter_timer -= dt
        if self.chatter_timer <= 0:
            self.chatter_timer = random.uniform(3.8, 6.2)
            self._emit_neighborhood_chatter()

        # Update all 24 characters
        minute = self.get_in_game_minutes()
        for cid, char in self.characters.items():
            if char.speech_timer > 0:
                char.speech_timer = max(0.0, char.speech_timer - dt)
                if char.speech_timer == 0:
                    char.speech_bubble = ""

            if not char.is_player:
                self._update_npc_schedule_and_path(char, dt, minute)

            if math.hypot(char.vx, char.vy) > 105.0:
                char.step_timer -= dt
                if char.step_timer <= 0:
                    self.particles.emit_step(char.x, char.y)
                    char.step_timer = 0.24

            char.rig.update(char.vx, char.vy, dt, is_speaking=(char.speech_timer > 0))

        # Check if Social Credibility hit 0% (Detained for Galvanic Delirium!)
        if self.credibility <= 0:
            self.outcome_state = "TIME_UP"
            self.outcome_reason = (
                f"PUBLIC HYSTERIA ON {self.get_day_name().upper()}! Because you shouted wild prophecies without "
                f"evidence or composure, Chief Inspector Miller and Sister Joya confined you for 'Galvanic Delirium'. "
                f"While you were detained, {self.scenario['title']} struck! Rewinding to Monday (Loop #{self.loop_id + 1})..."
            )
            return

        # Check end of Day Clock (6:00 PM Bell)
        if self.time_remaining <= 0.0:
            if self.zone_state.get("day_threat_foiled"):
                if self.current_day < TOTAL_DAYS_IN_WEEK:
                    self.advance_to_next_day()
                else:
                    self.outcome_state = "VICTORY"
                    self.outcome_reason = (
                        f"ALL 7 DAYS SURVIVED! You protected {self.get_protected_target_label()} through the entire week!"
                    )
            else:
                self._trigger_fate_catastrophe()

    def _trigger_fate_catastrophe(self):
        """Called when 6:00 PM strikes on Day d and today's Butterfly threat was NOT foiled."""
        self._sync_chapter_from_progress()
        day_str = f"Day {self.current_day}/7 ({self.get_day_name()})"
        sc = self.scenario

        # Flag for cinematic death cutscene instead of abrupt game-over
        self.fatal_death_type = sc.get("hazard_type", "CARRIAGE_CRASH")
        self.pending_fatal_death = True
        self.outcome_state = None  # Handled via cinematic rewind

        if self.scenario_mode == "WORLD_END":
            self.outcome_reason = (
                f"6:00 PM DOOMSDAY ON {day_str.upper()}! [{sc['title']}] went unchecked—{sc['motive']} "
                f"The Imperial Aether-Boiler ruptured and shattered Dunwick-on-Severn! "
                f"Time rewinds to Monday (Loop #{self.loop_id + 1}), and the causal web shifts..."
            )
        elif self.scenario_mode == "SELF_DEATH":
            self.outcome_reason = (
                f"YOU DIED ON {day_str.upper()}! Fate claimed your life via [{sc['title']}]: {sc['motive']} "
                f"Your consciousness snaps back to Monday Morning (Loop #{self.loop_id + 1}) with new Subconscious Echoes!"
            )
        else:
            loved_lbl = self.get_protected_target_label()
            self.outcome_reason = (
                f"TRAGEDY ON {day_str.upper()}! You could not save {loved_lbl} from [{sc['title']}]: {sc['motive']} "
                f"Time rewinds to Monday (Loop #{self.loop_id + 1}). Use your Foresight Journal [N] to outwit the Butterfly Effect!"
            )

    def trigger_death_sequence(self, death_type: str = None):
        """Triggers an immediate cinematic death sequence (e.g. from walking into an unfixed hazard or keypress)."""
        self.fatal_death_type = death_type or self.scenario.get("hazard_type", "CARRIAGE_CRASH")
        self.pending_fatal_death = True
        self.outcome_state = None

    def handle_cinematic_rewind_complete(self):
        """Called by DeathCinematicEngine once the temporal rewind sequence finishes."""
        # 1. Inscribe death into the Sole-Knower's memory journal
        death_entry = {
            "loop": self.loop_id,
            "day": self.current_day,
            "day_name": self.get_day_name(),
            "hazard": self.scenario.get("title", "Fate Catastrophe"),
            "hazard_type": self.fatal_death_type,
            "catalyst": self.scenario.get("saboteur_name", "Unknown"),
            "clue": self.scenario.get("trace_type", "Unknown catalyst"),
        }
        self.death_journal.append(death_entry)

        # 2. Impart subconscious neural perturbations to all 24 citizens
        self.butterfly_eco.handle_temporal_reset(self.fatal_death_type, self.current_day, self.loop_id)

        # 3. Rewind timeline back to Monday morning with Sole-Knower memory retention
        self.start_loop(player_char_id=self.player_char_id, is_new_loop=True, reset_to_monday=True)
        self.pending_fatal_death = False

    def _update_npc_schedule_and_path(self, char: SimCharacter, dt: float, minute: int):
        if char.arrested:
            char.vx = 0.0
            char.vy = 0.0
            char.current_schedule_label = "Detained at Scotland Yard Post"
            return

        if char.id == "hank":
            if self.zone_state["police_clearance_granted"] or self.zone_state["day_threat_foiled"]:
                goal_x, goal_y, label = (2060.0, 360.0, "Standing down per official clearance")
            else:
                goal_x, goal_y, label = (2140.0, 360.0, "Guarding Royal Aether-Works Boiler Gate")
        else:
            goal_x, goal_y, label = self._get_scheduled_destination(char, minute)

        char.current_schedule_label = label

        char.schedule_recalc_timer -= dt
        if char.schedule_recalc_timer <= 0:
            char.schedule_recalc_timer = random.uniform(3.2, 5.5)
            dist_to_goal = math.hypot(goal_x - char.x, goal_y - char.y)
            if dist_to_goal > 28.0:
                char.path_waypoints = self.grid_engine.find_path(char.x, char.y, goal_x, goal_y)
            elif not char.path_waypoints and random.random() < 0.45:
                wx, wy = self.grid_engine.snap_to_nearest_walkable(
                    goal_x + random.uniform(-36.0, 36.0),
                    goal_y + random.uniform(-28.0, 28.0),
                )
                char.path_waypoints = [(wx, wy)]

        if char.path_waypoints:
            tx, ty = char.path_waypoints[0]
            dx = tx - char.x
            dy = ty - char.y
            d = math.hypot(dx, dy)
            if d <= 14.0:
                char.path_waypoints.pop(0)
                char.stuck_timer = 0.0
                if not char.path_waypoints:
                    char.vx = 0.0
                    char.vy = 0.0
            else:
                spd = char.base_speed * 0.72
                char.vx = (dx / d) * spd
                char.vy = (dy / d) * spd
                old_x, old_y = char.x, char.y
                char.x, char.y = self.grid_engine.move_with_sliding(
                    char.x, char.y, char.vx * dt, char.vy * dt, radius=10.0
                )
                if math.hypot(char.x - old_x, char.y - old_y) < spd * dt * 0.25:
                    char.stuck_timer += dt
                    perp_x = -char.vy * dt * 0.85
                    perp_y = char.vx * dt * 0.85
                    char.x, char.y = self.grid_engine.move_with_sliding(char.x, char.y, perp_x, perp_y, radius=10.0)
                    if char.stuck_timer > 0.45:
                        char.path_waypoints.pop(0)
                        char.stuck_timer = 0.0
                else:
                    char.stuck_timer = 0.0
        else:
            char.vx = 0.0
            char.vy = 0.0

    def _emit_neighborhood_chatter(self):
        player = self.get_player()
        nearby = [
            c
            for c in self.characters.values()
            if not c.is_player
            and not c.arrested
            and not c.speech_bubble
            and self.get_char_scene(c) == self.active_scene
            and math.hypot(c.x - player.x, c.y - player.y) < 520.0
        ]
        if not nearby:
            return
        sp = random.choice(nearby)
        sc = self.scenario
        day_name = self.get_day_name()

        # Leo's passive eavesdropping perk: adults mutter candid secrets when Leo is nearby!
        if player.id == "leo" and sp.id in (sc["saboteur_id"], sc["witness_id"]):
            sp.say(f"(Overheard): '...Must be careful with {sc['trace_type'][:36]}...'", duration=4.5)
            return

        if sp.id == sc["saboteur_id"]:
            sp.say(f" Goodness, {day_name} is flying by—I must finish this errand before 6:00 PM!", duration=4.2)
            return
        if sp.id == sc["witness_id"]:
            sp.say(f"Did anyone else notice {sc['trace_type'][:38]}...", duration=4.2)
            return

        flavor_lines = {
            "sal": f"Fresh Darjeeling steaming in the copper urn this {day_name}!",
            "mia": "Mind the hot mutton pie platters—folks are eating in such a rush today!",
            "jenkins": "By my brass chronometer, the Clocktower gears sound strained.",
            "mayor": "Order and British decorum must prevail in Dunwick-on-Severn!",
            "sam": "Every brass valve and brake cotter-pin is logged in my Ironmonger's ledger.",
            "martha": "Freshly baked mutton pies and crumpets at the Crown Bakehouse!",
            "lin": "Keep clear of the top apothecary shelf—those belladonna phials are potent.",
            "zack": "Heavy steam-lorry loads rolling down High Street all afternoon!",
            "clarke": "The Galvanic Analyzer at St. Dunstan's is humming with ley-static.",
            "joya": "My Red Cross triage kit is ready by the Gargoyle Fountain if anyone chokes or falls ill.",
            "miller": "Scotland Yard acts on tangible evidence and calm testimony, not wild rumors.",
            "rosa": "Mind the steam-carriages when crossing High Street!",
        }
        sp.say(flavor_lines.get(sp.id, f"A brisk {day_name} in Dunwick, {player.name.split('(')[0].strip()}!"), duration=4.2)

    def get_nearest_interactable(self, max_dist: float = 108.0) -> tuple[str, object]:
        """
        Scene-aware interaction target finder:
        - Only checks NPCs and interactive stations inside the player's current `active_scene`.
        - Also detects nearby House Entrance Doors (on `"OVERWORLD"`) or the Interior Exit Door (when inside).
        """
        player = self.get_player()
        best_kind = None
        best_target = None
        best_d = max_dist

        for cid, char in self.characters.items():
            if not char.is_player and not char.arrested and self.get_char_scene(char) == self.active_scene:
                d = math.hypot(char.x - player.x, char.y - player.y)
                if d < best_d:
                    best_d = d
                    best_kind = "npc"
                    best_target = char

        if self.active_scene != "OVERWORLD":
            for oid, wobj in self.objects.items():
                if wobj.get("building") != self.active_scene:
                    continue
                d = math.hypot(wobj["x"] - player.x, wobj["y"] - player.y)
                if d < best_d:
                    best_d = d
                    best_kind = "obj"
                    best_target = wobj

            b = self.buildings.get(self.active_scene)
            if b:
                d_door = math.hypot(b["door_x"] - player.x, b["door_y"] - player.y)
                if d_door < min(best_d, 96.0):
                    best_d = d_door
                    best_kind = "door_exit"
                    best_target = b
        else:
            for b in BUILDINGS:
                d_door = math.hypot(b["door_x"] - player.x, b["door_y"] - player.y)
                if d_door < min(best_d, 96.0):
                    best_d = d_door
                    best_kind = "door_enter"
                    best_target = b

        return best_kind, best_target

    # =========================================================================
    # SOLE-KNOWER HUMAN DIALOGUE & NON-REPETITIVE BUTTERFLY INTERACTION
    # =========================================================================
    def get_npc_greeting_and_options(self, npc: SimCharacter) -> tuple[str, list[str]]:
        """
        Generates dynamic, loop-fresh 1920s British dialogue:
        - Other family members DO NOT know about the loop! They speak to you as a normal parent/sibling/spouse.
        - Incorporates Subconscious Dream Echoes on Loop >= 2 so no two loops ever read the same!
        - Shows the NPC's daily behavioral micro-tell.
        """
        p = self.get_player()
        fam_id = p.id
        p_first = p.name.split("(")[0].strip()
        sc = self.scenario
        day_name = self.get_day_name()

        # Automatic Earl Grey Tea rapport & composure boost
        tea_note = ""
        if self.has_warm_coffee:
            self.has_warm_coffee = False
            self.credibility = min(100, self.credibility + 15)
            if fam_id in npc.grudges:
                npc.grudges.remove(fam_id)
                npc.modify_rapport(fam_id, 35)
                tea_note = "(You shared a warm cup of Earl Grey—their alarm melted away!) "
            else:
                npc.modify_rapport(fam_id, 18)
                tea_note = "(You shared a cup of Earl Grey! +18 Rapport & +15 Composure) "

        # Lady Elena's passive perk: automatically spots Behavioral Tells!
        if fam_id == "elena" and npc.id in (sc["saboteur_id"], sc["witness_id"]):
            self.zone_state["threat_deduced"] = True

        # 1. Check if Yarn Spinner has a tailored node for this character (YarnSpinnerTool)
        node_name = f"{npc.id.capitalize()}_Node"
        if node_name in self.yarn_engine.nodes:
            self.yarn_engine.set_variable("player_name", p.name.split("(")[0].strip())
            self.yarn_engine.set_variable("player_id", fam_id)
            self.yarn_engine.set_variable("current_day", self.current_day)
            self.yarn_engine.set_variable("loop_id", self.loop_id)
            self.yarn_engine.set_variable("held_item", self.held_counter_item or "")
            self.yarn_engine.set_variable("credibility", self.credibility)
            self.yarn_engine.set_variable("threat_foiled", self.zone_state.get("day_threat_foiled", False))
            self.yarn_engine.set_variable("threat_deduced", self.zone_state.get("threat_deduced", False))
            self.yarn_engine.start_dialogue(node_name)

            spoken_lines = []
            while not self.yarn_engine.is_waiting_for_choice and not self.yarn_engine.is_finished:
                if self.yarn_engine.current_line:
                    spoken_lines.append(self.yarn_engine.current_line.text)
                self.yarn_engine.advance()

            if spoken_lines and self.yarn_engine.current_options:
                greeting = f"{tea_note}{' '.join(spoken_lines)}"
                options = [opt.text for opt in self.yarn_engine.current_options]
                return greeting, options

        # Check if NPC is alarmed/skeptical of the player
        if fam_id in npc.grudges:
            greeting = (
                f"{tea_note}Good heavens, {p_first}, please compose yourself! After you shouted those frantic "
                f"accusations earlier, I fear you've caught Aether-Fever. Bring me a calming cup of Earl Grey "
                f"from The Brass Kettle—or speak with tangible proof—before I call Sister Joya!"
            )
            options = [
                f"Speak calmly and ask about their {day_name} afternoon routine",
                "Apologize for your frayed nerves (+Composure)",
                "Step back to gather concrete proof or Earl Grey tea",
            ]
            return greeting, options

        # Subconscious echo from previous loops (makes Loop #2, #3, #4 feel eerie and fresh!)
        echo_str = ""
        latest_echo = npc.memory_store.get_latest_echo()
        if latest_echo and self.loop_id > 1:
            clean_echo = latest_echo.split(":", 1)[-1].strip()
            echo_str = f" Strange thing—I woke up this {day_name} with a haunting sensation ({clean_echo})."

        # If speaking to one of the other 3 family members (who do NOT know about the loop!)
        if npc.is_family:
            protected_note = (
                " [PROTECTED LOVED ONE]"
                if (self.scenario_mode == "LOVED_ONE" and npc.id == self.get_protected_target_id())
                else ""
            )
            greeting = (
                f"{tea_note}Hallo, {p_first}!{protected_note} You look awfully pale this {day_name}—did you sleep poorly "
                f"at the Manor? I'm just {npc.current_schedule_label.lower()} ({npc.daily_tell}).{echo_str} "
                f"Is something troubling you, my dear?"
            )
        else:
            rapport = npc.get_rapport(fam_id)
            warmth = (
                f"Delighted to see you this {day_name}, {p_first}!"
                if rapport >= 68
                else f"Good afternoon, {p_first}. The Clocktower reads {self.get_clock_string()}."
            )
            greeting = (
                f"{tea_note}{warmth} [Tell: {npc.daily_tell.capitalize()}].{echo_str} "
                f"I am currently {npc.current_schedule_label.lower()}."
            )

        # Dynamic 4th option based on context
        if self.held_counter_item and npc.id in (sc["saboteur_id"], sc["market_id"], self.get_protected_target_id()):
            fourth_opt = f"Deploy '{self.held_counter_item}' to neutralize {day_name}'s hazard!"
        elif npc.id == self.get_protected_target_id() and self.scenario_mode == "LOVED_ONE":
            fourth_opt = f"Persuade {npc.name.split('(')[0].strip()} to change their {day_name} route & stay safe!"
        else:
            fourth_opt = f"Urgently intervene / Warn them to halt their {day_name} errand!"

        options = [
            f"Observe their {day_name} habits & ask about their afternoon schedule",
            "Ask if they noticed any odd deliveries, hazards, or nervous habits today",
            f"Discuss {sc['title'].title()} & offer a plausible 1924 precaution",
            fourth_opt,
        ]
        return greeting, options

    def select_dialogue_option(self, npc: SimCharacter, option_index: int, custom_text: str = "") -> str:
        p = self.get_player()
        fam_id = p.id
        p_first = p.name.split("(")[0].strip()
        sc = self.scenario
        zs = self.zone_state
        day_name = self.get_day_name()

        # Dispatch custom free-text to the AI Broker
        if custom_text.strip():
            retrieved = [
                {"source": m.source, "score": sc_val, "text": m.text}
                for m, sc_val in npc.memory_store.retrieve_relevant(custom_text, top_k=3)
            ]
            self.llm_broker.submit_agent_dialogue(
                {
                    "agent_id": npc.id,
                    "agent_name": npc.name,
                    "agent_role": npc.role,
                    "persona": npc.bio,
                    "mood_and_tell": npc.daily_tell,
                    "current_action": npc.current_schedule_label,
                    "sector": npc.home_building,
                    "trust": npc.get_rapport(fam_id),
                    "has_anchor": npc.memory_store.has_anchored_memory(),
                    "retrieved_memories": retrieved,
                    "scenario_mode": self.scenario_mode,
                    "day_num": self.current_day,
                    "day_name": day_name,
                    "loop_id": self.loop_id,
                    "daily_hint": sc["trace_type"],
                    "player_id": fam_id,
                    "player_name": p.name,
                    "player_item": self.held_counter_item,
                    "player_message": custom_text,
                }
            )
            return f"Spoke to {npc.name}: \"{custom_text}\" (AI composing response...)"

        # Update Neural Influence Network (adapted from The-Butterfly-)
        self.butterfly_eco.record_interaction(
            npc.id,
            player_composure=self.credibility / 100.0,
            rapport_stimulus=0.5,
            env_tension=self.current_day / 7.0,
            confrontation=0.1 if option_index < 3 else 0.4,
        )

        # Check if Yarn Engine has an active choice waiting
        if self.yarn_engine.is_waiting_for_choice and 0 <= option_index < len(self.yarn_engine.current_options):
            chosen_opt = self.yarn_engine.current_options[option_index]
            self.yarn_engine.select_option(option_index)

            # Synchronize mutated variables back to simulation state
            if self.yarn_engine.get_variable("threat_foiled"):
                self._record_day_foiled("Yarn Dialogue Intervention", f"Averted {sc['title']} with {npc.name} on {day_name}!")
            if self.yarn_engine.get_variable("threat_deduced"):
                zs["threat_deduced"] = True
                zs["saboteur_identified"] = True
            if self.yarn_engine.get_variable("held_item"):
                self.held_counter_item = self.yarn_engine.get_variable("held_item")
            if self.yarn_engine.get_variable("has_warm_tea"):
                self.has_warm_coffee = True

            resp = ""
            if self.yarn_engine.current_line:
                resp = self.yarn_engine.current_line.text
                npc.say(resp, duration=6.0)
            return resp or f"Discussed: {chosen_opt.text}"

        # Handle Skeptical / Alarmed state
        if fam_id in npc.grudges:
            if option_index == 1:
                npc.grudges.remove(fam_id)
                npc.modify_rapport(fam_id, 25)
                self.credibility = min(100, self.credibility + 10)
                line = f"Well... I suppose the coal-fog has everyone on edge this {day_name}, {p_first}. Let us speak calmly."
                npc.say(line, duration=5.5)
                return f"You calmed {npc.name}'s skepticism (+10 Composure)!"
            npc.say("Please, take a breath and speak calmly before you alarm the whole street!", duration=5.0)
            return f"{npc.name} thinks you are frantic! Choose Option [2] to apologize or bring Earl Grey tea."

        npc.modify_rapport(fam_id, 6)
        rapport = npc.get_rapport(fam_id)
        self.particles.emit_burst(npc.x, npc.y - 25, (242, 198, 82), count=10)

        # ---------------------------------------------------------------------
        # OPTION 0: Observe Daily Habits & Afternoon Schedule
        # ---------------------------------------------------------------------
        if option_index == 0:
            if npc.id == sc["saboteur_id"]:
                zs["threat_deduced"] = True
                zs["saboteur_identified"] = True
                line = (
                    f"My {day_name} habit? Pardon my haste, {p_first}—I'm {npc.daily_tell}. "
                    f"Between you and me, I'm dealing with {sc['trace_type']} before the 6:00 PM bell!"
                )
                self.add_clue(
                    f"habit_{self.current_day}_{npc.id}",
                    f"Behavioral Tell ({npc.name}): {npc.daily_tell.capitalize()}—connected to {sc['trace_type']}!",
                )
            elif npc.id == self.get_protected_target_id() and self.scenario_mode == "LOVED_ONE":
                zs["threat_deduced"] = True
                line = (
                    f"My {day_name} plan? I'm {npc.current_schedule_label.lower()}, and shortly I'll be heading "
                    f"toward {SCHEDULE_LOCATIONS[sc['hazard_loc_key']][2].lower()}. Why do you look so worried, {p_first}?"
                )
                self.add_clue(
                    f"loved_route_{self.current_day}",
                    f"Loved One's {day_name} Pattern: {npc.name} is headed straight toward {SCHEDULE_LOCATIONS[sc['hazard_loc_key']][2]}!",
                )
            else:
                line = (
                    f"Every {day_name} at {self.get_clock_string()}, I'm {npc.current_schedule_label.lower()}. "
                    f"Though I did notice {sc['saboteur_hint']} near the thoroughfare earlier!"
                )
                zs["threat_deduced"] = True
            npc.say(line, duration=6.0)
            return f"{npc.name}: \"{line}\""

        # ---------------------------------------------------------------------
        # OPTION 1: Ask About Subtle Anomalies, Deliveries, or Nervous Habits
        # ---------------------------------------------------------------------
        if option_index == 1:
            zs["threat_deduced"] = True
            if npc.id in (sc["witness_id"], "elena", "mia", "sal", "jenkins", "rosa", "toby"):
                zs["witness_interviewed"] = True
                zs["saboteur_identified"] = True
                line = (
                    f"Now that you ask, {p_first}—on this {day_name} I spotted {sc['saboteur_name']} "
                    f"({sc['saboteur_hint']})! Look out for {sc['trace_type']}. You might counter it with "
                    f"'{sc['item_clue']}' or by speaking to {sc['market_name']}!"
                )
                self.add_clue(
                    f"witness_day_{self.current_day}",
                    f"{day_name} Observation ({npc.name}): {sc['saboteur_name']} is the unwitting catalyst for {sc['title']} ({sc['trace_type']}).",
                )
                npc.say(line, duration=6.5)
                return f"CLUE DEDUCED on {day_name}! Catalyst is {sc['saboteur_name']}! Check Journal [N]."

            line = (
                f"People are creatures of habit in Dunwick, {p_first}. Watch closely for {sc['trace_type']}—"
                f"or ask {sc['witness_name']}, who sees everything along that corner!"
            )
            self.add_clue(
                f"lead_day_{self.current_day}",
                f"{day_name} Hint: Ask {sc['witness_name']} or inspect the station linked to {sc['trace_type']}.",
            )
            npc.say(line, duration=6.0)
            return f"{npc.name}: \"{line}\""

        # ---------------------------------------------------------------------
        # OPTION 2: Discuss Precaution / Specialist Aid / Craft Countermeasure
        # ---------------------------------------------------------------------
        if option_index == 2:
            # If speaking to today's Specialist Ally or Polytechnic Scholar / Engineer / Nurse / Inspector
            if npc.id in (sc["market_id"], sc["analyst_id"], "joya", "raj", "clarke", "lin", "miller", "rosa", "sam"):
                if rapport < 58 and not zs["threat_deduced"] and fam_id != "arthur":
                    line = (
                        f"That sounds rather far-fetched for a quiet {day_name}, {p_first}. Observe the actual "
                        f"hazard first (or bring me a warm Earl Grey) so I know where to intervene!"
                    )
                    npc.say(line, duration=5.5)
                    return f"{npc.name} needs a concrete observation first (Try Option [1] or inspect a station)!"

                zs["threat_deduced"] = True
                zs["counter_item_crafted"] = True
                self.held_counter_item = sc["item_clue"]
                self.deja_vu_charges = min(4, self.deja_vu_charges + 1)

                # If this NPC is the exact Specialist for today and we already deduced the threat, they can directly foil it!
                if npc.id == sc["market_id"] and zs["saboteur_identified"]:
                    self._record_day_foiled(
                        f"Specialist Intervention ({npc.name})",
                        f"{npc.name} deployed '{sc['item_clue']}' and neutralized {sc['title']} before 6:00 PM!",
                    )
                    line = (
                        f"Say no more, {p_first}! With {sc['saboteur_name']}'s habit and {sc['trace_type']}, "
                        f"that's a lethal trap! I've deployed the {sc['item_clue']}—{day_name}'s crisis is averted!"
                    )
                    npc.say(line, duration=6.5)
                    return f"{day_name.upper()} SAVED BY {npc.name.upper()}! Press [G] to advance to the next day!"

                line = (
                    f"Good thinking, {p_first}. Take this '{sc['item_clue']}' (+1 Aether-Tuning Charge)! "
                    f"Use it at the hazard station or bring it to {sc['saboteur_name']} / {sc['market_name']}!"
                )
                self.add_clue(
                    f"item_day_{self.current_day}",
                    f"Acquired Countermeasure '{sc['item_clue']}' from {npc.name} for {day_name}'s threat.",
                )
                npc.say(line, duration=6.5)
                return f"PREPARED '{sc['item_clue']}' (+1 Premonition Charge)!"

            line = (
                f"I'm no specialist in {sc['title'].lower()}, {p_first}, but {sc['market_name']} or the "
                f"Polytechnic Lab can prepare a '{sc['item_clue']}' if you ask them!"
            )
            npc.say(line, duration=5.5)
            return f"{npc.name} suggests consulting {sc['market_name']} for '{sc['item_clue']}'."

        # ---------------------------------------------------------------------
        # OPTION 3: Direct Intervention / Redirect Schedule / Deploy Item
        # ---------------------------------------------------------------------
        # Case A: Player is holding the Counter-Item or has deduced the threat and talks to Protected Target / Catalyst / Specialist
        if npc.id in (sc["saboteur_id"], self.get_protected_target_id(), sc["market_id"]):
            if self.held_counter_item or zs["threat_deduced"] or zs["saboteur_identified"] or rapport >= 68:
                npc.schedule_shifted_today = True
                method_type = (
                    f"Countermeasure ({self.held_counter_item})"
                    if self.held_counter_item
                    else f"Schedule Redirection ({npc.name.split('(')[0].strip()})"
                )
                self._record_day_foiled(
                    method_type,
                    f"Intervened with {npc.name} on {day_name} to prevent {sc['title']}!",
                )
                line = (
                    f"Bless my soul, {p_first}—look at that {sc['trace_type']}! You just saved us from a dreadful "
                    f"accident this {day_name}! I'm changing my afternoon routine immediately!"
                )
                npc.say(line, duration=6.5)
                return f"{day_name.upper()} THREAT FOILED! Press [G] to advance to the next day!"
            else:
                # Ungrounded panic lowers Social Credibility!
                loss = 8 if fam_id == "leo" else 18
                self.credibility = max(0, self.credibility - loss)
                npc.add_grudge(fam_id)
                line = (
                    f"What on earth are you shouting about, {p_first}?! Accusing people or demanding I abandon my "
                    f"{day_name} duties without a shred of proof? You sound delirious!"
                )
                npc.say(line, duration=6.0)
                return f"UNGROUNDED PANIC (-{loss}% Composure)! Observe habits (Option [1]/[2]) before intervening!"

        # Case B: Raving at an unrelated bystander without proof
        loss = 6 if fam_id == "leo" else 14
        self.credibility = max(0, self.credibility - loss)
        npc.add_grudge(fam_id)
        line = (
            f"Steady on, {p_first}! Why are you warning me about {sc['title'].lower()}? I have nothing to do "
            f"with that this {day_name}—please calm yourself!"
        )
        npc.say(line, duration=5.5)
        return f"Wrong target! {npc.name} grew alarmed (-{loss}% Composure). Deduce today's Catalyst first!"

    # =========================================================================
    # INTERACTIVE STEAMPUNK STATIONS & PHYSICAL HAZARD DISARMAMENT
    # =========================================================================
    def interact_with_object(self, wobj: dict) -> str:
        oid = wobj["id"]
        sc = self.scenario
        zs = self.zone_state
        p = self.get_player()
        day_name = self.get_day_name()
        self.particles.emit_burst(wobj["x"], wobj["y"], wobj["color"], count=18)

        if oid == "cafe_counter":
            self.has_warm_coffee = True
            self.credibility = min(100, self.credibility + 12)
            # If today's hazard is at the Teahouse (Poisoned Cup, Choking on Mutton Pie, or Steam-Urn), inspecting the counter can also disarm it!
            if sc["hazard_obj"] == "cafe_counter" or sc["alt_obj"] == "cafe_counter":
                zs["threat_deduced"] = True
                if zs["saboteur_identified"] or self.held_counter_item or p.id in ("elena", "maya"):
                    self._record_day_foiled(
                        "Teahouse Inspection & Remedy",
                        f"Cleared the fatal hazard ({sc['trace_type']}) at The Brass Kettle Counter on {day_name}!",
                    )
                    return f"BRASS KETTLE COUNTER: Neutralized {sc['title']}! Press [G] for Next Day!"
                return (
                    f"Poured Earl Grey (+Rapport/+Composure) & spotted a clue: {sc['trace_type']}! "
                    f"(Identify {sc['saboteur_name']} or grab '{sc['item_clue']}' to disarm!)"
                )
            return "Poured a steaming cup of Earl Grey (+18 Rapport with next NPC & +12% Composure)!"

        # Check if this station is today's primary or secondary Butterfly Hazard Station!
        if oid in (sc["hazard_obj"], sc["alt_obj"]):
            zs["threat_deduced"] = True
            zs["saboteur_identified"] = True
            self.add_clue(
                f"station_{self.current_day}_{oid}",
                f"{wobj['name']} ({day_name}): Detected '{sc['trace_type']}' linked to {sc['saboteur_name']}.",
            )
            # Can disarm immediately if holding counter item, or if using protagonist specialty, or on second inspection!
            can_disarm = (
                bool(self.held_counter_item)
                or zs.get("counter_item_crafted")
                or (p.id == "arthur" and oid in ("office_records", "power_generator", "study_notebook"))
                or (p.id == "maya" and oid in ("school_lab_table", "market_ledger"))
                or (p.id == "elena" and oid in ("cafe_counter", "market_ledger", "police_dispatch"))
                or (p.id == "leo")
            )
            if can_disarm:
                self._record_day_foiled(
                    f"Physical Intervention at {wobj['name']}",
                    f"Physically disarmed [{sc['title']}] at {wobj['name']} using '{self.held_counter_item or p.name + ' Specialty'}'!",
                )
                return f"HAZARD FOILED AT {wobj['name'].upper()}! {day_name} is safe—press [G] for Next Day!"
            else:
                self.held_counter_item = sc["item_clue"]
                zs["counter_item_crafted"] = True
                return (
                    f"DEDUCED HAZARD AT {wobj['name'].upper()}: Found {sc['trace_type']}! "
                    f"Prepared '{sc['item_clue']}'—press [E] again or talk to {sc['saboteur_name']} to foil!"
                )

        # Standard helpful station functions on any day
        if oid == "study_notebook":
            zs["home_research_synced"] = True
            zs["threat_deduced"] = True
            self.add_clue(
                f"orrery_day_{self.current_day}",
                f"Manor Orrery ({day_name}): Fate vector '{sc['title']}' centers on {sc['trace_type']}.",
            )
            return f"Manor Brass Orrery: Mapped {day_name}'s Fate Vector ('{sc['title']}') to your Foresight Journal [N]!"

        if oid == "school_lab_table":
            zs["school_lab_calibrated"] = True
            zs["counter_item_crafted"] = True
            self.held_counter_item = sc["item_clue"]
            self.deja_vu_charges = min(4, self.deja_vu_charges + 1)
            return f"St. Dunstan's Galvanic Lab: Synthesized '{sc['item_clue']}' & +1 Aether-Premonition Charge [R]!"

        if oid == "market_ledger":
            zs["market_manifest_logged"] = True
            zs["saboteur_identified"] = True
            self.add_clue(
                f"ledger_day_{self.current_day}",
                f"Guildhall Ledger ({day_name}): Flagged {sc['saboteur_name']} in connection with {sc['item_clue']}.",
            )
            return f"Guildhall Ledger: Identified {sc['saboteur_name']} as {day_name}'s unwitting catalyst!"

        if oid == "office_records":
            zs["office_code_unlocked"] = True
            self.held_counter_item = sc["item_clue"]
            return f"Ministry Difference Engine: Prepared '{sc['item_clue']}' & logged override '{self.shutdown_code}'!"

        if oid == "police_dispatch":
            if zs["threat_deduced"] or zs["saboteur_identified"]:
                self._record_day_foiled(
                    "Scotland Yard Telegraph Dispatch",
                    f"Constabulary patrol intercepted {sc['title']} on {day_name}!",
                )
                return f"SCOTLAND YARD DISPATCH: Constables intercepted {day_name}'s hazard! Press [G] for Next Day!"
            return "Scotland Yard Telegraph: Deduce today's hazard or catalyst first before filing an emergency dispatch!"

        if oid == "power_generator":
            if zs["threat_deduced"] or self.held_counter_item or p.id == "arthur":
                self._record_day_foiled(
                    "Imperial Aether-Boiler Regulator",
                    f"Stabilized the Clocktower Aether-Boiler pressure on {day_name}!",
                )
                return f"IMPERIAL AETHER-BOILER STABILIZED FOR {day_name.upper()}! Press [G] for Next Day!"
            return f"{wobj['name']}: Observe {day_name}'s causal clues first or bring '{sc['item_clue']}'!"

        return f"{wobj['name']}: {wobj['desc']}"

    def trigger_deja_vu_on_npc(self, npc: SimCharacter) -> str:
        """
        Awakens a fleeting Aether-Premonition in an NPC (`[R]`).
        Notice: Only gives them a vivid premonition of TODAY's danger so they help you without
        breaking the Sole-Knower rule across the whole town!
        """
        if self.deja_vu_charges <= 0:
            return "No Aether-Premonition Charges left! Use St. Dunstan's Galvanic Lab to recharge (+1)!"
        self.deja_vu_charges -= 1
        sc = self.scenario
        day_name = self.get_day_name()

        npc.memory_store.inject_chronos_anchor(
            f"Experienced a vivid premonition of {sc['title']} on {day_name}!",
            loop_id=self.loop_id,
        )
        npc.clear_grudges()
        npc.schedule_shifted_today = True
        self.credibility = min(100, self.credibility + 20)
        self.particles.emit_burst(npc.x, npc.y - 20, (92, 238, 165), count=26, speed=120.0)

        if npc.id in (sc["saboteur_id"], self.get_protected_target_id(), sc["market_id"], sc["witness_id"]):
            self._record_day_foiled(
                f"Aether-Premonition Awakening ({npc.name})",
                f"Awakened a premonition in {npc.name}, causing them to avert {sc['title']} on {day_name}!",
            )
            npc.say(
                f"By heavens... I just saw a flash of {sc['title'].lower()} in my mind's eye! I'm halting my errand at once!",
                duration=6.5,
            )
            return f"PREMONITION AWAKENED! {npc.name} foresaw and averted {day_name}'s tragedy! Press [G] for Next Day!"

        self.zone_state["threat_deduced"] = True
        self.zone_state["saboteur_identified"] = True
        self.add_clue(
            f"premonition_{self.current_day}",
            f"Premonition via {npc.name}: {sc['saboteur_name']} is the catalyst for {sc['title']} ({sc['trace_type']}).",
        )
        npc.say(
            f"I felt a sudden chill... Watch out for {sc['saboteur_name']} and {sc['trace_type']} before 6:00 PM!",
            duration=6.0,
        )
        return f"PREMONITION AWAKENED IN {npc.name.upper()}! Revealed {day_name}'s catalyst: {sc['saboteur_name']}!"
