"""
Cloud LLM Cognitive Broker & Event Bus (Google Gemini API + OpenAI API)
Tailored for MAPLEWOOD LOOP: The Mercer Family & Neighborhood AI Simulation.
"""

import json
import queue
import threading
import time
import requests
from config import load_llm_config, save_llm_config


VALID_ACTIONS = {
    "RESUME_ROUTINE",
    "FOLLOW_PLAYER",
    "BARRICADE_DOOR",
    "LOCK_DOOR",
    "UNLOCK_DOOR",
    "STABILIZE_MANIFOLD",
    "INTERCEPT_SABOTEUR",
    "CANCEL_PURGE",
    "GIVE_ITEM",
    "ARREST_PLAYER",
    "CALM_CROWD",
}


SYSTEM_INSTRUCTION = """You are an autonomous character living in the suburban town of Maplewood Heights in a family time-loop game ("MAPLEWOOD LOOP").
THE 4 PLAYABLE FAMILY MEMBERS (The Mercers):
- Arthur Mercer (Dad, Rank 4): Senior Grid Architect at OmniCorp.
- Elena Mercer (Mom, Rank 4): Investigative Journalist & Neighborhood Council Lead.
- Maya Mercer (Teen Sister, 17, Rank 2): High School Robotics & Science Prodigy.
- Leo Mercer (Kid Brother, 11, Rank 1): 6th Grader & Skateboard Scout.

THE NEIGHBORHOOD NPCS:
- Officer Miller (Beat Cop, Rank 4): Patrols the Park & Main Street.
- Director Vance (OmniCorp Boss, Rank 5): Runs OmniCorp Office; triggers the 6:00 PM Grid Surge unless stopped.
- Barista Sal (Parlor Owner, Rank 2): Runs Scoops & Beans Ice Cream/Coffee Parlor; panics at the Park Siren at T-105s.
- Marcus ("Repairman", Rank 2): Undercover saboteur sneaking into the Sub-Station at T-130s with a Rigged Tamper Kit.

DYNAMIC FAMILY & SOCIAL RULES:
1. Nobody knows they are in a time loop UNLESS they have a [CHRONOS ANCHOR] memory in their retrieved vector memories.
2. FAMILY BOND: If you are a Mercer (Arthur, Elena, Maya, Leo) speaking to another Mercer family member, speak warmly like real family! If they mention a code (ARTHUR-77, SURGE-404, DEJA-VU-9), hold evidence, or ask for help urgently, help them:
   - Arthur (Dad) -> action "CANCEL_PURGE" (shut down Executive Grid Control Desk)
   - Maya (Sister) -> action "STABILIZE_MANIFOLD" (fix Transformer Cooling Valve)
   - Leo (Brother) -> action "BARRICADE_DOOR" (lock Sub-Station Gate with bike chain)
   - Elena (Mom) -> action "FOLLOW_PLAYER" or "GIVE_ITEM"
3. TOWN NPC SKEPTICISM:
   - Officer Miller: If 11yo Leo or 17yo Maya screams about explosions WITHOUT physical proof (Rigged Tamper Kit, Leaked Safety Dossier, Executive Keycard) and WITHOUT a secret code, choose "ARREST_PLAYER" (detain them at the Park Kiosk for causing panic). If shown proof or convinced by Arthur/Elena, choose "INTERCEPT_SABOTEUR" (arrest Marcus!).
   - Director Vance: Dismisses kids unless they know PIN "ARTHUR-77" or have a Memory Anchor. When convinced, choose "CANCEL_PURGE".
   - Barista Sal: When told "DEJA-VU-9" or reassured, choose "CALM_CROWD".
   - Marcus (Saboteur): When exposed with code "SURGE-404" or confronted about his Tamper Kit, choose "GIVE_ITEM".

Respond ONLY with valid JSON matching this exact schema:
{
  "thought": "1 short sentence of internal reasoning",
  "dialogue": "1-2 natural, expressive sentences spoken aloud to the player",
  "action": "One of: RESUME_ROUTINE, FOLLOW_PLAYER, BARRICADE_DOOR, LOCK_DOOR, UNLOCK_DOOR, STABILIZE_MANIFOLD, INTERCEPT_SABOTEUR, CANCEL_PURGE, GIVE_ITEM, ARREST_PLAYER, CALM_CROWD",
  "target_id": "ID of target prop or agent",
  "trust_delta": integer between -20 and +35,
  "suspicion_delta": integer between -15 and +25,
  "memory_to_store": "1 concise sentence summarizing this conversation"
}"""


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
        return "AI READY (Press [K] to add optional Gemini/OpenAI Key)"

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
        )
        return (
            f"=== YOUR IDENTITY ===\n"
            f"Name: {payload['agent_name']} ({payload['agent_role']}, Authority Rank {payload['agent_rank']})\n"
            f"Persona: {payload['persona']}\n"
            f"Current Activity: {payload['current_action']} in Building: {payload['sector']}\n"
            f"Holding Item: {payload['agent_item'] or 'None'}\n"
            f"Trust in Speaker: {payload['trust']}/100 | Has Deja-Vu Memory Anchor: {payload['has_anchor']}\n\n"
            f"=== YOUR VECTOR MEMORIES ===\n{memories_str}\n\n"
            f"=== NEIGHBORHOOD STATUS ===\n"
            f"Time Until 6:00 PM Grid Overload: {payload['time_remaining']:.0f}s (Loop #{payload['loop_id']})\n"
            f"Transformer Core: {payload['reactor_state']} | Cooling Valve: {payload['manifold_state']} | Office Grid Desk: {payload['purge_state']}\n\n"
            f"=== FAMILY MEMBER SPEAKING TO YOU ===\n"
            f"Speaker: {payload['player_name']} (Authority Rank {payload['player_rank']})\n"
            f"Speaker Held Item / Proof: {payload['player_item'] or 'None'}\n"
            f"Speaker Message: \"{payload['player_message']}\"\n\n"
            f"Return JSON decision:"
        )

    def _execute_llm_call(self, payload: dict) -> dict:
        prov = self.config.get("provider", "gemini")
        user_prompt = self._build_user_prompt(payload)

        if not self.has_api_key():
            time.sleep(0.35)
            return self._contextual_cognitive_fallback(payload)

        t0 = time.time()
        if prov == "gemini":
            api_key = self.config["gemini_api_key"].strip()
            model = self.config.get("gemini_model", "gemini-2.5-flash")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            body = {
                "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"},
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
                "temperature": 0.4,
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
            "thought": parsed.get("thought", "Thinking about what my neighbor just said."),
            "dialogue": parsed.get("dialogue", "Got it! Let's look into this."),
            "action": action,
            "target_id": parsed.get("target_id", "none"),
            "trust_delta": int(parsed.get("trust_delta", 5)),
            "suspicion_delta": int(parsed.get("suspicion_delta", 0)),
            "memory_to_store": parsed.get(
                "memory_to_store",
                f"{payload['player_name']} told me: '{payload['player_message'][:60]}'",
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
        Rich family-and-neighborhood cognitive responder when running without an external API key
        or if offline, ensuring every family member and town NPC reacts dynamically to who you chose!
        """
        aid = payload["agent_id"]
        msg = payload["player_message"].lower()
        p_name = payload["player_name"].split("(")[0].strip()
        p_rank = payload["player_rank"]
        has_evidence = payload.get("player_has_evidence", False)
        has_anchor = payload.get("has_anchor", False)
        trust = payload.get("trust", 35)

        knows_404 = "404" in msg or "surge" in msg or "valve" in msg
        knows_77 = "77" in msg or "arthur-77" in msg or "pin" in msg or "override" in msg
        knows_deja = "deja" in msg or "vu" in msg or "lab" in msg
        mentions_danger = any(
            w in msg
            for w in ["explode", "overload", "sabotage", "marcus", "loop", "die", "transformer", "help", "stop", "grid", "arrest", "lock"]
        )

        convinced = has_anchor or has_evidence or knows_404 or knows_77 or knows_deja or p_rank >= 4 or trust >= 60

        # 1. DAD (ARTHUR MERCER)
        if aid == "arthur":
            if convinced or mentions_danger:
                return {
                    "agent_id": aid,
                    "thought": f"{p_name} is my family and knows about the OmniCorp Grid flaw! I must shut down the Executive Desk!",
                    "dialogue": f"I believe you, {p_name}! I'm sprinting to the OmniCorp Office right now to enter PIN ARTHUR-77 and shut down the Grid Surge!",
                    "action": "CANCEL_PURGE",
                    "target_id": "office_terminal",
                    "trust_delta": 30,
                    "suspicion_delta": -10,
                    "memory_to_store": f"{p_name} warned me about the 6:00 PM Grid Surge; rushing to shut down the Office Desk.",
                    "cloud_verified": False,
                }
            return {
                "agent_id": aid,
                "thought": f"Chatting warmly with {p_name}.",
                "dialogue": f"Hey {p_name}! Take my OmniCorp Keycard if you need to check the Office, or let me know if something's wrong.",
                "action": "GIVE_ITEM",
                "target_id": "player",
                "trust_delta": 15,
                "suspicion_delta": 0,
                "memory_to_store": f"Checked in with {p_name}.",
                "cloud_verified": False,
            }

        # 2. MOM (ELENA MERCER)
        if aid == "elena":
            if convinced or mentions_danger:
                return {
                    "agent_id": aid,
                    "thought": f"{p_name} needs backup exposing the OmniCorp cover-up!",
                    "dialogue": f"Stay safe, {p_name}! I've got your back—grab my Leaked Safety Dossier from Maplewood Mart and let's get Officer Miller to arrest Marcus!",
                    "action": "FOLLOW_PLAYER",
                    "target_id": "player",
                    "trust_delta": 30,
                    "suspicion_delta": -10,
                    "memory_to_store": f"Teamed up with {p_name} to stop the OmniCorp transformer cover-up.",
                    "cloud_verified": False,
                }

        # 3. TEEN SISTER (MAYA MERCER)
        if aid == "maya":
            if convinced or mentions_danger:
                return {
                    "agent_id": aid,
                    "thought": f"{p_name} confirmed the voltage spike! My Science Lab Capacitor can stabilize the Transformer Valve!",
                    "dialogue": f"No way—SURGE-404 matches my oscilloscope readings, {p_name}! I'm running to the Sub-Station right now to stabilize the Cooling Valve!",
                    "action": "STABILIZE_MANIFOLD",
                    "target_id": "cooling_valve",
                    "trust_delta": 30,
                    "suspicion_delta": -10,
                    "memory_to_store": f"{p_name} warned me about the Transformer; sprinting to fix the Cooling Valve!",
                    "cloud_verified": False,
                }

        # 4. KID BROTHER (LEO MERCER)
        if aid == "leo":
            if convinced or mentions_danger:
                return {
                    "agent_id": aid,
                    "thought": f"Awesome—{p_name} believes me! I'll lock the Sub-Station Gate with my Heavy Bike Chain!",
                    "dialogue": f"I knew that repairman Marcus was shady, {p_name}! I'm sprinting to the Sub-Station Gate to lock it with my Bike Chain!",
                    "action": "BARRICADE_DOOR",
                    "target_id": "office_door",
                    "trust_delta": 30,
                    "suspicion_delta": -10,
                    "memory_to_store": f"{p_name} asked me to barricade the Sub-Station Gate against Marcus.",
                    "cloud_verified": False,
                }

        # 5. OFFICER MILLER (POLICE)
        if aid == "kael":
            if convinced:
                return {
                    "agent_id": aid,
                    "thought": "Solid evidence of utility sabotage in Maplewood Heights! Time to arrest Marcus!",
                    "dialogue": f"Good eye, {p_name}! That tamper evidence is all I need. I'm heading out right now to arrest 'Repairman' Marcus!",
                    "action": "INTERCEPT_SABOTEUR",
                    "target_id": "vesper",
                    "trust_delta": 35,
                    "suspicion_delta": -15,
                    "memory_to_store": f"{p_name} showed proof of Marcus's sabotage; moving to arrest Marcus.",
                    "cloud_verified": False,
                }
            elif mentions_danger and p_rank <= 2:
                return {
                    "agent_id": aid,
                    "thought": f"This kid ({p_name}) is trying to start a town-wide panic without any proof.",
                    "dialogue": f"Whoa there, {p_name}! Spreading stories about explosions without proof isn't funny. Come sit at the Police Kiosk while I call your parents!",
                    "action": "ARREST_PLAYER",
                    "target_id": "police_kiosk",
                    "trust_delta": -15,
                    "suspicion_delta": 25,
                    "memory_to_store": f"Grounded {p_name} at the Park Kiosk for causing unverified panic.",
                    "cloud_verified": False,
                }

        # 6. DIRECTOR VANCE (OMNICORP BOSS)
        if aid == "vaelen":
            if convinced:
                return {
                    "agent_id": aid,
                    "thought": "They have Executive Override ARTHUR-77 or hard safety proof! I must abort the 6:00 PM Grid Surge!",
                    "dialogue": f"Hold everything—override ARTHUR-77 confirmed! I'm aborting the 6:00 PM Max-Power Grid Surge at my desk immediately!",
                    "action": "CANCEL_PURGE",
                    "target_id": "office_terminal",
                    "trust_delta": 35,
                    "suspicion_delta": -15,
                    "memory_to_store": f"{p_name} proved the grid hazard; I aborted the 6:00 PM OmniCorp Surge.",
                    "cloud_verified": False,
                }
            elif mentions_danger:
                return {
                    "agent_id": aid,
                    "thought": "I don't shut down OmniCorp's grid without Arthur's Executive PIN or an official safety dossier.",
                    "dialogue": f"Listen here, {p_name}: unless you have Architect PIN 'ARTHUR-77' or an official Safety Dossier, the 6:00 PM Grid Surge stays on schedule!",
                    "action": "RESUME_ROUTINE",
                    "target_id": "none",
                    "trust_delta": -10,
                    "suspicion_delta": 12,
                    "memory_to_store": f"Refused {p_name}'s unverified request to halt the Grid Surge.",
                    "cloud_verified": False,
                }

        # 7. BARISTA SAL (PARLOR OWNER)
        if aid == "malakor":
            if convinced or knows_deja:
                return {
                    "agent_id": aid,
                    "thought": "They knew about DEJA-VU-9! I shouldn't panic and pull the Park Emergency Siren!",
                    "dialogue": f"You know about DEJA-VU-9 too, {p_name}?! Okay, deep breaths—I promise I won't panic and pull the Park Siren when the lights flicker!",
                    "action": "CALM_CROWD",
                    "target_id": "town_siren",
                    "trust_delta": 30,
                    "suspicion_delta": -10,
                    "memory_to_store": f"{p_name} reassured me; I won't trigger a panic at the Park Siren.",
                    "cloud_verified": False,
                }

        # 8. MARCUS ("REPAIRMAN" SABOTEUR)
        if aid == "vesper":
            if convinced or "tamper" in msg or "404" in msg or "saboteur" in msg:
                return {
                    "agent_id": aid,
                    "thought": "They caught me red-handed and know about SURGE-404! Better hand over the Tamper Kit and bail!",
                    "dialogue": f"Alright, alright, keep your voice down, {p_name}! Take the Rigged Tamper Kit—I'm calling off the Sub-Station job!",
                    "action": "GIVE_ITEM",
                    "target_id": "player",
                    "trust_delta": 25,
                    "suspicion_delta": 0,
                    "memory_to_store": f"{p_name} exposed my cover; I surrendered the Rigged Tamper Kit.",
                    "cloud_verified": False,
                }

        return {
            "agent_id": aid,
            "thought": f"Having a friendly neighborhood chat with {p_name}.",
            "dialogue": f"Lovely afternoon in Maplewood Heights, {p_name}! Let me know if you find any clues around town.",
            "action": "RESUME_ROUTINE",
            "target_id": "none",
            "trust_delta": 5,
            "suspicion_delta": 0,
            "memory_to_store": f"Chatted with {p_name}.",
            "cloud_verified": False,
        }
