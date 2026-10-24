"""
Long-Term Vector Memory Store & Cross-Timeline Memory Rewriting Engine.
Uses NumPy semantic/hashed feature embeddings with cosine-similarity retrieval,
allowing the player to inspect, query, and rewrite AI agent vector memories across loops.
"""

import re
import time
import hashlib
import numpy as np


EMBED_DIM = 64

# Domain-specific semantic concept clusters for high-signal embedding dims [0..23]
CONCEPT_CLUSTERS = [
    ["aether", "core", "reactor", "overload", "explode", "detonate", "critical", "foundry"],
    ["manifold", "coolant", "cooling", "cryo", "rod", "valve", "404", "flush", "temperature"],
    ["vesper", "saboteur", "sabotage", "poison", "vial", "corrosive", "ledger", "conspiracy", "spy"],
    ["vaelen", "archon", "ruler", "purge", "terminal", "omega", "77", "signet", "sovereign", "throne"],
    ["kael", "commander", "guard", "garrison", "arrest", "stockade", "prison", "lockdown", "martial"],
    ["lyra", "spire", "astrologer", "engineer", "synthesizer", "chronos", "shard", "echo"],
    ["malakor", "bell", "plaza", "panic", "hysteria", "preach", "herald", "doomsday"],
    ["door", "gate", "barricade", "lock", "unlock", "weld", "seal", "blast"],
    ["loop", "timeline", "remember", "memory", "deja", "vu", "future", "died", "catastrophe", "reset"],
    ["trust", "ally", "help", "believe", "proof", "evidence", "truth", "friend"],
    ["insane", "crazy", "glitch", "liar", "arrest", "suspicion", "erratic", "threat"],
    ["bake", "bread", "routine", "courier", "mundane", "normal", "work", "citizen"],
]


def compute_semantic_embedding(text: str) -> np.ndarray:
    """
    Computes a normalized 64-D dense semantic + lexical n-gram vector in NumPy.
    Dims [0..11] capture domain concept activations;
    Dims [12..63] capture character 3-gram & token feature projections.
    """
    vec = np.zeros(EMBED_DIM, dtype=np.float32)
    clean = re.sub(r"[^a-z0-9\s\-]", " ", text.lower())
    tokens = clean.split()

    if not tokens:
        vec[0] = 1.0
        return vec

    # 1. Domain concept cluster activations (weighted high for accurate semantic recall)
    for c_idx, keywords in enumerate(CONCEPT_CLUSTERS):
        if c_idx >= 12:
            break
        hits = sum(1 for t in tokens if any(k in t for k in keywords))
        if hits > 0:
            vec[c_idx] = min(2.5, hits * 0.95)

    # 2. Hashed token + character trigram projections into dims [12..63]
    rem_dims = EMBED_DIM - 12
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16)
        idx = 12 + (h % rem_dims)
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[idx] += sign * 0.65

        # Trigrams for morphological robustness
        padded = f"<{tok}>"
        for i in range(len(padded) - 2):
            tg = padded[i : i + 3]
            th = int(hashlib.md5(tg.encode("utf-8")).hexdigest()[:8], 16)
            t_idx = 12 + (th % rem_dims)
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
        importance: float = 0.6,
        persistent: bool = False,
        source: str = "baseline",
    ):
        self.text = text
        self.loop_id = loop_id
        self.importance = importance
        self.persistent = persistent  # If True, survives timeline resets (Mode 2 core mechanic!)
        self.source = source  # "baseline", "observation", "dialogue", "rewritten_anchor"
        self.timestamp = time.time()
        self.vector = compute_semantic_embedding(text)


class VectorMemoryStore:
    """
    Per-Agent Vector Memory Database supporting:
    - Cosine-similarity top-K retrieval
    - Cross-timeline memory wiping (for non-anchored memories)
    - Player-driven Vector Memory Rewriting (Chronos Anchors)
    """

    def __init__(self, agent_id: str, baseline_memories: list[str]):
        self.agent_id = agent_id
        self.baseline_texts = list(baseline_memories)
        self.memories: list[MemoryEngram] = []
        self.reset_for_new_loop(loop_id=1, full_wipe=True)

    def reset_for_new_loop(self, loop_id: int, full_wipe: bool = False):
        """
        Called when the simulation timeline resets.
        Preserves any memory with `persistent=True` (rewritten by the player!)
        while wiping ordinary ephemeral memories from the failed loop.
        """
        if full_wipe:
            preserved = []
        else:
            preserved = [m for m in self.memories if m.persistent and m.source == "rewritten_anchor"]

        self.memories = []
        for text in self.baseline_texts:
            self.memories.append(
                MemoryEngram(
                    text=text,
                    loop_id=loop_id,
                    importance=0.65,
                    persistent=True,
                    source="baseline",
                )
            )
        # Re-attach player-anchored cross-timeline memories at the top of salience!
        self.memories.extend(preserved)

    def add_memory(
        self,
        text: str,
        loop_id: int = 1,
        importance: float = 0.7,
        persistent: bool = False,
        source: str = "observation",
    ) -> MemoryEngram:
        # Deduplicate near-identical memory strings
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
            importance=importance,
            persistent=persistent,
            source=source,
        )
        self.memories.append(engram)
        return engram

    def inject_chronos_anchor(self, rewritten_belief: str, loop_id: int) -> MemoryEngram:
        """
        Rewrites the agent's long-term vector memory with a high-importance persistent engram
        that survives all future timeline resets.
        """
        tagged = f"[CHRONOS ANCHOR // LOOP #{loop_id}]: {rewritten_belief}"
        return self.add_memory(
            text=tagged,
            loop_id=loop_id,
            importance=1.5,
            persistent=True,
            source="rewritten_anchor",
        )

    def has_anchored_memory(self) -> bool:
        return any(m.source == "rewritten_anchor" for m in self.memories)

    def retrieve_relevant(self, query_text: str, top_k: int = 4) -> list[tuple[MemoryEngram, float]]:
        """
        Retrieves the top_k most relevant memories using cosine similarity + importance + anchor boost.
        Returns list of (MemoryEngram, score).
        """
        if not self.memories:
            return []

        q_vec = compute_semantic_embedding(query_text)
        scored = []
        for mem in self.memories:
            cos_sim = float(np.dot(q_vec, mem.vector))
            anchor_boost = 0.45 if mem.source == "rewritten_anchor" else 0.0
            total_score = cos_sim * 0.65 + mem.importance * 0.35 + anchor_boost
            scored.append((mem, total_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
