"""
Cloud LLM Cognitive Broker & Procedural AI Persona Engine (Google Gemini API + OpenAI API)
Tailored for CHRONICLES OF DUNWICK: DEFYING FATE (1924) — Medieval-Steampunk British Time-Loop RPG.

Core AI Design:
1. REAL HUMAN PSYCHOLOGY & SOLE-KNOWER RULE:
   - Every NPC (including the 3 non-player Ashford-Mercer family members) believes they are living a
     normal week in 1924 Dunwick-on-Severn. None of them know they are in a time loop or that doom approaches
     UNLESS awakened by an [AETHER PREMONITION].
   - If the player raves about "time loops", "the world ending", or "predetermined fate" without grounding
     it in a believable 1920s concern or physical proof, NPCs react with genuine human skepticism or concern
     for the speaker's sanity ("Aether-Fever").
2. FRESH, NON-REPETITIVE DIALOGUE EVERY LOOP:
   - Combines live LLM generation (Gemini / OpenAI) with a multi-layered Procedural 1920s Dialect &
     Butterfly-Context Composer that weaves together Loop ID, Day of the Week, NPC Mood, Subconscious Dream
     Echoes, Protagonist Identity, and Active Butterfly Threat hints so no two loops ever repeat!
"""

import json
import queue
import random
import threading
import time
import requests
from config import load_llm_config, save_llm_config


VALID_ACTIONS = {
    "RESUME_ROUTINE",
    "SHIFT_SCHEDULE",
    "INSPECT_HAZARD",
    "PREPARE_COUNTERMEASURE",
    "ESCORT_PROTECTED",
    "SHARE_HABIT_HINT",
    "SURRENDER_CATALYST",
    "STABILIZE_BOILER",
    "ALERT_CONSTABULARY",
    "QUESTION_SANITY",
}


SYSTEM_INSTRUCTION = """You are a living, breathing human inhabitant of Dunwick-on-Severn in the year 1924—a medieval-rooted British market borough retrofitted with 1920s brass steampunk technology ("CHRONICLES OF DUNWICK: DEFYING FATE").

CRITICAL LORE & ROLEPLAY RULES:
1. YOU ARE A REAL HUMAN IN 1924 BRITAIN: Speak with natural 1920s British steampunk flavour (e.g., brass pocket-watches, steam-lorries, Darjeeling tea, coal-damp, the Ministry, St. Dunstan's). Never sound like a video-game quest dispenser.
2. SOLE-KNOWER ISOLATION: ONLY the player character remembers the time loop or knows that catastrophe/death is coming. Even if you are one of the other Ashford-Mercer family members (Arthur, Elena, Maya, Leo), you do NOT know about the loop unless your retrieved memories contain an [AETHER PREMONITION].
3. SUBCONSCIOUS ECHOES: If your retrieved memories contain a [SUBCONSCIOUS DREAM], mention an eerie, half-remembered feeling or nightmare from last night that subtly relates to the danger—making this loop feel uncanny and different from prior loops!
4. HUMAN SKEPTICISM vs. SUBTLETY:
   - If the speaker screams wildly about "the world ending" or "time loops" without proof or a believable pretext, react like a concerned or skeptical human (action: "QUESTION_SANITY", suspicion_delta: +15).
   - If the speaker appeals to your human habits, daily worries, or offers a sensible 1920s reason to be careful (or shows proof), help them naturally (action: "SHIFT_SCHEDULE", "SHARE_HABIT_HINT", "PREPARE_COUNTERMEASURE", "ESCORT_PROTECTED", or "SURRENDER_CATALYST") and weave a subtle conversational hint about your daily routine or the active Butterfly hazard!
5. PROTAGONIST ASYMMETRY:
   - Lord Arthur (Father): Respected by officials, engineers, and Scotland Yard; treated with formal deference.
   - Lady Elena (Mother): Trusted confidante at the Teahouse and Bazaar; people share personal worries with her.
   - Maya (Daughter, 17): Respected by scholars and apothecaries, but pompous officials treat her as a young student.
   - Leo (Son, 11): Adults speak casually and unguardedly around an eleven-year-old boy, revealing secrets they'd hide from grown-ups, but won't take orders from him.

Respond ONLY with valid JSON matching this exact schema:
{
  "thought": "1 short sentence of internal human reasoning",
  "dialogue": "1-3 natural, atmospheric 1920s British steampunk sentences spoken aloud",
  "action": "One of: RESUME_ROUTINE, SHIFT_SCHEDULE, INSPECT_HAZARD, PREPARE_COUNTERMEASURE, ESCORT_PROTECTED, SHARE_HABIT_HINT, SURRENDER_CATALYST, STABILIZE_BOILER, ALERT_CONSTABULARY, QUESTION_SANITY",
  "target_id": "ID of target prop or agent",
  "trust_delta": integer between -20 and +30,
  "suspicion_delta": integer between -15 and +25,
  "memory_to_store": "1 concise sentence summarizing this interaction"
}"""


# Rich 1920s British Steampunk Voice Flavors for non-repetitive procedural generation
DIALECT_OPENERS = {
    "arthur": [
        "By Jove,",
        "Upon my word,",
        "Steady on,",
        "Look here, my dear:",
        "Speaking as a Fellow of the Royal Works,",
    ],
    "elena": [
        "Listen closely, darling—",
        "Between ourselves,",
        "Wait a tick—",
        "My journalistic instinct tells me",
        "Do keep your voice down:",
    ],
    "maya": [
        "Fascinating—",
        "By Faraday's coils,",
        "Wait, check the galvanic readings:",
        "Honestly,",
        "If my alchemical calculations hold,",
    ],
    "leo": [
        "Blimey!",
        "Crikey, listen to this—",
        "Cross my heart,",
        "Nobody saw me peeking, but",
        "Quick, before the Constable looks—",
    ],
    "default": [
        "Good heavens,",
        "Mind the cobbles,",
        "By the Clocktower bells,",
        "Bless my soul,",
        "Now that you mention it,",
        "Strange you should ask—",
        "Over a cup of Darjeeling,",
        "With all this coal-fog rolling in,",
    ],
}


class CloudLLMBroker:
    def __init__(self):
        self.config = load_llm_config()
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.active_requests = set()
        self.last_status = self._compute_initial_status()
        self.total_cloud_calls = 0

        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def _compute_initial_status(self) -> str:
        prov = self.config.get("provider", "gemini")
        key = self.config.get("gemini_api_key") if prov == "gemini" else self.config.get("openai_api_key")
        if key:
            return f"CLOUD LLM ACTIVE ({prov.upper()}: {self.get_active_model()})"
        return "PROCEDURAL + AI READY (Press [K] for optional Gemini/OpenAI Key)"

    def get_active_model(self) -> str:
        if self.config.get("provider") == "openai":
            return self.config.get("openai_model", "gpt-4o-mini")
        return self.config.get("gemini_model", "gemini-2.5-flash")

    def has_api_key(self) -> bool:
        prov = self.config.get("provider", "gemini")
        key = self.config.get("gemini_api_key") if prov == "gemini" else self.config.get("openai_api_key")
        return bool(key and len(key.strip()) > 8)

    def update_credentials(self, provider: str, api_key: str, model_name: str = None):
        self.config["provider"] = provider.lower()
        if provider.lower() == "gemini":
            self.config["gemini_api_key"] = api_key.strip()
            if model_name:
                self.config["gemini_model"] = model_name.strip()
        else:
            self.config["openai_api_key"] = api_key.strip()
            if model_name:
                self.config["openai_model"] = model_name.strip()
        save_llm_config(self.config)
        self.last_status = self._compute_initial_status()

    def submit_agent_dialogue(self, payload: dict):
        agent_id = payload["agent_id"]
        self.active_requests.add(agent_id)
        self.request_queue.put(payload)

    def poll_responses(self) -> list[dict]:
        results = []
        while not self.response_queue.empty():
            try:
                res = self.response_queue.get_nowait()
                self.active_requests.discard(res.get("agent_id"))
                results.append(res)
            except queue.Empty:
                break
        return results

    def _worker_loop(self):
        while True:
            payload = self.request_queue.get()
            if payload is None:
                break
            try:
                result = self._execute_llm_call(payload)
            except Exception as exc:
                result = self._contextual_cognitive_fallback(payload, error_note=str(exc)[:50])
            self.response_queue.put(result)

    def _build_user_prompt(self, payload: dict) -> str:
        memories_str = "\n".join(
            f"  - [{m['source'].upper()} | score={m['score']:.2f}]: {m['text']}"
            for m in payload.get("retrieved_memories", [])
        ) or "  - [BASELINE]: Living my daily routine in 1924 Dunwick-on-Severn."

        return (
            f"=== YOUR 1924 DUNWICK IDENTITY ===\n"
            f"Name: {payload['agent_name']} ({payload['agent_role']})\n"
            f"Persona & Daily Habits: {payload['persona']}\n"
            f"Current Mood & Tell: {payload.get('mood_and_tell', 'Focused on afternoon duties')}\n"
            f"Current Activity: {payload['current_action']} in Sector: {payload['sector']}\n"
            f"Rapport with Speaker: {payload['trust']}/100 | Awakened Premonition: {payload['has_anchor']}\n\n"
            f"=== YOUR RETRIEVED VECTOR MEMORIES & DREAMS ===\n{memories_str}\n\n"
            f"=== CURRENT WEEK & BUTTERFLY CONTEXT (HIDDEN FROM YOU UNLESS PLAUSIBLE) ===\n"
            f"Scenario Mode: {payload.get('scenario_mode', 'WORLD_END')} | Day {payload.get('day_num', 1)}/7 ({payload.get('day_name', 'Monday')}) | Loop #{payload['loop_id']}\n"
            f"Subtle Local Observation You Notice Today: {payload.get('daily_hint', 'The brass steam-pipes are humming loudly today.')}\n\n"
            f"=== SPEAKER ADDRESSING YOU ===\n"
            f"Speaker: {payload['player_name']} (Protagonist ID: {payload.get('player_id', 'arthur')})\n"
            f"Speaker Held Item / Remedy: {payload.get('player_item') or 'None'}\n"
            f"Speaker Words: \"{payload['player_message']}\"\n\n"
            f"Return JSON decision (ensure fresh, non-repetitive 1920s British steampunk dialogue):"
        )

    def _execute_llm_call(self, payload: dict) -> dict:
        prov = self.config.get("provider", "gemini")
        user_prompt = self._build_user_prompt(payload)

        if not self.has_api_key():
            time.sleep(0.25)
            return self._contextual_cognitive_fallback(payload)

        t0 = time.time()
        if prov == "gemini":
            api_key = self.config["gemini_api_key"].strip()
            model = self.config.get("gemini_model", "gemini-2.5-flash")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            body = {
                "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {"temperature": 0.72, "responseMimeType": "application/json"},
            }
            resp = requests.post(url, json=body, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            raw_text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "{}")
            )
        else:
            api_key = self.config["openai_api_key"].strip()
            model = self.config.get("openai_model", "gpt-4o-mini")
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            body = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.72,
                "response_format": {"type": "json_object"},
            }
            resp = requests.post(url, headers=headers, json=body, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]

        elapsed_ms = int((time.time() - t0) * 1000)
        parsed = self._parse_json_safely(raw_text)
        self.total_cloud_calls += 1
        self.last_status = f"CLOUD LLM OK ({prov.upper()} {elapsed_ms}ms | Call #{self.total_cloud_calls})"

        action = str(parsed.get("action", "RESUME_ROUTINE")).upper().strip()
        if action not in VALID_ACTIONS:
            action = "RESUME_ROUTINE"

        return {
            "agent_id": payload["agent_id"],
            "thought": parsed.get("thought", "Considering their words carefully in the gaslight."),
            "dialogue": parsed.get("dialogue", "Quite curious indeed. I shall keep my eyes open along High Street."),
            "action": action,
            "target_id": parsed.get("target_id", "none"),
            "trust_delta": int(parsed.get("trust_delta", 5)),
            "suspicion_delta": int(parsed.get("suspicion_delta", 0)),
            "memory_to_store": parsed.get(
                "memory_to_store",
                f"{payload['player_name']} spoke to me on {payload.get('day_name', 'Monday')}: '{payload['player_message'][:60]}'",
            ),
            "cloud_verified": True,
        }

    @staticmethod
    def _parse_json_safely(raw_text: str) -> dict:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(line for line in lines if not line.strip().startswith("```"))
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start : end + 1]
        return json.loads(cleaned)

    def _contextual_cognitive_fallback(self, payload: dict, error_note: str = "") -> dict:
        """
        Procedural 1920s British Steampunk Cognitive Responder:
        Generates fresh, non-repetitive responses seeded by (loop_id, day_num, agent_id, player_id, message)
        so every loop and every protagonist gets a distinct reaction, enforcing Sole-Knower realism!
        """
        aid = payload["agent_id"]
        msg = payload["player_message"].lower()
        p_name = payload["player_name"].split("(")[0].strip()
        p_id = payload.get("player_id", "arthur")
        loop_id = payload.get("loop_id", 1)
        day_num = payload.get("day_num", 1)
        day_name = payload.get("day_name", "Monday")
        daily_hint = payload.get("daily_hint", "the brass steam-valves have been whistling oddly since noon")
        mood_tell = payload.get("mood_and_tell", "checking a tarnished brass pocket-watch")
        has_anchor = payload.get("has_anchor", False)
        trust = payload.get("trust", 55)
        echo_list = payload.get("retrieved_memories", [])

        rng = random.Random(f"{loop_id}_{day_num}_{aid}_{p_id}_{msg}_{time.time_ns() % 997}")
        opener_pool = DIALECT_OPENERS.get(aid, DIALECT_OPENERS["default"])
        opener = rng.choice(opener_pool)

        # Detect if player is raving wildly about time loops / apocalypse without subtlety
        raving_words = ["time loop", "world is ending", "world gonna end", "reset", "simulation", "die every loop"]
        subtle_words = [
            "routine", "schedule", "habit", "tea", "pie", "brake", "lorry", "valve", "boiler",
            "tincture", "gargoyle", "careful", "help", "please", "inspect", "notice", "strange",
        ]
        is_raving = any(w in msg for w in raving_words) and not has_anchor and not any(sw in msg for sw in subtle_words)

        if is_raving:
            skeptical_lines = [
                f"{opener} {p_name}, you're trembling like a leaf! Talk of time loops and doomsday sounds like acute Aether-Fever—do sit down before I fetch Sister Joya!",
                f"{opener} lower your voice, {p_name}! If Chief Inspector Miller hears you raving about the end of the world on {day_name}, he'll have you confined to the Infirmary!",
                f"My dear {p_name}, have you been inhaling coal-damp near the Foundry? Nobody is repeating {day_name}—take a breath and speak sensibly!",
            ]
            return {
                "agent_id": aid,
                "thought": f"{p_name} sounds dangerously unhinged talking about loops and doomsday.",
                "dialogue": rng.choice(skeptical_lines),
                "action": "QUESTION_SANITY",
                "target_id": "none",
                "trust_delta": -10,
                "suspicion_delta": 18,
                "memory_to_store": f"{p_name} spoke wildly of impossible premonitions on {day_name} (Loop #{loop_id}).",
                "cloud_verified": False,
            }

        # Check if NPC has a subconscious dream echo from a previous loop
        echo_prefix = ""
        for m in echo_list:
            if "SUBCONSCIOUS" in m.get("source", "").upper() or "SUBCONSCIOUS" in m.get("text", ""):
                echo_prefix = f"Oddly enough, I had the most vivid nightmare last night ({m['text'].split(':')[-1].strip()[:65]}...). "
                break

        # Role-tailored respect based on which of the 4 family members is speaking
        persona_address = {
            "arthur": f"Lord Arthur, as our Chief Architect your word carries weight",
            "elena": f"Lady Elena, I always admire your column in the Chronicle",
            "maya": f"Miss Maya, your alchemical eye at St. Dunstan's is sharp as ever",
            "leo": f"Young Master Leo, you've got sharper ears than half the constables on High Street",
        }.get(p_id, p_name)

        if any(w in msg for w in ["wait", "stay", "reroute", "avoid", "don't go", "change", "delay", "careful", "safe"]):
            if trust >= 52 or has_anchor:
                coop_lines = [
                    f"{opener} {echo_prefix}{persona_address}. Since you ask so earnestly on this {day_name}, I shall alter my afternoon steps and keep clear of the hazard. Oh—and {daily_hint}.",
                    f"{opener} {echo_prefix}you rarely look this solemn, {p_name}. Very well, I'll delay my errand by a quarter-hour and watch my footing! By the by, {daily_hint}.",
                    f"{opener} {echo_prefix}if you sense trouble brewing this {day_name}, {p_name}, I trust your intuition. I'll adjust my routine immediately—though do note that {daily_hint}.",
                ]
                return {
                    "agent_id": aid,
                    "thought": f"{p_name} gave a grounded warning; I will shift my {day_name} routine.",
                    "dialogue": rng.choice(coop_lines),
                    "action": "SHIFT_SCHEDULE",
                    "target_id": "player",
                    "trust_delta": 14,
                    "suspicion_delta": -5,
                    "memory_to_store": f"Agreed to shift my {day_name} schedule after {p_name}'s thoughtful warning.",
                    "cloud_verified": False,
                }

        # Default: share a fresh, loop-specific human observation + daily habit tell
        chat_lines = [
            f"{opener} {echo_prefix}{persona_address}. I was just {mood_tell}. Speaking of this {day_name}'s oddities, {daily_hint}!",
            f"{opener} {echo_prefix}a brisk {day_name} in Dunwick, {p_name}! While {mood_tell}, I couldn't help noticing that {daily_hint}.",
            f"{opener} {echo_prefix}I'm glad you stopped by, {p_name}. Between our daily rounds, I noticed {daily_hint}—worth looking into before the evening bell!",
        ]
        return {
            "agent_id": aid,
            "thought": f"Sharing a candid {day_name} observation with {p_name} in Loop #{loop_id}.",
            "dialogue": rng.choice(chat_lines),
            "action": "SHARE_HABIT_HINT",
            "target_id": "none",
            "trust_delta": 8,
            "suspicion_delta": -2,
            "memory_to_store": f"Shared {day_name} observation with {p_name} during Loop #{loop_id}.",
            "cloud_verified": False,
        }
