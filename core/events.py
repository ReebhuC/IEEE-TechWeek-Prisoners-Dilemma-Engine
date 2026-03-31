import random
from typing import List, Dict, Callable

from .state import TournamentState
from bots.strategies import BUILT_IN_BOTS


def apply_drift_event(
    state: TournamentState,
    agent_runners: Dict[str, Callable],   # FIX 7: receive runner map to swap functions
    drift_percentage: float = 0.3,
) -> List[str]:
    """
    Randomly selects a percentage of bot agents, changes their strategy to a new one,
    and — FIX 7 — actually swaps the callable in agent_runners so the behaviour
    changes (previously only the label changed, not the decision function).

    Returns list of affected agent IDs.
    """
    # Only bots are eligible for drift
    eligible_bots = [
        agent_id for agent_id, agent in state.agents.items() if agent.is_bot
    ]

    num_to_drift = max(1, int(len(eligible_bots) * drift_percentage))
    drift_targets = random.sample(eligible_bots, min(num_to_drift, len(eligible_bots)))

    available_strategies = list(BUILT_IN_BOTS.keys())

    for bot_id in drift_targets:
        agent_state = state.agents[bot_id]

        # Track pre-drift score for adaptability measurement
        agent_state.pre_drift_score = agent_state.resource_score
        agent_state.post_drift_score = agent_state.resource_score  # baseline

        # Pick a genuinely different strategy
        old_strategy = agent_state.strategy_type
        possible_new = [s for s in available_strategies if s != old_strategy]
        if possible_new:
            new_strategy = random.choice(possible_new)
            agent_state.strategy_type = new_strategy

            # FIX 7: Swap the actual decision callable — not just the label
            agent_runners[bot_id] = BUILT_IN_BOTS[new_strategy]().decide

        # Reset action history so the bot starts fresh post-drift
        agent_state.action_history = []
        # Reset reputation counters to match cleared history
        agent_state._coop_count = 0
        agent_state._total_count = 0
        agent_state.reputation_score = 0.0

    return drift_targets
