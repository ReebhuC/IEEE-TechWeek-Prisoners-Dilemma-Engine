import random
from typing import Dict, Callable

from .state import TournamentState, AgentState
from .features import compute_features
from .game import resolve_interaction, normalize_action
from .scoring import update_elo
from .events import apply_drift_event

class TournamentEngine:
    def __init__(self, max_rounds: int = 500, on_round_end=None, on_event=None):
        self.state = TournamentState(max_rounds=max_rounds)
        # Function dispatcher for agents: id -> decide(state)
        # Temporarily store direct callables here until Sandbox is implemented
        self.agent_runners: Dict[str, Callable] = {}
        self.on_round_end = on_round_end
        self.on_event = on_event
        
    def register_agent(self, agent_id: str, is_bot: bool, runner_func: Callable, strategy_type: str = None):
        """Registers an agent with the tournament engine."""
        self.state.agents[agent_id] = AgentState(
            agent_id=agent_id, 
            is_bot=is_bot,
            strategy_type=strategy_type
        )
        self.agent_runners[agent_id] = runner_func
        
    def _run_interaction(self, agent1_id: str, agent2_id: str):
        """Runs a single interaction between two agents."""
        f1 = compute_features(agent1_id, agent2_id, self.state)
        f2 = compute_features(agent2_id, agent1_id, self.state)
        
        try:
            a1_action = self.agent_runners[agent1_id](f1)
        except Exception:
            a1_action = "COOPERATE" # Fallback
            
        try:
            a2_action = self.agent_runners[agent2_id](f2)
        except Exception:
            a2_action = "COOPERATE" # Fallback
            
        a1_action = normalize_action(a1_action)
        a2_action = normalize_action(a2_action)
            
        p1, p2 = resolve_interaction(a1_action, a2_action)
        
        # Elo update
        a1_state = self.state.agents[agent1_id]
        a2_state = self.state.agents[agent2_id]
        new_elo1, new_elo2 = update_elo(a1_state.elo_rating, a2_state.elo_rating, p1, p2)
        a1_state.elo_rating = new_elo1
        a2_state.elo_rating = new_elo2
        
        self.state.add_interaction(agent1_id, a1_action, p1, agent2_id, a2_action, p2)
        
    def play_round(self):
        """Pairs agents randomly and runs one interaction for each pair."""
        agent_ids = list(self.state.agents.keys())
        random.shuffle(agent_ids)
        
        # Pair agents up
        for i in range(0, len(agent_ids) - 1, 2):
            self._run_interaction(agent_ids[i], agent_ids[i+1])
            
        # Handle odd agent out if necessary
        if len(agent_ids) % 2 != 0:
            # Handle odd agent out if necessary
            pass
            
        self.state.current_round += 1
        
        if self.on_round_end:
            self.on_round_end(self.state)

    def warmup_agents(self):
        """Executes a single dummy state payload to trace startup errors prematurely."""
        print(f"Warming up {len(self.agent_runners)} agents...")
        dummy_state = {
            "aggression_score": 0.5, "cooperation_trend": 0.5, "volatility": 0.5,
            "noisy_reputation": 0.5, "opponent_energy": 100, "round": -1,
            "tournament_phase": "warmup", "resource_percentile": 0.5
        }
        for agent_id, runner in self.agent_runners.items():
            print(f"  -> Warming up: {agent_id} ", end="", flush=True)
            try:
                action = runner(dummy_state)
                print(f"[OK] -> {action}")
            except Exception as e:
                print(f"[FAILED] -> {e}")

    def run_tournament(self):
        """Runs the whole tournament."""
        self.warmup_agents()
        print(f"Tournament loop starting for {self.state.max_rounds} rounds...")
        while self.state.current_round < self.state.max_rounds:
            if self.state.current_round > 0 and self.state.current_round % 10 == 0:
                print(f"  [Engine] Processing round {self.state.current_round} / {self.state.max_rounds} ...")
            if self.state.current_round == 250:
                affected = apply_drift_event(self.state)
                if self.on_event:
                    self.on_event(f"Drift Event! 30% of bots ({len(affected)}) have changed strategies and reset state.")
                
            self.play_round()
        print(f"  [Engine] Tournament simulation complete! Loop successfully exited.")
