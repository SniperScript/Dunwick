"""
butterfly_nn.py
Butterfly Neural Influence Engine for CHRONICLES OF DUNWICK: DEFYING FATE (1924)
Adapted from 'The-Butterfly-' (Hebbian learning & neural influence network by DantrazTrev).

In Dunwick, the timeline is not a static tree; it is an organic, perturbable neural web:
1. Each citizen possesses an internal neural state:
   - Trust (in the player)
   - Suspicion (alarm / delirium perception)
   - Fatalism (receptivity to impending doom)
   - Composure (calmness vs panic)
   - Nervous Tell Intensity
2. Across time loops and butterfly interventions, Hebbian weight reinforcement
   (w = w + eta * nabla_w - forget * w) updates their subconscious neural weights.
3. While townsfolk do not retain explicit episodic memories of prior loops (Sole-Knower isolation),
   their neural weights carry subconscious ripples (déjà vu, inexplicable dread, shifting habits).
"""

import math
import random
import numpy as np


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -15.0, 15.0)))


def _inv_sigmoid(z):
    z = np.clip(z, 1e-5, 1.0 - 1e-5)
    return np.log(z / (1.0 - z))


class ButterflyNetwork:
    """
    Lightweight feedforward network with Hebbian learning and forgetting factor,
    directly based on NN.py from The-Butterfly-.
    """

    def __init__(self, layer_sizes: list[int]):
        self.sizes = layer_sizes
        self.num_layers = len(layer_sizes)
        # Xavier/He initialization for stable dynamics
        self.weights = [
            np.random.randn(y, x) * np.sqrt(2.0 / (x + y))
            for x, y in zip(layer_sizes[:-1], layer_sizes[1:])
        ]
        self.biases = [np.zeros((y, 1)) for y in layer_sizes[1:]]

    def feedforward(self, a: np.ndarray) -> np.ndarray:
        for b, w in zip(self.biases, self.weights):
            a = _sigmoid(np.dot(w, a) + b)
        return a

    def hebbian_update(self, a_in: np.ndarray, eta: float = 0.08, forget: float = 0.02):
        """
        Hebbian learning rule adapted from The-Butterfly-:
        Activities that co-activate strengthen synaptic connection; forgetting factor prevents saturation.
        """
        activations = [a_in]
        curr = a_in
        for b, w in zip(self.biases, self.weights):
            curr = _sigmoid(np.dot(w, curr) + b)
            activations.append(curr)

        # Delta weights: outer product of layer activations
        new_weights = []
        new_biases = []
        for i in range(len(self.weights)):
            w = self.weights[i]
            b = self.biases[i]
            act_in = activations[i]
            act_out = activations[i + 1]

            # Correlation dw = act_out * act_in^T
            dw = np.dot(act_out, act_in.T)
            # Apply Hebbian shift with decay
            w_updated = (1.0 - forget) * w + eta * dw
            b_updated = b + (eta * 0.5) * (act_out - 0.5)
            new_weights.append(w_updated)
            new_biases.append(b_updated)

        self.weights = new_weights
        self.biases = new_biases
        return activations[-1]


class NPCButterflyMind:
    """
    Represents an NPC's internal neural psyche in 1924 Dunwick.
    Inputs (5 dimensions):
    [0]: Player Composure & Presence
    [1]: Shared Earl Grey / Gift Rapport
    [2]: Environmental Tension (Current Day Crisis Level)
    [3]: Subconscious Déjà Vu from Prior Loop Catastrophe
    [4]: Direct Confrontation / Accusation intensity

    Outputs (4 dimensions):
    [0]: Trust Level (0.0 to 1.0)
    [1]: Suspicion of Delirium (0.0 to 1.0)
    [2]: Receptivity to Hazard Warning (0.0 to 1.0)
    [3]: Behavioral Tell Frequency (0.0 to 1.0)
    """

    def __init__(self, char_id: str, baseline_trust: float = 0.5, baseline_suspicion: float = 0.2):
        self.char_id = char_id
        # Architecture: 5 inputs -> 6 hidden neurons -> 4 outputs
        self.net = ButterflyNetwork([5, 6, 4])
        self.baseline_trust = baseline_trust
        self.baseline_suspicion = baseline_suspicion

        # Current personality state
        self.trust = baseline_trust
        self.suspicion = baseline_suspicion
        self.receptivity = 0.4
        self.tell_frequency = 0.5

        # Subconscious memory weight
        self.deja_vu_weight = 0.0
        self.interaction_count = 0

    def get_state_vector(self) -> dict:
        return {
            "trust": round(float(self.trust), 3),
            "suspicion": round(float(self.suspicion), 3),
            "receptivity": round(float(self.receptivity), 3),
            "tell_frequency": round(float(self.tell_frequency), 3),
            "deja_vu": round(float(self.deja_vu_weight), 3),
        }

    def process_stimulus(
        self,
        player_composure: float,
        rapport_stimulus: float,
        env_tension: float,
        confrontation: float,
        learning_rate: float = 0.06,
    ) -> dict:
        """
        Feeds inputs through the neural network and updates Hebbian synapses.
        """
        x = np.array([
            [np.clip(player_composure, 0.0, 1.0)],
            [np.clip(rapport_stimulus, 0.0, 1.0)],
            [np.clip(env_tension, 0.0, 1.0)],
            [np.clip(self.deja_vu_weight, 0.0, 1.0)],
            [np.clip(confrontation, 0.0, 1.0)],
        ])

        out = self.net.hebbian_update(x, eta=learning_rate, forget=0.015)

        # Blend neural outputs with baselines for graceful progression
        self.trust = float(np.clip(0.3 * self.baseline_trust + 0.7 * out[0, 0], 0.05, 0.98))
        self.suspicion = float(np.clip(0.3 * self.baseline_suspicion + 0.7 * out[1, 0], 0.02, 0.95))
        self.receptivity = float(np.clip(out[2, 0], 0.1, 0.95))
        self.tell_frequency = float(np.clip(out[3, 0], 0.1, 0.95))

        self.interaction_count += 1
        return self.get_state_vector()

    def impart_loop_deja_vu(self, fatal_event: str, intensity: float = 0.35):
        """
        When the player dies and the loop resets to Monday, townsfolk receive an
        intangible subconscious ripple of the tragedy.
        """
        self.deja_vu_weight = float(np.clip(self.deja_vu_weight + intensity, 0.0, 1.0))
        # Stimulate the network so the NPC wakes up Monday with an altered psychological posture
        x = np.array([
            [0.5],
            [0.3],
            [0.7],
            [self.deja_vu_weight],
            [0.1],
        ])
        self.net.hebbian_update(x, eta=0.09, forget=0.04)


class DunwickButterflyEcosystem:
    """
    Manages the collective neural influence web of all 24 Dunwick citizens.
    Interactions with one citizen ripple out to their associates (e.g. Sal -> Mia, Arthur -> Elena, Clarke -> Chloe).
    """

    ASSOCIATE_GRAPH = {
        "sal": ["mia", "zack", "martha"],
        "mia": ["sal", "chloe", "sam"],
        "arthur": ["elena", "maya", "leo", "vance", "sam"],
        "elena": ["arthur", "sal", "mayor", "martha"],
        "maya": ["chloe", "clarke", "leo", "lin"],
        "leo": ["toby", "dan", "maya", "rosa"],
        "rosa": ["sam", "hank", "zack"],
        "miller": ["jenkins", "mayor", "arthur"],
        "clarke": ["maya", "higgins", "pam"],
        "joya": ["martha", "lin", "miller"],
    }

    def __init__(self, character_specs: list[dict]):
        self.minds: dict[str, NPCButterflyMind] = {}
        for spec in character_specs:
            cid = spec["id"]
            base_trust = 0.65 if spec.get("is_family") else 0.45
            base_susp = 0.10 if spec.get("is_family") else 0.25
            self.minds[cid] = NPCButterflyMind(cid, base_trust, base_susp)

        self.total_loop_deaths: list[dict] = []

    def get_mind(self, char_id: str) -> NPCButterflyMind:
        if char_id not in self.minds:
            self.minds[char_id] = NPCButterflyMind(char_id)
        return self.minds[char_id]

    def record_interaction(
        self,
        char_id: str,
        player_composure: float,
        rapport_stimulus: float,
        env_tension: float,
        confrontation: float,
    ):
        """
        Updates the target NPC's mind and propagates secondary ripples to their associates.
        """
        mind = self.get_mind(char_id)
        state = mind.process_stimulus(player_composure, rapport_stimulus, env_tension, confrontation)

        # Propagate secondary ripple to immediate associates (Butterfly Effect!)
        associates = self.ASSOCIATE_GRAPH.get(char_id, [])
        for assoc_id in associates:
            if assoc_id in self.minds:
                # Associates receive a softened secondary shockwave
                self.minds[assoc_id].process_stimulus(
                    player_composure=player_composure * 0.9,
                    rapport_stimulus=rapport_stimulus * 0.4,
                    env_tension=env_tension * 0.7,
                    confrontation=confrontation * 0.5,
                    learning_rate=0.03,
                )
        return state

    def handle_temporal_reset(self, fatal_event_type: str, fatal_day: int, loop_count: int):
        """
        Called when the player perishes and time snaps back to Monday.
        Subconscious déjà vu ripples cascade across all 24 citizens.
        """
        self.total_loop_deaths.append({
            "loop": loop_count,
            "event": fatal_event_type,
            "day": fatal_day,
        })

        for cid, mind in self.minds.items():
            # Citizens close to the fatal scene receive stronger subconscious tremors
            intensity = 0.35 if cid in ("sal", "mia", "elena", "arthur", "maya", "leo") else 0.20
            mind.impart_loop_deja_vu(fatal_event_type, intensity=intensity)

