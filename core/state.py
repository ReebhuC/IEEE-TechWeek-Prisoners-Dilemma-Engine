from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import defaultdict

@dataclass
class AgentState:
    agent_id: str
    is_bot: bool
    strategy_type: Optional[str] = None
    
    # Scoring tracking
    resource_score: int = 0
    elo_rating: float = 1200.0
    reputation_score: float = 0.0 
    
    # Action history (COOPERATE, DEFECT, IGNORE)
    action_history: List[str] = field(default_factory=list)
    
    # Drift and adaptability fields
    pre_drift_score: Optional[int] = None
    post_drift_score: Optional[int] = None

    def get_adaptability_score(self) -> float:
        """
        Adaptability is difference between post-drift and pre-drift performance.
        Valid primarily for agents heavily affected by the drift environment.
        """
        if self.pre_drift_score is not None and self.post_drift_score is not None:
            pre_drift_rate = self.pre_drift_score
            post_drift_rate = self.resource_score - self.post_drift_score
            return post_drift_rate - pre_drift_rate
        return 0.0

@dataclass
class TournamentState:
    current_round: int = 0
    max_rounds: int = 500
    
    # Dictionary mapping agent_id to their AgentState
    agents: Dict[str, AgentState] = field(default_factory=dict)
    
    # Pairwise interaction history
    # tuple(agent1_id, agent2_id) -> List of tuples(action_1, action_2)
    pairwise_history: Dict[tuple, List[tuple]] = field(default_factory=lambda: defaultdict(list))
    
    def get_pairwise_history(self, agent1: str, agent2: str) -> List[tuple]:
        """Returns history oriented from agent1's perspective: list of (agent1_action, agent2_action)"""
        if agent1 == agent2:
            return [] # Agents do not play against themselves
        
        key = tuple(sorted((agent1, agent2)))
        history = self.pairwise_history[key]
        if agent1 > agent2:
            return [(a2, a1) for a1, a2 in history]
        return history

    def add_interaction(self, agent1: str, action1: str, payoff1: int, 
                        agent2: str, action2: str, payoff2: int):
        """Records an interaction between two agents."""
        self.agents[agent1].action_history.append(action1)
        self.agents[agent2].action_history.append(action2)
        
        self.agents[agent1].resource_score += payoff1
        self.agents[agent2].resource_score += payoff2
        
        # Store in sorted order to ensure consistent lookup
        key = tuple(sorted((agent1, agent2)))
        if agent1 <= agent2:
            self.pairwise_history[key].append((action1, action2))
        else:
            self.pairwise_history[key].append((action2, action1))
