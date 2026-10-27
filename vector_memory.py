"""
Long-Term Vector Memory Store, Subconscious Loop Echoes & Butterfly-Effect Memory Engine.
Uses NumPy semantic/hashed feature embeddings with cosine-similarity retrieval,
powering non-repetitive AI NPC interactions across loops and across the 7-day week.
"""

import re
import time
import hashlib
import numpy as np


EMBED_DIM = 64

# 16 Domain-specific semantic concept clusters for 1924 Dunwick-on-Severn & Butterfly Effect scenarios
CONCEPT_CLUSTERS = [
    ["aether", "boiler", "reactor", "overload", "explode", "detonate", "ley", "foundry", "doomsday", "world"],
    ["steam", "valve", "pressure", "manifold", "coal", "gas", "damper", "pipe", "burst", "scald"],
    ["assassin", "sniper", "blade", "poison", "dart", "murder", "kill", "shadow", "marksman", "stalk"],
    ["carriage", "lorry", "tram", "crash", "brake", "pin", "wheel", "crosswalk", "runaway", "swerve"],
    ["choke", "suffocate", "food", "pie", "mutton", "tart", "swallow", "cough", "crust", "bakehouse"],
    ["tincture", "belladonna", "nightshade", "apothecary", "vial", "antidote", "remedy", "dose", "chemist"],
    ["gargoyle", "masonry", "stone", "collapse", "scaffold", "roof", "clocktower", "fall", "crush"],
    ["galvanic", "coil", "arc", "voltage", "shock", "polytechnic", "alchemical", "lab", "oscilloscope"],
    ["constable", "scotland", "yard", "miller", "warrant", "arrest", "detain", "patrol", "whistle", "guard"],
    ["habit", "routine", "schedule", "tea", "darjeeling", "earl", "grey", "watch", "hurry", "nervous"],
    ["loop", "timeline", "remember", "memory", "deja", "vu", "dream", "nightmare", "premonition", "fate"],
    ["butterfly", "consequence", "ripple", "shift", "delay", "reroute", "destiny", "omen", "curse"],
    ["family", "arthur", "elena", "maya", "leo", "wife", "son", "sister", "brother", "friend", "chloe"],
    ["trust", "ally", "help", "believe", "proof", "evidence", "truth", "kind", "rapport"],
    ["insane", "mad", "hysteria", "delirium", "raving", "lunatic", "suspicion", "panic", "fever"],
    ["bazaar", "ironmonger", "ledger", "chancery", "telegraph", "fountain", "commons", "manor"],
]


def compute_semantic_embedding(text: str) -> np.ndarray:
    """
    Computes a normalized 64-D dense semantic + lexical n-gram vector in NumPy.
    Dims [0..15] capture domain concept activations;
    Dims [16..63] capture character 3-gram & token feature projections.
    """
    vec = np.zeros(EMBED_DIM, dtype=np.float32)
    clean = re.sub(r"[^a-z0-9\s\-]", " ", text.lower())
    tokens = clean.split()

    if not tokens:
        vec[0] = 1.0
        return vec

    # 1. Domain concept cluster activations
    num_clusters = min(16, len(CONCEPT_CLUSTERS))
    for c_idx in range(num_clusters):
        keywords = CONCEPT_CLUSTERS[c_idx]
        hits = sum(1 for t in tokens if any(k in t for k in keywords))
        if hits > 0:
            vec[c_idx] = min(2.5, hits * 0.95)

    # 2. Hashed token + character trigram projections into dims [16..63]
    rem_dims = EMBED_DIM - num_clusters
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16)
        idx = num_clusters + (h % rem_dims)
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[idx] += sign * 0.65

        padded = f"<{tok}>"
        for i in range(len(padded) - 2):
            tg = padded[i : i + 3]
            th = int(hashlib.md5(tg.encode("utf-8")).hexdigest()[:8], 16)
            t_idx = num_clusters + (th % rem_dims)
            t_sign = 1.0 if ((th >> 4) & 1) == 0 else -1.0
            vec[t_idx] += t_sign * 0.25

    norm = float(np.linalg.norm(vec))
    if norm > 1e-6:
        vec /= norm
    else:
        vec[0] = 1.0
    return vec


class MemoryEngram:
    """Single vector memory entry inside an AI Agent's VectorMemoryStore."""

    def __init__(
        self,
        text: str,
        loop_id: int = 1,
        day_id: int = 1,
        importance: float = 0.6,
        persistent: bool = False,
        source: str = "baseline",
    ):
        self.text = text
        self.loop_id = loop_id
        self.day_id = day_id
        self.importance = importance
        self.persistent = persistent  # Survives loop resets if True (Chronos Anchor or Subconscious Echo)
        self.source = source  # "baseline", "observation", "dialogue", "subconscious_echo", "rewritten_anchor"
        self.timestamp = time.time()
        self.vector = compute_semantic_embedding(text)


class VectorMemoryStore:
    """
    Per-Agent Vector Memory Database supporting:
    - Cosine-similarity top-K retrieval
    - Cross-timeline Subconscious Echoes (so NPCs never repeat loops identically!)
    - Player-driven Aether-Resonance Premonition Anchors
    """

    def __init__(self, agent_id: str, baseline_memories: list[str]):
        self.agent_id = agent_id
        self.baseline_texts = list(baseline_memories)
        self.memories: list[MemoryEngram] = []
        self.reset_for_new_loop(loop_id=1, full_wipe=True)

    def reset_for_new_loop(self, loop_id: int, full_wipe: bool = False):
        """
        Called when the timeline rewinds to Monday after a catastrophe/death.
        Preserves `rewritten_anchor` and up to 3 `subconscious_echo` engrams so NPCs
        experience eerie deja-vu and shifting perspectives on every new loop!
        """
        if full_wipe:
            preserved = []
        else:
            anchors = [m for m in self.memories if m.persistent and m.source == "rewritten_anchor"]
            echoes = [m for m in self.memories if m.persistent and m.source == "subconscious_echo"][-3:]
            preserved = anchors + echoes

        self.memories = []
        for text in self.baseline_texts:
            self.memories.append(
                MemoryEngram(
                    text=text,
                    loop_id=loop_id,
                    day_id=1,
                    importance=0.65,
                    persistent=True,
                    source="baseline",
                )
            )
        self.memories.extend(preserved)

    def add_memory(
        self,
        text: str,
        loop_id: int = 1,
        day_id: int = 1,
        importance: float = 0.7,
        persistent: bool = False,
        source: str = "observation",
    ) -> MemoryEngram:
        for existing in self.memories:
            if existing.text.strip().lower() == text.strip().lower():
                existing.importance = max(existing.importance, importance)
                if persistent:
                    existing.persistent = True
                    existing.source = source
                return existing

        engram = MemoryEngram(
            text=text,
            loop_id=loop_id,
            day_id=day_id,
            importance=importance,
            persistent=persistent,
            source=source,
        )
        self.memories.append(engram)
        return engram

    def inject_subconscious_echo(self, dream_text: str, loop_id: int) -> MemoryEngram:
        """
        Injects a haunting subconscious dream/echo from a previous failed loop.
        The NPC does NOT consciously know they are in a loop, but they feel an uncanny
        unease or intuition that makes their dialogue fresh in the next loop!
        """
        tagged = f"[SUBCONSCIOUS DREAM // LOOP #{loop_id}]: {dream_text}"
        return self.add_memory(
            text=tagged,
            loop_id=loop_id,
            day_id=1,
            importance=1.1,
            persistent=True,
            source="subconscious_echo",
        )

    def inject_chronos_anchor(self, rewritten_belief: str, loop_id: int) -> MemoryEngram:
        """
        Awakens a vivid premonition inside the NPC's long-term vector memory that
        survives timeline resets.
        """
        tagged = f"[AETHER PREMONITION // LOOP #{loop_id}]: {rewritten_belief}"
        return self.add_memory(
            text=tagged,
            loop_id=loop_id,
            day_id=1,
            importance=1.5,
            persistent=True,
            source="rewritten_anchor",
        )

    def has_anchored_memory(self) -> bool:
        return any(m.source == "rewritten_anchor" for m in self.memories)

    def get_latest_echo(self) -> str | None:
        for m in reversed(self.memories):
            if m.source in ("rewritten_anchor", "subconscious_echo"):
                return m.text
        return None

    def retrieve_relevant(self, query_text: str, top_k: int = 4) -> list[tuple[MemoryEngram, float]]:
        if not self.memories:
            return []

        q_vec = compute_semantic_embedding(query_text)
        scored = []
        for mem in self.memories:
            cos_sim = float(np.dot(q_vec, mem.vector))
            boost = 0.45 if mem.source == "rewritten_anchor" else (0.25 if mem.source == "subconscious_echo" else 0.0)
            total_score = cos_sim * 0.65 + mem.importance * 0.35 + boost
            scored.append((mem, total_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
