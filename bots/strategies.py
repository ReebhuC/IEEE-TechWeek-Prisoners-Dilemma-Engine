import random
from typing import Dict, Any
from .base import Agent
from core.game import Action

class Aggressor(Agent):
    """Always defects."""
    def decide(self, state: Dict[str, Any]) -> str:
        return Action.DEFECT.value

class Cooperator(Agent):
    """Always cooperates."""
    def decide(self, state: Dict[str, Any]) -> str:
        return Action.COOPERATE.value

class RandomBot(Agent):
    """Returns a completely random legal action."""
    def decide(self, state: Dict[str, Any]) -> str:
        return random.choice([Action.COOPERATE.value, Action.DEFECT.value, Action.IGNORE.value])

class TitForTatBot(Agent):
    """
    Approximate Tit-for-Tat using the noisy feature vector.
    If the opponent's aggression or noisy_reputation is high, defect.
    Otherwise, cooperate.
    """
    def decide(self, state: Dict[str, Any]) -> str:
        # Check if opponent is generally aggressive
        aggression = state.get("aggression_score", 0.0)
        reputation = state.get("noisy_reputation", 0.0)
        
        # Tit-for-Tat: defect if opponent is defecting often recently
        if aggression > 0.4 or reputation > 0.6:
            return Action.DEFECT.value
        return Action.COOPERATE.value

class OpportunistBot(Agent):
    """
    Exploits cooperators (defects against low aggression), 
    cooperates/ignores highly aggressive opponents to minimize loss.
    """
    def decide(self, state: Dict[str, Any]) -> str:
        aggression = state.get("aggression_score", 0.0)
        
        if aggression < 0.2:
            return Action.DEFECT.value # Opponent is a pushover, exploit them
        elif aggression > 0.7:
            return Action.IGNORE.value # Opponent is too aggressive, minimize interaction
        else:
            return Action.COOPERATE.value # Play nice generally

# Map of built-in strategies
BUILT_IN_BOTS = {
    "Aggressor": Aggressor,
    "Cooperator": Cooperator,
    "Random": RandomBot,
    "TitForTat": TitForTatBot,
    "Opportunist": OpportunistBot
}
