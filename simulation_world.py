"""
Dynamic Mystery, Daily Schedule & Cross-Zone Simulation Engine for MAPLEWOOD LOOP.
Integrates architectural patterns from 5 open-source reference projects:
1. Tiny Life (Ellpeck/TinyLife): Seamless multi-character household switching (Arthur, Elena, Maya, Leo)
   and human-scaled 5:00 PM - 6:00 PM daily schedules with A* commuting across buildings.
2. IsoCity (victorqribeiro/isocity): 2D Tile Matrix navigation along sidewalks/crosswalks and street vehicles.
3. Unknown Horizons (unknown-horizons): Cross-zone backend state persistence (actions in School/Market/Park
   dynamically update terminals and guards in the Town Office).
4. IslandEscape: Per-character relationship & grudge memory tables (NPCs react differently to Dad, Mom,
   Maya, and Leo, and hold grudges if falsely accused).
5. OpenPixel-RPG: Unspoiled runtime detective dialogue and clue progression.
"""

import math
import random
from config import (
    BUILDINGS,
    CHARACTER_SPECS,
    LOOP_DURATION_SECONDS,
    WORLD_HEIGHT,
    WORLD_OBJECTS,
    WORLD_WIDTH,
)
from skeletal_engine import ParticleSystem2D, SkeletalRig2D
from tile_grid_engine import TileGridEngine
from vector_memory import VectorMemoryStore


POSSIBLE_SCENARIOS = [
    {
        "saboteur_id": "zack",
        "saboteur_name": "Courier Zack",
        "saboteur_hint": "someone wearing a blue delivery cap who carries express crates",
        "motive": "paid by an outside competitor to overload the Aether-Core using a Stolen Surge Relay",
        "witness_id": "mia",
        "witness_name": "Waitress Mia",
        "market_id": "sam",
        "market_name": "Shopkeeper Sam",
        "analyst_id": "clarke",
        "analyst_name": "Mr. Clarke",
        "item_clue": "Stolen Surge Relay",
        "trace_type": "high-voltage relay capacitor",
    },
    {
        "saboteur_id": "lin",
        "saboteur_name": "Pharmacist Lin",
        "saboteur_hint": "someone in a teal chemist coat wearing glasses",
        "motive": "pouring corrosive thermal acid into the cooling manifold to cover up an unauthorized lab",
        "witness_id": "sal",
        "witness_name": "Barista Sal",
        "market_id": "martha",
        "market_name": "Baker Martha",
        "analyst_id": "clarke",
        "analyst_name": "Mr. Clarke",
        "item_clue": "Corrosive Coolant Vial",
        "trace_type": "industrial thermal acid residue",
    },
    {
        "saboteur_id": "raj",
        "saboteur_name": "Engineer Raj",
        "saboteur_hint": "a technician in a work cap who knows the generator pressure valves",
        "motive": "blackmailed into locking the relief valves at 6:00 PM to trigger a massive insurance payout",
        "witness_id": "jenkins",
        "witness_name": "Old Man Jenkins",
        "market_id": "sam",
        "market_name": "Shopkeeper Sam",
        "analyst_id": "pam",
        "analyst_name": "Secretary Pam",
        "item_clue": "Rigged Valve Key",
        "trace_type": "magnetic valve override keycard",
    },
    {
        "saboteur_id": "dan",
        "saboteur_name": "Coach Dan",
        "saboteur_hint": "someone in a red athletic jacket who jogs along Main Street",
        "motive": "planting a heavy timer fuse on the Aether-Core to settle secret debts",
        "witness_id": "sal",
        "witness_name": "Barista Sal",
        "market_id": "sam",
        "market_name": "Shopkeeper Sam",
        "analyst_id": "pam",
        "analyst_name": "Secretary Pam",
        "item_clue": "Heavy Timer Fuse",
        "trace_type": "clockwork thermal detonator",
    },
]

# Social spheres for IslandEscape-style per-family-member affinity
SOCIAL_AFFINITY = {
    "arthur": {"vance", "pam", "raj", "hank", "miller", "mayor", "jenkins"},
    "elena": {"sal", "mia", "sam", "martha", "lin", "mayor", "joya"},
    "maya": {"clarke", "higgins", "chloe", "zack", "lin", "joya", "raj"},
    "leo": {"toby", "dan", "rosa", "jenkins", "sal", "martha", "chloe"},
}

# Tiny Life style afternoon schedule waypoints (5:00 PM to 6:00 PM)
SCHEDULE_LOCATIONS = {
    "home_living": (520.0, 360.0, "At Mercer Home"),
    "home_study": (260.0, 560.0, "Studying at Mercer Home"),
    "cafe_bar": (1180.0, 320.0, "At Sunrise Cafe Counter"),
    "cafe_tables": (1380.0, 490.0, "Having coffee at Sunrise Cafe"),
    "cafe_patio": (1290.0, 785.0, "Outside Sunrise Cafe"),
    "office_lobby": (1950.0, 340.0, "At Town Office Reception"),
    "office_desk": (1960.0, 510.0, "Working in Town Office"),
    "power_room": (2215.0, 540.0, "Inside Town Power Room"),
    "school_lab": (265.0, 1285.0, "In High School Science Lab"),
    "school_class": (560.0, 1285.0, "In High School Classroom"),
    "school_gym": (420.0, 1510.0, "At High School Gym"),
    "market_tools": (1135.0, 1255.0, "At Market Hardware Stall"),
    "market_bakery": (1435.0, 1255.0, "At Market Bakery Stall"),
    "market_chem": (1145.0, 1515.0, "At Market Pharmacy"),
    "park_police": (1965.0, 1275.0, "At Police Post in Park"),
    "park_fountain": (2245.0, 1515.0, "Near Town Park Fountain"),
    "street_west": (680.0, 880.0, "Walking along West Main Street"),
    "street_center": (1290.0, 880.0, "Walking along Central Main Street"),
    "street_east": (1920.0, 880.0, "Walking along East Main Street"),
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
        self.perk = spec.get("perk", "Town Resident")
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

        # IslandEscape-style per-family-member relationship & grudge tables
        self.relationships: dict[str, int] = {}
        self.grudges: set[str] = set()
        self.init_relationships()

        self.trust = 85 if self.is_family else 55
        self.speech_bubble = ""
        self.speech_timer = 0.0
        self.path_waypoints: list[tuple[float, float]] = []
        self.current_schedule_label = "Following afternoon routine"
        self.schedule_recalc_timer = random.uniform(0.5, 2.0)
        self.step_timer = 0.0
        self.arrested = False

    def init_relationships(self):
        for fam_id in ("arthur", "elena", "maya", "leo"):
            if self.is_family:
                self.relationships[fam_id] = 95
            elif self.id in SOCIAL_AFFINITY.get(fam_id, set()):
                self.relationships[fam_id] = 72
            else:
                self.relationships[fam_id] = 50
        self.grudges.clear()

    def get_rapport(self, fam_id: str) -> int:
        if fam_id in self.grudges:
            return 10
        return self.relationships.get(fam_id, 50)

    def get_relationship_status(self, fam_id: str) -> str:
        if self.is_family:
            return "MERCER FAMILY"
        if fam_id in self.grudges:
            return "HOLDING A GRUDGE"
        r = self.get_rapport(fam_id)
        if r >= 75:
            return "TRUSTED ALLY"
        if r >= 60:
            return "FRIENDLY"
        return "NEUTRAL"

    def modify_rapport(self, fam_id: str, delta: int):
        cur = self.relationships.get(fam_id, 50)
        self.relationships[fam_id] = max(5, min(100, cur + delta))
        self.trust = self.relationships[fam_id]

    def add_grudge(self, fam_id: str):
        if not self.is_family:
            self.grudges.add(fam_id)
            self.relationships[fam_id] = 10
            self.trust = 10

    def clear_grudges(self):
        self.grudges.clear()
        for fam_id in ("arthur", "elena", "maya", "leo"):
            self.relationships[fam_id] = max(85, self.relationships.get(fam_id, 50))
        self.trust = 90

    def say(self, text: str, duration: float = 5.0):
        self.speech_bubble = text
        self.speech_timer = duration


class SimulationWorld:
    def __init__(self, llm_broker):
        self.llm_broker = llm_broker
        self.particles = ParticleSystem2D()
        self.grid_engine = TileGridEngine()
        self.loop_id = 1
        self.player_char_id = "arthur"

        # Build all 24 characters and snap to walkable tiles
        self.specs_by_id = {s["id"]: s for s in CHARACTER_SPECS}
        self.characters: dict[str, SimCharacter] = {}
        for spec in CHARACTER_SPECS:
            c = SimCharacter(spec, is_player=(spec["id"] == self.player_char_id))
            c.spawn_x, c.spawn_y = self.grid_engine.snap_to_nearest_walkable(c.spawn_x, c.spawn_y)
            c.x, c.y = c.spawn_x, c.spawn_y
            self.characters[spec["id"]] = c

        self.objects = {obj["id"]: dict(obj) for obj in WORLD_OBJECTS}
        self.buildings = {b["id"]: b for b in BUILDINGS}

        # Dynamic Mystery & Cross-Zone State (Changes every campaign!)
        self.scenario = {}
        self.shutdown_code = ""
        self.chapter = 1
        self.substep = 0
        self.notebook_clues: list[str] = []
        self.discovered_flags: set[str] = set()
        self.zone_state: dict[str, bool] = {}
        self.deja_vu_charges = 2
        self.has_warm_coffee = False

        self.elapsed_time = 0.0
        self.time_remaining = LOOP_DURATION_SECONDS
        self.outcome_state = None
        self.outcome_reason = ""
        self.chatter_timer = 3.0

        self.start_new_campaign(player_char_id="arthur")

    def _reset_zone_state(self):
        """Unknown Horizons cross-zone persistence state dictionary."""
        self.zone_state = {
            "home_research_synced": False,
            "witness_interviewed": False,
            "market_manifest_logged": False,
            "saboteur_identified": False,
            "school_lab_calibrated": False,
            "office_code_unlocked": False,
            "evidence_confiscated": False,
            "police_clearance_granted": False,
        }

    def start_new_campaign(self, player_char_id: str = "arthur"):
        """Generates a fresh mystery campaign (new Saboteur, Witness, Analyst, and Passcode)."""
        self.loop_id = 1
        self.chapter = 1
        self.substep = 0
        self.notebook_clues = []
        self.discovered_flags.clear()
        self._reset_zone_state()
        self.deja_vu_charges = 2
        self.has_warm_coffee = False

        self.scenario = random.choice(POSSIBLE_SCENARIOS).copy()
        self.shutdown_code = f"SAFE-{random.randint(100, 999)}"

        for c in self.characters.values():
            c.init_relationships()

        self.add_clue(
            "loop_start",
            "5:00 PM Anomaly: At 6:00 PM sharp, someone sabotages the Aether-Core Generator in the Town Office.",
        )
        self.add_clue(
            "investigation_lead",
            "Lead: Check the Family Research Terminal at Home, ask around Sunrise Cafe & Town Market, and watch NPC schedules.",
        )
        self.start_loop(player_char_id=player_char_id, is_new_loop=False)

    def add_clue(self, flag_key: str, text: str):
        if flag_key not in self.discovered_flags:
            self.discovered_flags.add(flag_key)
            self.notebook_clues.append(text)
        elif text not in self.notebook_clues:
            self.notebook_clues.append(text)

    def start_loop(self, player_char_id: str = None, is_new_loop: bool = True):
        if player_char_id:
            self.player_char_id = player_char_id
        if is_new_loop:
            self.loop_id += 1
            # Grudges reset on a new loop unless anchored, while discovered clues & cross-zone knowledge persist!
            for c in self.characters.values():
                if not c.memory_store.has_anchored_memory():
                    c.grudges.clear()

        self.elapsed_time = 0.0
        self.time_remaining = LOOP_DURATION_SECONDS
        self.outcome_state = None
        self.outcome_reason = ""
        self.has_warm_coffee = False
        self.particles.particles.clear()

        for cid, char in self.characters.items():
            char.is_player = cid == self.player_char_id
            sx, sy = self.grid_engine.snap_to_nearest_walkable(
                char.spawn_x + random.uniform(-10, 10),
                char.spawn_y + random.uniform(-10, 10),
            )
            char.x, char.y = sx, sy
            char.vx = 0.0
            char.vy = 0.0
            char.path_waypoints.clear()
            char.speech_bubble = ""
            char.speech_timer = 0.0
            char.arrested = self.zone_state.get("police_clearance_granted", False) and (
                cid == self.scenario.get("saboteur_id")
            )

    def switch_active_family_member(self, new_char_id: str) -> str:
        """
        Tiny Life style seamless live character switch!
        Switches control between Arthur, Elena, Maya, and Leo in real time without resetting the loop.
        """
        if new_char_id not in ("arthur", "elena", "maya", "leo"):
            return ""
        self.player_char_id = new_char_id
        for cid, char in self.characters.items():
            char.is_player = cid == new_char_id
            if char.is_player:
                char.path_waypoints.clear()
                char.vx = 0.0
                char.vy = 0.0
        p = self.get_player()
        self.particles.emit_burst(p.x, p.y - 15, (85, 220, 255), count=16)
        return f"Switched control to {p.name} ({self.get_building_name_at(p.x, p.y)})!"

    def get_player(self) -> SimCharacter:
        return self.characters[self.player_char_id]

    def get_in_game_minutes(self) -> int:
        """Maps 0..LOOP_DURATION_SECONDS to 0..60 minutes past 5:00 PM."""
        pct = max(0.0, min(1.0, self.elapsed_time / LOOP_DURATION_SECONDS))
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
        return "MAIN STREET & CROSSWALKS"

    def _sync_chapter_from_progress(self):
        """Updates self.chapter (1..5) based on organic detective discoveries."""
        zs = self.zone_state
        if zs["police_clearance_granted"] and zs["office_code_unlocked"]:
            self.chapter = 5
        elif zs["saboteur_identified"] and zs["office_code_unlocked"]:
            self.chapter = 4
        elif zs["saboteur_identified"] or zs["market_manifest_logged"]:
            self.chapter = 3
        elif zs["witness_interviewed"] or zs["home_research_synced"]:
            self.chapter = 2
        else:
            self.chapter = 1

    def get_current_objective(self) -> dict:
        """
        Returns a non-spoiler Detective Investigation Summary for the UI.
        Does NOT reveal the secret Witness or Saboteur names until the player actually discovers them!
        """
        self._sync_chapter_from_progress()
        zs = self.zone_state
        sc = self.scenario

        if not zs["witness_interviewed"] and not zs["market_manifest_logged"]:
            return {
                "chapter_title": "STAGE 1: GATHER NEIGHBORHOOD LEADS",
                "instruction": "Check the Home Research Terminal, interview patrons at Sunrise Cafe, or inspect the Town Market Register.",
            }

        if not zs["saboteur_identified"]:
            return {
                "chapter_title": "STAGE 2: TRACE THE RESTRICTED HARDWARE",
                "instruction": "Cross-check the Sunrise Cafe witness tip with the Town Market Sales Register & shopkeepers.",
            }

        if not zs["office_code_unlocked"]:
            sab_label = sc["saboteur_name"]
            return {
                "chapter_title": f"STAGE 3: DECODE SHUTDOWN KEY (SUSPECT: {sab_label.upper()})",
                "instruction": "Calibrate the High School Science Scanner, then access the Town Office Security Mainframe for the Shutdown Code.",
            }

        if not zs["evidence_confiscated"]:
            return {
                "chapter_title": f"STAGE 4: INTERCEPT {sc['saboteur_name'].upper()}",
                "instruction": f"Track down {sc['saboteur_name']} and confront them in dialogue to seize the {sc['item_clue']}!",
            }

        if not zs["police_clearance_granted"]:
            return {
                "chapter_title": "STAGE 4: OBTAIN POLICE CLEARANCE",
                "instruction": f"Present the confiscated {sc['item_clue']} to Chief Miller or the Police Dispatch Terminal in Town Park.",
            }

        return {
            "chapter_title": f"FINAL STAGE: DISARM THE AETHER-CORE (CODE: {self.shutdown_code})",
            "instruction": f"Enter the Town Office Power Room and use the Generator Console with code {self.shutdown_code} before 6:00 PM!",
        }

    # =========================================================================
    # TINY LIFE DAILY SCHEDULES & ISOCITY A* NAVIGATION
    # =========================================================================
    def _get_scheduled_destination(self, char: SimCharacter, minute: int) -> tuple[float, float, str]:
        """
        Determines where each NPC should be between 5:00 PM (min 0) and 6:00 PM (min 60).
        The secret Saboteur follows an actual physical sabotage route across town!
        """
        sc = self.scenario
        cid = char.id

        # 1. Secret Saboteur's Physical Route (5:00 PM -> Market -> Cafe/Street -> Power Room!)
        if cid == sc.get("saboteur_id"):
            if minute < 15:
                return (char.spawn_x, char.spawn_y, "Acting normal at usual post")
            if minute < 32:
                x, y, _ = SCHEDULE_LOCATIONS["market_tools"]
                return (x + 25.0, y + 15.0, "Picking up concealed package at Town Market")
            if minute < 44:
                x, y, _ = SCHEDULE_LOCATIONS["cafe_patio"]
                return (x, y, "Hurrying past Sunrise Cafe patio")
            x, y, _ = SCHEDULE_LOCATIONS["power_room"]
            return (x, y, "Loitering near the Town Office Power Room!")

        # 2. Non-active Playable Family Members follow helpful autonomous routines
        if char.is_family:
            if cid == "arthur":
                return SCHEDULE_LOCATIONS["home_living"] if minute < 22 else SCHEDULE_LOCATIONS["office_desk"]
            if cid == "elena":
                return SCHEDULE_LOCATIONS["home_study"] if minute < 20 else SCHEDULE_LOCATIONS["cafe_tables"]
            if cid == "maya":
                return SCHEDULE_LOCATIONS["school_lab"] if minute < 35 else SCHEDULE_LOCATIONS["cafe_bar"]
            if cid == "leo":
                return SCHEDULE_LOCATIONS["school_gym"] if minute < 25 else SCHEDULE_LOCATIONS["park_fountain"]

        # 3. Townspeople 5:00 PM - 6:00 PM Daily Schedules
        if cid == "chloe":
            return SCHEDULE_LOCATIONS["school_lab"] if minute < 20 else SCHEDULE_LOCATIONS["cafe_tables"]
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

        # Default: local work station
        return (char.spawn_x, char.spawn_y, f"Working at {char.home_building.title()}")

    def update(self, dt: float, move_dir: tuple[float, float]):
        if self.outcome_state is not None:
            return

        self.elapsed_time += dt
        self.time_remaining = max(0.0, LOOP_DURATION_SECONDS - self.elapsed_time)

        # Drain any async Cloud LLM responses
        for resp in self.llm_broker.poll_responses():
            aid = resp.get("agent_id")
            if aid in self.characters and resp.get("dialogue"):
                self.characters[aid].say(resp["dialogue"], duration=6.5)

        # Update IsoCity street vehicles (yielding smoothly to pedestrians on crosswalks)
        for veh in self.grid_engine.vehicles:
            veh.update(dt, self.characters)

        # Smooth Tile-Grid Player Movement with Corner-Sliding
        player = self.get_player()
        dx, dy = move_dir
        mag = math.hypot(dx, dy)
        if mag > 0.01:
            dx /= mag
            dy /= mag
            player.vx = dx * player.base_speed
            player.vy = dy * player.base_speed
            player.x, player.y = self.grid_engine.move_with_sliding(
                player.x, player.y, player.vx * dt, player.vy * dt, radius=11.0
            )
        else:
            player.vx = 0.0
            player.vy = 0.0

        # Ambient neighborhood chatter
        self.chatter_timer -= dt
        if self.chatter_timer <= 0:
            self.chatter_timer = random.uniform(4.0, 6.8)
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

        if self.time_remaining <= 0.0:
            self._sync_chapter_from_progress()
            self.outcome_state = "TIME_UP"
            self.outcome_reason = (
                f"6:00 PM REACHED! The Aether-Core overloaded and rewound Maplewood back to 5:00 PM. "
                f"All {len(self.notebook_clues)} discovered clues and cross-zone security codes remain saved in your Case File for Loop #{self.loop_id + 1}!"
            )

    def _update_npc_schedule_and_path(self, char: SimCharacter, dt: float, minute: int):
        if char.arrested:
            char.vx = 0.0
            char.vy = 0.0
            char.current_schedule_label = "Detained by Maplewood Police"
            return

        # Guard Hank steps aside once Police Clearance is granted!
        if char.id == "hank":
            if self.zone_state["police_clearance_granted"]:
                goal_x, goal_y, label = (2060.0, 360.0, "Cleared Power Room access per Chief Miller")
            else:
                goal_x, goal_y, label = (2140.0, 360.0, "Guarding Power Room entrance")
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
                # Subtle local stroll around scheduled station
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
            if d <= 10.0:
                char.path_waypoints.pop(0)
                if not char.path_waypoints:
                    char.vx = 0.0
                    char.vy = 0.0
            else:
                spd = char.base_speed * 0.68
                char.vx = (dx / d) * spd
                char.vy = (dy / d) * spd
                char.x, char.y = self.grid_engine.move_with_sliding(
                    char.x, char.y, char.vx * dt, char.vy * dt, radius=10.0
                )
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
            and math.hypot(c.x - player.x, c.y - player.y) < 520.0
        ]
        if not nearby:
            return
        sp = random.choice(nearby)
        clock_str = self.get_clock_string()
        lines_by_role = {
            "sal": f"Already {clock_str}! Fresh espresso on the Sunrise Cafe counter!",
            "mia": "Someone seemed awfully nervous near the patio earlier...",
            "jenkins": "My pocket watch never lies—the street lamps flicker right before 6:00 PM.",
            "mayor": "Heading over to the Town Office to check on the afternoon municipal reports.",
            "sam": "Every hardware tool and relay sold today is logged in my Market Register.",
            "martha": "Warm pastries at the Market, and then I'm grabbing coffee at Sunrise Cafe!",
            "lin": "Inventory check complete at the Pharmacy counter.",
            "zack": "Express parcels moving across Main Street all afternoon!",
            "clarke": "The High School Science Scanner is online for frequency calibration.",
            "higgins": "Afternoon clubs wrap up before 6:00 PM, students!",
            "chloe": "Meeting friends at Sunrise Cafe after robotics lab!",
            "toby": "Heading to the Park Fountain before dinner!",
            "vance": "The 6:00 PM Aether-Core load test proceeds unless security proves otherwise.",
            "pam": "The Office Security Mainframe requires a calibrated frequency key from the School Lab.",
            "raj": "Core pressure is rising... someone needs to check the cooling manifold.",
            "hank": (
                "Chief Miller cleared you—go right ahead to the Generator Console!"
                if self.zone_state["police_clearance_granted"]
                else "Power Room is restricted without Police Dispatch clearance!"
            ),
            "miller": "Bring me confiscated physical evidence and I'll lock up the culprit immediately.",
            "rosa": "Remember to use the crosswalks—drivers yield to pedestrians on Main Street!",
            "joya": "Lovely afternoon by the Park Fountain!",
            "dan": "Keeping up my afternoon pace along Main Street!",
        }
        sp.say(lines_by_role.get(sp.id, f"Evening, {player.name.split('(')[0].strip()}!"), duration=4.2)

    def get_nearest_interactable(self, max_dist: float = 108.0) -> tuple[str, object]:
        """Returns ('npc', SimCharacter) or ('obj', dict) for the single closest interactable near the player."""
        player = self.get_player()
        best_kind = None
        best_target = None
        best_d = max_dist

        for cid, char in self.characters.items():
            if not char.is_player and not char.arrested:
                d = math.hypot(char.x - player.x, char.y - player.y)
                if d < best_d:
                    best_d = d
                    best_kind = "npc"
                    best_target = char

        for oid, wobj in self.objects.items():
            d = math.hypot(wobj["x"] - player.x, wobj["y"] - player.y)
            if d < best_d:
                best_d = d
                best_kind = "obj"
                best_target = wobj

        return best_kind, best_target

    # =========================================================================
    # ISLAND-ESCAPE & OPENPIXEL-RPG UNSPOILED DETECTIVE DIALOGUE SYSTEM
    # =========================================================================
    def get_npc_greeting_and_options(self, npc: SimCharacter) -> tuple[str, list[str]]:
        """
        Generates dynamic, unspoiled dialogue tailored to:
        1. Which of the 4 Mercer family members is currently speaking (Arthur, Elena, Maya, Leo)
        2. The NPC's relationship/grudge table with that specific family member
        3. The NPC's current 5:00 PM - 6:00 PM schedule and what they actually know
        """
        p = self.get_player()
        fam_id = p.id
        p_first = p.name.split("(")[0].strip()

        # Automatic coffee rapport boost if player is holding a Warm Espresso
        coffee_note = ""
        if self.has_warm_coffee and not npc.is_family:
            self.has_warm_coffee = False
            if fam_id in npc.grudges:
                npc.grudges.remove(fam_id)
                npc.modify_rapport(fam_id, 35)
                coffee_note = "(You offered a Warm Espresso—they forgave their grudge!) "
            else:
                npc.modify_rapport(fam_id, 18)
                coffee_note = "(You shared a Warm Espresso! +18 Rapport) "

        rapport = npc.get_rapport(fam_id)

        # Check if holding a grudge against THIS family member
        if fam_id in npc.grudges:
            greeting = (
                f"{coffee_note}I have nothing to say to you, {p_first}! You falsely accused me of sabotaging "
                f"the town earlier. Unless another member of your family comes to apologize—or you clear my head "
                f"with a Deja-Vu pulse [R]—I'm not helping you."
            )
            options = [
                "Ask about their 5:00 PM - 6:00 PM schedule anyway",
                "Apologize for the misunderstanding",
                "Step back and switch to another family member [1-4]",
            ]
            return greeting, options

        # Family member check-in
        if npc.is_family:
            greeting = (
                f"{p_first}! I'm currently {npc.current_schedule_label.lower()}. Remember, you can press [1], [2], [3], "
                f"or [4] at any moment to switch directly into my shoes! What should we focus on before 6:00 PM?"
            )
        else:
            affinity_note = (
                f"Always glad to help you, {p_first}!"
                if rapport >= 68
                else f"Hello {p_first}. Make it quick—it's {self.get_clock_string()}."
            )
            greeting = (
                f"{coffee_note}{affinity_note} I'm {npc.name} ({npc.role}), currently {npc.current_schedule_label.lower()}. "
                f"{npc.bio}"
            )

        # Unspoiled, consistent investigative choices for every conversation
        fourth_option = (
            f"Present confiscated {self.scenario['item_clue']} as evidence!"
            if (npc.id == "miller" and self.zone_state["evidence_confiscated"])
            else "Confront / Accuse of plotting the 6:00 PM Sabotage!"
        )
        options = [
            "Ask about their 5:00 PM - 6:00 PM schedule & alibi",
            "Ask if they saw anyone suspicious or unusual orders today",
            "Discuss the Aether-Core Generator & cross-zone security",
            fourth_option,
        ]
        return greeting, options

    def select_dialogue_option(self, npc: SimCharacter, option_index: int, custom_text: str = "") -> str:
        """
        Evaluates the player's investigative question without hand-holding spoilers.
        Updates npc.greeting in-place or returns a clear discovery summary.
        """
        p = self.get_player()
        fam_id = p.id
        p_first = p.name.split("(")[0].strip()
        sc = self.scenario
        zs = self.zone_state

        # If player typed a custom prompt, also dispatch to Cloud LLM Broker
        if custom_text.strip():
            self.llm_broker.submit_agent_dialogue(
                {
                    "agent_id": npc.id,
                    "agent_name": npc.name,
                    "agent_role": npc.role,
                    "agent_rank": 3,
                    "persona": npc.bio,
                    "current_action": npc.current_schedule_label,
                    "sector": npc.home_building,
                    "agent_item": None,
                    "trust": npc.get_rapport(fam_id),
                    "has_anchor": npc.memory_store.has_anchored_memory(),
                    "retrieved_memories": [],
                    "time_remaining": self.time_remaining,
                    "loop_id": self.loop_id,
                    "reactor_state": self.get_clock_string(),
                    "manifold_state": "Calibrated" if zs["school_lab_calibrated"] else "Uncalibrated",
                    "purge_state": self.shutdown_code if zs["office_code_unlocked"] else "Encrypted",
                    "player_name": p.name,
                    "player_rank": 3,
                    "player_item": None,
                    "player_has_evidence": zs["evidence_confiscated"],
                    "player_message": custom_text,
                }
            )

        # Blocked if NPC holds a grudge against this family member
        if fam_id in npc.grudges:
            npc.say("I told you, I'm not talking to you after that false accusation!", duration=5.0)
            return f"{npc.name} holds a grudge against {p_first}! Switch family members [1-4] or bring Cafe Espresso!"

        npc.modify_rapport(fam_id, 6)
        rapport = npc.get_rapport(fam_id)
        self.particles.emit_burst(npc.x, npc.y - 25, (255, 215, 75), count=12)

        # ---------------------------------------------------------------------
        # OPTION 0: Ask about their 5:00 PM - 6:00 PM schedule & alibi
        # ---------------------------------------------------------------------
        if option_index == 0:
            if npc.id == sc["saboteur_id"]:
                line = (
                    "My schedule? Uh... I was definitely just doing my normal rounds! Don't ask why I stopped by "
                    "the Town Market around 5:20 PM or why I'm heading toward the Town Office before 6:00 PM!"
                )
                self.add_clue(
                    f"alibi_{npc.id}",
                    f"Shaky Alibi: {npc.name} got defensive about visiting the Market at 5:20 PM and the Office before 6:00 PM.",
                )
            else:
                line = (
                    f"Right now at {self.get_clock_string()}, I'm {npc.current_schedule_label.lower()}. "
                    f"Wait—did you notice someone {sc['saboteur_hint']} hurrying between the Market and the Cafe earlier?"
                    if npc.id in (sc["witness_id"], "rosa", "chloe", "toby")
                    else f"At {self.get_clock_string()}, I'm {npc.current_schedule_label.lower()}. Everything on my shift has been routine."
                )
            npc.say(line, duration=6.0)
            return f"{npc.name}: \"{line}\""

        # ---------------------------------------------------------------------
        # OPTION 1: Ask if they saw anyone suspicious or unusual orders today
        # ---------------------------------------------------------------------
        if option_index == 1:
            # 1A. Family check-in
            if npc.is_family:
                zs["home_research_synced"] = True
                line = (
                    f"I checked our notes: someone picked up a restricted component at the Town Market around 5:20 PM "
                    f"and passed by Sunrise Cafe around 5:35 PM. Let's question the staff at Sunrise Cafe and the Market!"
                )
                self.add_clue(
                    "family_briefing",
                    "Family Notes: Suspect visited Town Market (~5:20 PM) and passed Sunrise Cafe (~5:35 PM).",
                )
                npc.say(line, duration=6.0)
                return f"{npc.name}: \"{line}\""

            # 1B. The Cafe Witness!
            if npc.id == sc["witness_id"]:
                zs["witness_interviewed"] = True
                line = (
                    f"Yes! Around 5:32 PM, I saw {sc['saboteur_hint']} rush past Sunrise Cafe carrying a "
                    f"'{sc['item_clue']}' from the Town Market! Ask {sc['market_name']} or check the Market Register!"
                )
                self.add_clue(
                    "witness_clue",
                    f"Witness ({npc.name}): Saw {sc['saboteur_hint']} carrying a '{sc['item_clue']}' from {sc['market_name']}'s stall.",
                )
                npc.say(line, duration=6.5)
                return f"CLUE DISCOVERED from {npc.name}! Check Case File [N]!"

            # 1C. Other Cafe workers point toward the actual Cafe Witness
            if npc.home_building == "cafe":
                line = (
                    f"I was busy behind the counter, {p_first}, but {sc['witness_name']} here at Sunrise Cafe "
                    f"mentioned seeing someone drop a hardware slip near the patio!"
                )
                npc.say(line, duration=6.0)
                return f"{npc.name}: \"{line}\""

            # 1D. The Market Informant!
            if npc.id == sc["market_id"]:
                if rapport < 58 and not zs["witness_interviewed"] and not zs["market_manifest_logged"]:
                    line = (
                        f"I don't hand out customer records to just anyone, {p_first}. Either have Elena ask me, "
                        f"bring me a coffee, or inspect the Market Sales Register yourself!"
                    )
                    npc.say(line, duration=6.0)
                    return f"{npc.name} is guarded (Rapport {rapport}%). Try Elena [2], Cafe Coffee, or the Market Register!"

                zs["market_manifest_logged"] = True
                zs["saboteur_identified"] = True
                line = (
                    f"Checked my ledger for you, {p_first}: the person who acquired the '{sc['item_clue']}' today "
                    f"was {sc['saboteur_name']}! They also left an encrypted calibration chip—take it to the High School Science Lab!"
                )
                self.add_clue(
                    "saboteur_id_clue",
                    f"Market Record ({npc.name}): {sc['saboteur_name']} acquired the '{sc['item_clue']}' ({sc['trace_type']})!",
                )
                npc.say(line, duration=6.5)
                return f"BREAKTHROUGH! {npc.name} identified {sc['saboteur_name']} as the buyer of the {sc['item_clue']}!"

            # 1E. Other Market NPCs point toward the Market Informant or Register
            if npc.home_building == "market" and npc.id != sc["saboteur_id"]:
                line = (
                    f"If you're tracking a restricted tool or chemical order, talk to {sc['market_name']} "
                    f"or inspect the Market Hardware & Chemical Register table!"
                )
                npc.say(line, duration=6.0)
                return f"{npc.name}: \"{line}\""

            # 1F. Street & Park observers give observational clues about the Saboteur's appearance
            if npc.id in ("rosa", "dan", "toby", "chloe", "jenkins") and npc.id != sc["saboteur_id"]:
                line = (
                    f"Now that you mention it, {p_first}, I noticed {sc['saboteur_hint']} walking fast between "
                    f"the Town Market and the Town Office!"
                )
                self.add_clue(
                    "street_sighting",
                    f"Street Sighting ({npc.name}): Spotted {sc['saboteur_hint']} commuting between the Market and Town Office.",
                )
                npc.say(line, duration=6.0)
                return f"Sighting from {npc.name}: Spotted {sc['saboteur_hint']}!"

            line = "I haven't seen anything out of the ordinary here, but people at Sunrise Cafe and the Market talk all day."
            npc.say(line, duration=5.5)
            return f"{npc.name}: \"{line}\""

        # ---------------------------------------------------------------------
        # OPTION 2: Discuss the Aether-Core Generator & cross-zone security
        # ---------------------------------------------------------------------
        if option_index == 2:
            if npc.id in (sc["analyst_id"], "clarke", "pam", "raj"):
                if npc.id == "clarke" or (npc.id == sc["analyst_id"] and not zs["school_lab_calibrated"]):
                    zs["school_lab_calibrated"] = True
                    self.deja_vu_charges += 1
                    line = (
                        f"I've calibrated the High School Science Scanner for {sc['trace_type']} and transmitted the "
                        f"decryption packet to the Town Office Security Mainframe! (+1 Deja-Vu Charge)"
                    )
                    self.add_clue(
                        "lab_calibrated",
                        "Cross-Zone Sync: High School Science Lab transmitted the decryption key to the Town Office Mainframe.",
                    )
                    npc.say(line, duration=6.5)
                    return "CROSS-ZONE SYNC! School Lab unlocked the Town Office Security Mainframe (+1 Deja-Vu)!"

                if zs["school_lab_calibrated"]:
                    zs["office_code_unlocked"] = True
                    line = (
                        f"The School Lab frequency key synced with our Office Mainframe! The emergency Aether-Core "
                        f"Shutdown Code for this timeline is '{self.shutdown_code}'!"
                    )
                    self.add_clue(
                        "shutdown_code",
                        f"Generator Passcode Unlocked: Enter '{self.shutdown_code}' at the Main Power Generator Console.",
                    )
                    npc.say(line, duration=6.5)
                    return f"SHUTDOWN CODE UNLOCKED: '{self.shutdown_code}'!"
                else:
                    line = (
                        "The Town Office Security Mainframe is locked behind an encrypted frequency! Run a scan at "
                        "the High School Science Scanner (or talk to Mr. Clarke) to transmit the calibration key first."
                    )
                    npc.say(line, duration=6.0)
                    return f"{npc.name}: \"{line}\""

            if npc.id == "hank":
                if zs["police_clearance_granted"]:
                    line = f"Chief Miller radioed me, {p_first}! The Power Room is open—use code {self.shutdown_code or '[Check Office Mainframe]'} on the Generator!"
                else:
                    line = "Strict orders: nobody touches the Main Power Generator Console until Chief Miller radios Police Clearance!"
                npc.say(line, duration=6.0)
                return f"Guard Hank: \"{line}\""

            if npc.id == "miller":
                line = (
                    "If someone is plotting to overload the Aether-Core, confront them to seize the physical sabotage "
                    "device and bring it to me (or log it at the Police Dispatch Terminal) so I can make the arrest!"
                )
                npc.say(line, duration=6.0)
                return f"Chief Miller: \"{line}\""

            line = "The Aether-Core Generator is in the Town Office Power Room, guarded by Hank and monitored by Engineer Raj."
            npc.say(line, duration=5.5)
            return f"{npc.name}: \"{line}\""

        # ---------------------------------------------------------------------
        # OPTION 3: Confront / Accuse of Sabotage (or Present Evidence to Police)
        # ---------------------------------------------------------------------
        if npc.id == "miller":
            if zs["evidence_confiscated"]:
                zs["police_clearance_granted"] = True
                self.characters[sc["saboteur_id"]].arrested = True
                line = (
                    f"By George, {p_first}—that's the '{sc['item_clue']}' from {sc['saboteur_name']}! My officers have "
                    f"detained {sc['saboteur_name']}, and I've radioed Guard Hank at the Town Office to let you disarm the Generator!"
                )
                self.add_clue(
                    "police_cleared",
                    f"Police Clearance Granted: {sc['saboteur_name']} arrested! Guard Hank unlocked the Power Room.",
                )
                npc.say(line, duration=6.5)
                return f"ARREST MADE! {sc['saboteur_name']} detained & Power Room unlocked! Go disarm the Generator!"
            else:
                line = (
                    f"I can't arrest a citizen on a hunch, {p_first}! Identify who bought the sabotage hardware, "
                    f"confront them to seize the physical device, and bring that proof to me!"
                )
                npc.say(line, duration=6.0)
                return f"Chief Miller needs physical proof! Confront the Saboteur first to seize the {sc['item_clue']}."

        # Confronting the actual Saboteur!
        if npc.id == sc["saboteur_id"]:
            # Player can catch them if they found the Market/Witness clues OR caught them red-handed at Market/Power Room!
            caught_in_act = self.get_in_game_minutes() >= 18
            if zs["saboteur_identified"] or zs["witness_interviewed"] or caught_in_act:
                zs["saboteur_identified"] = True
                zs["evidence_confiscated"] = True
                line = (
                    f"W-wait, {p_first}! How did you figure out I had the {sc['item_clue']}?! Look, I was "
                    f"{sc['motive']}! Here—take the {sc['item_clue']}, I'm calling the whole thing off!"
                )
                self.add_clue(
                    "confession_evidence",
                    f"Confession & Physical Proof: Seized the '{sc['item_clue']}' from {sc['saboteur_name']}! Take it to Chief Miller in Town Park.",
                )
                self.particles.emit_burst(npc.x, npc.y - 20, (255, 95, 95), count=22)
                npc.say(line, duration=6.5)
                return f"CONFESSION! Seized the '{sc['item_clue']}' from {sc['saboteur_name']}! Take it to Chief Miller in Town Park!"
            else:
                line = (
                    f"Excuse me, {p_first}?! You have zero proof tying me to anything! Come back when you actually "
                    f"have a witness or a sales receipt!"
                )
                npc.say(line, duration=5.5)
                return f"{npc.name} denied everything! Gather a Witness tip (Cafe) or Market receipt first!"

        # Falsely accusing an INNOCENT NPC triggers an IslandEscape Grudge!
        if npc.is_family:
            line = f"Haha, very funny {p_first}! We're family—we're trying to STOP the 6:00 PM explosion together!"
            npc.say(line, duration=5.0)
            return f"{npc.name}: \"{line}\""

        npc.add_grudge(fam_id)
        self.particles.emit_burst(npc.x, npc.y - 20, (255, 70, 70), count=18)
        line = (
            f"How DARE you accuse me of sabotage without a shred of proof, {p_first}! I'm an innocent {npc.role}! "
            f"Don't speak to me again!"
        )
        npc.say(line, duration=6.0)
        return (
            f"FALSE ACCUSATION! {npc.name} is innocent and now holds a GRUDGE against {p_first}! "
            f"(Switch family members [1-4] or use Deja-Vu [R])"
        )

    # =========================================================================
    # UNKNOWN HORIZONS CROSS-ZONE INTERACTIVE TERMINALS
    # =========================================================================
    def interact_with_object(self, wobj: dict) -> str:
        oid = wobj["id"]
        sc = self.scenario
        zs = self.zone_state
        p = self.get_player()
        self.particles.emit_burst(wobj["x"], wobj["y"], wobj["color"], count=18)

        if oid == "study_notebook":
            zs["home_research_synced"] = True
            self.add_clue(
                "home_terminal",
                "Home Research Terminal: Power surge originates from a restricted Market item carried past Sunrise Cafe around 5:32 PM.",
            )
            return "Home Research Terminal: Synced anomaly timeline to your Case File [N] (Check Cafe & Market)!"

        if oid == "cafe_counter":
            self.has_warm_coffee = True
            return "Picked up a Warm Sunrise Espresso! The next townsperson you talk to gains +18 Rapport (or forgives a Grudge)!"

        if oid == "market_ledger":
            zs["market_manifest_logged"] = True
            zs["saboteur_identified"] = True
            self.add_clue(
                "market_ledger_clue",
                f"Market Hardware & Chemical Register: '{sc['item_clue']}' ({sc['trace_type']}) was signed out by {sc['saboteur_name']}!",
            )
            return (
                f"MARKET REGISTER: '{sc['item_clue']}' was acquired by {sc['saboteur_name']}! "
                f"Serial data sent to High School Science Lab!"
            )

        if oid == "school_lab_table":
            zs["school_lab_calibrated"] = True
            self.deja_vu_charges += 1
            self.add_clue(
                "lab_calibrated",
                f"High School Science Scanner: Calibrated for {sc['trace_type']} and unlocked the Town Office Security Mainframe!",
            )
            return (
                "CROSS-ZONE SYNC: High School Science Scanner calibrated (+1 Deja-Vu) & unlocked the Town Office Mainframe!"
            )

        if oid == "office_records":
            if not zs["school_lab_calibrated"] and p.id != "arthur":
                return (
                    "OFFICE MAINFRAME ENCRYPTED: Requires frequency calibration from the High School Science Scanner "
                    "(or Arthur Mercer's Architect override)!"
                )
            zs["school_lab_calibrated"] = True
            zs["office_code_unlocked"] = True
            self.add_clue(
                "shutdown_code",
                f"Office Security Mainframe: Emergency Generator Shutdown Code is '{self.shutdown_code}'.",
            )
            return f"OFFICE MAINFRAME UNLOCKED! Emergency Generator Shutdown Code is '{self.shutdown_code}'!"

        if oid == "police_dispatch":
            if not zs["evidence_confiscated"]:
                return (
                    f"POLICE DISPATCH TERMINAL: Cannot issue arrest warrant without physical evidence! "
                    f"Confront the Saboteur to seize the {sc['item_clue']} first."
                )
            zs["police_clearance_granted"] = True
            self.characters[sc["saboteur_id"]].arrested = True
            self.add_clue(
                "police_cleared",
                f"Police Dispatch Terminal: Warrant executed for {sc['saboteur_name']}! Guard Hank cleared the Power Room.",
            )
            return f"POLICE DISPATCH: {sc['saboteur_name']} arrested! Guard Hank has unlocked the Town Office Power Room!"

        if oid == "power_generator":
            if not zs["police_clearance_granted"]:
                return (
                    "GENERATOR CONSOLE LOCKED BY GUARD HANK: Present confiscated sabotage evidence to Chief Miller "
                    "(or Police Dispatch in Town Park) to get clearance!"
                )
            if not zs["office_code_unlocked"]:
                return (
                    "SHUTDOWN CODE REQUIRED: Access the Office Security Mainframe (after calibrating the High School "
                    "Science Scanner) to retrieve the Shutdown Code!"
                )
            self.chapter = 5
            self.outcome_state = "VICTORY"
            self.outcome_reason = (
                f"TIMELINE SAVED AT {self.get_clock_string()}! Using Shutdown Code '{self.shutdown_code}' and the "
                f"confiscated '{sc['item_clue']}' against {sc['saboteur_name']}, the Mercer family disarmed the "
                f"Aether-Core Generator on Loop #{self.loop_id} and broke the Maplewood time loop!"
            )
            return "AETHER-CORE GENERATOR DISARMED! YOU SAVED MAPLEWOOD HEIGHTS!"

        return f"{wobj['name']}: {wobj['desc']}"

    def trigger_deja_vu_on_npc(self, npc: SimCharacter) -> str:
        if self.deja_vu_charges <= 0:
            return "No Deja-Vu Charges left! Use the High School Science Scanner to synthesize +1 Charge!"
        self.deja_vu_charges -= 1
        npc.memory_store.inject_chronos_anchor("Awakened to the 5:00 PM - 6:00 PM time loop!", loop_id=self.loop_id)
        npc.clear_grudges()
        self.particles.emit_burst(npc.x, npc.y - 20, (80, 245, 155), count=26, speed=120.0)

        sc = self.scenario
        # Awakening an NPC clears any grudges, maxes out their trust with all 4 family members, and shares their deepest insight!
        if npc.id == sc["saboteur_id"]:
            self.zone_state["saboteur_identified"] = True
            self.zone_state["evidence_confiscated"] = True
            self.add_clue(
                "confession_evidence",
                f"Deja-Vu Awakening ({npc.name}): Remembered the 6:00 PM disaster and surrendered the '{sc['item_clue']}'!",
            )
            npc.say("I saw the 6:00 PM explosion in your memory! Take the device—stop the reactor!", duration=6.5)
            return f"DEJA-VU AWAKENED! {npc.name} saw the 6:00 PM explosion and surrendered the {sc['item_clue']}!"

        if npc.id == sc["witness_id"] or npc.home_building == "cafe":
            self.zone_state["witness_interviewed"] = True
            self.add_clue(
                "witness_clue",
                f"Deja-Vu Insight ({npc.name}): Remembered seeing {sc['saboteur_hint']} with a '{sc['item_clue']}' from {sc['market_name']}.",
            )
            npc.say(f"I remember now! Watch out for {sc['saboteur_hint']} near the Market!", duration=6.5)
            return f"DEJA-VU AWAKENED IN {npc.name.upper()}! Forgave all grudges & shared Cafe sighting!"

        if npc.id == sc["market_id"] or npc.home_building == "market":
            self.zone_state["market_manifest_logged"] = True
            self.zone_state["saboteur_identified"] = True
            self.add_clue(
                "saboteur_id_clue",
                f"Deja-Vu Insight ({npc.name}): Confirmed {sc['saboteur_name']} acquired the '{sc['item_clue']}'!",
            )
            npc.say(f"I remember the previous loop! {sc['saboteur_name']} took the {sc['item_clue']}!", duration=6.5)
            return f"DEJA-VU AWAKENED IN {npc.name.upper()}! Identified {sc['saboteur_name']} in Case File [N]!"

        if npc.home_building in ("school", "office"):
            self.zone_state["school_lab_calibrated"] = True
            self.zone_state["office_code_unlocked"] = True
            self.add_clue(
                "shutdown_code",
                f"Deja-Vu Insight ({npc.name}): Recalled emergency Shutdown Code '{self.shutdown_code}'.",
            )
            npc.say(f"I remember the timeline code! It's {self.shutdown_code}!", duration=6.5)
            return f"DEJA-VU AWAKENED IN {npc.name.upper()}! Unlocked Shutdown Code '{self.shutdown_code}'!"

        npc.say("Whoa... I remember the 6:00 PM flash now! All grudges forgiven—I'm with your family!", duration=6.0)
        return f"DEJA-VU AWAKENED IN {npc.name.upper()}! All grudges cleared & Rapport set to 100%!"
