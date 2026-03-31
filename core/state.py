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

    # FIX 13: reputation_score is now maintained incrementally (cooperation rate)
    # Previously always 0.0; now updated on every interaction via add_interaction.
    reputation_score: float = 0.0
    _coop_count: int = field(default=0, repr=False)   # internal: running cooperate count
    _total_count: int = field(default=0, repr=False)   # internal: total actions taken

    # Action history (COOPERATE, DEFECT, IGNORE)
    action_history: List[str] = field(default_factory=list)

    # Drift and adaptability fields
    pre_drift_score: Optional[int] = None
    post_drift_score: Optional[int] = None

    def get_adaptability_score(self) -> float:
        """
        Adaptability is the difference between post-drift and pre-drift
        performance rate. Valid primarily for drifted bots.
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

    # Dictionary mapping agent_id -> AgentState
    agents: Dict[str, AgentState] = field(default_factory=dict)

    # Pairwise interaction history
    # tuple(agent1_id, agent2_id) -> List of tuples(action_1, action_2)
    pairwise_history: Dict[tuple, List[tuple]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def get_pairwise_history(self, agent1: str, agent2: str) -> List[tuple]:
        """Returns history oriented from agent1's perspective."""
        if agent1 == agent2:
            return []
        key = tuple(sorted((agent1, agent2)))
        history = self.pairwise_history[key]
        if agent1 > agent2:
            return [(a2, a1) for a1, a2 in history]
        return history

    def add_interaction(
        self,
        agent1: str, action1: str, payoff1: int,
        agent2: str, action2: str, payoff2: int,
    ):
        """Records an interaction between two agents."""
        a1 = self.agents[agent1]
        a2 = self.agents[agent2]

        a1.action_history.append(action1)
        a2.action_history.append(action2)

        a1.resource_score += payoff1
        a2.resource_score += payoff2

        # FIX 13: Maintain reputation_score as a running cooperation rate (O(1) update)
        a1._total_count += 1
        a2._total_count += 1
        if action1 == "COOPERATE":
            a1._coop_count += 1
        if action2 == "COOPERATE":
            a2._coop_count += 1
        a1.reputation_score = a1._coop_count / a1._total_count
        a2.reputation_score = a2._coop_count / a2._total_count

        # Store in sorted-key order for consistent lookup
        key = tuple(sorted((agent1, agent2)))
        if agent1 <= agent2:
            self.pairwise_history[key].append((action1, action2))
        else:
            self.pairwise_history[key].append((action2, action1))
