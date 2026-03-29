import random
from typing import Dict, Any
from .state import TournamentState

def inject_noise(value: float, sigma: float = 0.12) -> float:
    """Injects Gaussian noise into a normalized value [0, 1]."""
    noisy = value + random.gauss(0, sigma)
    return max(0.0, min(1.0, noisy))

def compute_features(agent_id: str, opponent_id: str, state: TournamentState) -> Dict[str, Any]:
    """
    Compute noisy feature vector summarizing current state and opponent behaviour.
    This vector is passed to the agent's 'decide' method to avoid exposing raw history.
    """
    opponent = state.agents[opponent_id]
    history = opponent.action_history
    
    total_actions = len(history)
    
    # 1. aggression_score (fraction of defections)
    defects = sum(1 for a in history if a == "DEFECT")
    aggression_score = defects / total_actions if total_actions > 0 else 0.0
    
    # 2. cooperation_trend (recent cooperation rate - last 10 rounds)
    recent_history = history[-10:] if total_actions >= 10 else history
    recent_actions = len(recent_history)
    coops = sum(1 for a in recent_history if a == "COOPERATE")
    cooperation_trend = coops / recent_actions if recent_actions > 0 else 0.0
    
    # 3. volatility (frequency of behavior change)
    changes = 0
    for i in range(1, total_actions):
        if history[i] != history[i-1]:
            changes += 1
    volatility = changes / (total_actions - 1) if total_actions > 1 else 0.0
    
    # 4. noisy_reputation (delayed/averaged perception)
    noisy_reputation = opponent.reputation_score
    
    # 5. opponent_energy
    opponent_energy = opponent.resource_score
    
    # 6. resource_percentile (of the agent itself)
    all_scores = sorted([a.resource_score for a in state.agents.values()])
    agent = state.agents[agent_id]
    if len(all_scores) > 1:
        agent_rank = all_scores.index(agent.resource_score)
        resource_percentile = agent_rank / (len(all_scores) - 1)
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
        "opponent_energy": opponent_energy, # exact
        "round": state.current_round,    # exact
        "tournament_phase": phase,          # exact
        "resource_percentile": inject_noise(resource_percentile)
    }
