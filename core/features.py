import random
from typing import Dict, Any, List, Optional
from .state import TournamentState


def inject_noise(value: float, sigma: float = 0.12) -> float:
    """Injects Gaussian noise into a normalized value [0, 1]."""
    noisy = value + random.gauss(0, sigma)
    return max(0.0, min(1.0, noisy))


def compute_features(
    agent_id: str,
    opponent_id: str,
    state: TournamentState,
    cached_scores: Optional[List[int]] = None,   # FIX 8: pre-sorted scores from play_round
) -> Dict[str, Any]:
    """
    Computes a noisy feature vector summarising current state and opponent behaviour.
    This vector is passed to the agent's 'decide' method to avoid exposing raw history.

    FIX 8: accepts a pre-sorted cached_scores list to avoid O(N log N) sort on every
    single interaction call.  Engine passes this in; falls back to computing it here
    when called standalone (e.g. from tests).
    """
    opponent = state.agents[opponent_id]
    history = opponent.action_history
    total_actions = len(history)

    # 1. aggression_score (fraction of defections)
    defects = sum(1 for a in history if a == "DEFECT")
    aggression_score = defects / total_actions if total_actions > 0 else 0.0

    # 2. cooperation_trend (recent cooperation rate — last 10 rounds)
    recent_history = history[-10:] if total_actions >= 10 else history
    recent_actions = len(recent_history)
    coops = sum(1 for a in recent_history if a == "COOPERATE")
    cooperation_trend = coops / recent_actions if recent_actions > 0 else 0.0

    # 3. volatility (frequency of behaviour change)
    changes = 0
    for i in range(1, total_actions):
        if history[i] != history[i - 1]:
            changes += 1
    volatility = changes / (total_actions - 1) if total_actions > 1 else 0.0

    # 4. noisy_reputation — FIX 13: now a real cooperation rate, not always 0
    noisy_reputation = opponent.reputation_score

    # 5. opponent_energy
    opponent_energy = opponent.resource_score

    # 6. resource_percentile — FIX 8: use cached_scores if provided
    if cached_scores is None:
        cached_scores = sorted([a.resource_score for a in state.agents.values()])

    agent_score = state.agents[agent_id].resource_score
    if len(cached_scores) > 1:
        agent_rank = cached_scores.index(agent_score)
        resource_percentile = agent_rank / (len(cached_scores) - 1)
    else:
        resource_percentile = 0.5

    # 7. tournament_phase
    progress = state.current_round / state.max_rounds
    if progress < 0.33:
        phase = "early"
    elif progress < 0.66:
        phase = "mid"
    else:
        phase = "late"

    return {
        "aggression_score": inject_noise(aggression_score),
        "cooperation_trend": inject_noise(cooperation_trend),
        "volatility": inject_noise(volatility),
        "noisy_reputation": inject_noise(noisy_reputation),
        "opponent_energy": opponent_energy,       # exact
        "round": state.current_round,             # exact
        "tournament_phase": phase,                # exact
        "resource_percentile": inject_noise(resource_percentile),
    }
