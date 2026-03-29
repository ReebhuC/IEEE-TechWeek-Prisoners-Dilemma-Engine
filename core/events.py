import random
from typing import List

from .state import TournamentState
from bots.strategies import BUILT_IN_BOTS

def apply_drift_event(state: TournamentState, drift_percentage: float = 0.3) -> List[str]:
    """
    Randomly selects a percentage of bot agents and changes their strategy to a new one.
    Resets their internal behavioral state.
    Returns list of affected agent IDs.
    """
    # Only bots are eligible for drift
    eligible_bots = [agent_id for agent_id, agent in state.agents.items() if agent.is_bot]
    
    num_to_drift = max(1, int(len(eligible_bots) * drift_percentage))
    drift_targets = random.sample(eligible_bots, min(num_to_drift, len(eligible_bots)))
    
    available_strategies = list(BUILT_IN_BOTS.keys())
    
    for bot_id in drift_targets:
        agent_state = state.agents[bot_id]
        
        # Keep track of pre-drift score
        agent_state.pre_drift_score = agent_state.resource_score
        agent_state.post_drift_score = agent_state.resource_score # Starting baseline for post-drift
        
        # Change strategy
        old_strategy = agent_state.strategy_type
        possible_new = [s for s in available_strategies if s != old_strategy]
        if possible_new:
            new_strategy = random.choice(possible_new)
            agent_state.strategy_type = new_strategy
            
        # Clear action history
        agent_state.action_history = []
        
    return drift_targets
