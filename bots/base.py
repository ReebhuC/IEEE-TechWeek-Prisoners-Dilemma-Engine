from typing import Dict, Any

class Agent:
    """
    Base class for all agents in the tournament.
    Participant agents will be modeled as functions or classes
    that match this basic interface.
    """
    def decide(self, state: Dict[str, Any]) -> str:
        """
        Takes a feature state dictionary and returns an action:
        'COOPERATE', 'DEFECT', or 'IGNORE'.
        
        Args:
            state (dict):
                - aggression_score (float)
                - cooperation_trend (float)
                - volatility (float)
                - noisy_reputation (float)
                - opponent_energy (int)
                - round_number (int)
                - tournament_phase (str: 'early', 'mid', 'late')
                - resource_percentile (float)
        """
        raise NotImplementedError("Agents must implement the decide method.")
