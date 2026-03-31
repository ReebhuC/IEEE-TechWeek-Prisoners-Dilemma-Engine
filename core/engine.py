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
        # Function dispatcher for agents: id -> callable(state_dict) -> str
        self.agent_runners: Dict[str, Callable] = {}
        self.on_round_end = on_round_end
        self.on_event = on_event

    def register_agent(
        self,
        agent_id: str,
        is_bot: bool,
        runner_func: Callable,
        strategy_type: str = None,
    ):
        """Registers an agent with the tournament engine."""
        self.state.agents[agent_id] = AgentState(
            agent_id=agent_id,
            is_bot=is_bot,
            strategy_type=strategy_type,
        )
        self.agent_runners[agent_id] = runner_func

    def _run_interaction(
        self,
        agent1_id: str,
        agent2_id: str,
        cached_scores: list = None,   # FIX 8: sorted scores computed once per round
    ):
        """Runs a single interaction between two agents."""
        # FIX 8: pass cached_scores through to avoid repeated sort in compute_features
        f1 = compute_features(agent1_id, agent2_id, self.state, cached_scores)
        f2 = compute_features(agent2_id, agent1_id, self.state, cached_scores)

        try:
            a1_action = self.agent_runners[agent1_id](f1)
        except Exception:
            a1_action = "COOPERATE"

        try:
            a2_action = self.agent_runners[agent2_id](f2)
        except Exception:
            a2_action = "COOPERATE"

        a1_action = normalize_action(a1_action)
        a2_action = normalize_action(a2_action)

        p1, p2 = resolve_interaction(a1_action, a2_action)

        a1_state = self.state.agents[agent1_id]
        a2_state = self.state.agents[agent2_id]
        new_elo1, new_elo2 = update_elo(a1_state.elo_rating, a2_state.elo_rating, p1, p2)
        a1_state.elo_rating = new_elo1
        a2_state.elo_rating = new_elo2

        self.state.add_interaction(agent1_id, a1_action, p1, agent2_id, a2_action, p2)

    def _run_phantom_interaction(self, agent_id: str, cached_scores: list = None):
        """
        Plays the odd-agent-out against a phantom opponent instead of giving a bye.

        The phantom's action is sampled from the current field cooperation rate:
        - If 70% of all real agents cooperated last round, phantom cooperates 70%.
        - Phantom receives no payoff, has no elo, and never appears on the leaderboard.
        - This gives the odd agent a statistically representative interaction every round
          rather than sitting out and accumulating ~half the score of other agents.
        """
        all_agents = list(self.state.agents.values())

        # Compute field-wide cooperation rate from total action histories
        total_actions = sum(len(a.action_history) for a in all_agents)
        total_coops = sum(a.action_history.count("COOPERATE") for a in all_agents)
        coop_rate = total_coops / total_actions if total_actions > 0 else 0.5

        # Phantom plays according to the field average
        phantom_action = "COOPERATE" if random.random() < coop_rate else "DEFECT"

        # Build phantom-facing feature vector directly (no real opponent state)
        # Use field-wide averages as the opponent approximation
        avg_score = int(sum(a.resource_score for a in all_agents) / max(len(all_agents), 1))
        all_scores = cached_scores or sorted(a.resource_score for a in all_agents)
        a_state_pre = self.state.agents[agent_id]
        agent_rank = all_scores.index(a_state_pre.resource_score) if all_scores else 0
        resource_percentile = agent_rank / max(len(all_scores) - 1, 1)

        progress = self.state.current_round / self.state.max_rounds
        phase = "early" if progress < 0.33 else "mid" if progress < 0.66 else "late"

        features = {
            "aggression_score": round(1.0 - coop_rate, 3),
            "cooperation_trend": round(coop_rate, 3),
            "volatility": 0.3,  # neutral assumption for phantom
            "noisy_reputation": round(coop_rate, 3),
            "opponent_energy": avg_score,
            "round": self.state.current_round,
            "tournament_phase": phase,
            "resource_percentile": round(resource_percentile, 3),
        }

        try:
            agent_action = self.agent_runners[agent_id](features)
        except Exception:
            agent_action = "COOPERATE"

        agent_action = normalize_action(agent_action)
        phantom_action = normalize_action(phantom_action)

        # Compute payoff for the real agent only (phantom gets nothing)
        agent_payoff, _ = resolve_interaction(agent_action, phantom_action)

        # Update real agent's score, history, and elo vs phantom baseline (1200)
        a_state = self.state.agents[agent_id]
        a_state.action_history.append(agent_action)
        a_state.resource_score += agent_payoff

        # Incremental reputation update
        a_state._total_count += 1
        if agent_action == "COOPERATE":
            a_state._coop_count += 1
        a_state.reputation_score = a_state._coop_count / a_state._total_count

        # Elo: treat phantom as an average 1200-rated opponent
        new_elo, _phantom_elo = update_elo(a_state.elo_rating, 1200.0, agent_payoff, 0)
        a_state.elo_rating = new_elo

    def play_round(self):

        """Pairs agents randomly and runs one interaction for each pair."""
        agent_ids = list(self.state.agents.keys())
        random.shuffle(agent_ids)

        # FIX 8: Sort scores once per round, not once per interaction
        cached_scores = sorted(
            [a.resource_score for a in self.state.agents.values()]
        )

        for i in range(0, len(agent_ids) - 1, 2):
            self._run_interaction(agent_ids[i], agent_ids[i + 1], cached_scores)

        # Phantom opponent for the odd agent out (FIX 11 upgrade)
        # Rather than a pure bye (no action, no score impact) or always-COOPERATE,
        # the phantom mirrors the field's current average cooperation rate.
        # This gives the odd agent a statistically neutral, representative interaction.
        if len(agent_ids) % 2 != 0:
            bye_agent_id = agent_ids[-1]  # Last agent after shuffle
            self._run_phantom_interaction(bye_agent_id, cached_scores)


        self.state.current_round += 1

        if self.on_round_end:
            self.on_round_end(self.state)

    def warmup_agents(self) -> Dict[str, str]:
        """Executes a single dummy invocation per agent and returns failures."""
        print(f"Warming up {len(self.agent_runners)} agents...")
        dummy_state = {
            "aggression_score": 0.5, "cooperation_trend": 0.5, "volatility": 0.5,
            "noisy_reputation": 0.5, "opponent_energy": 100, "round": -1,
            "tournament_phase": "warmup", "resource_percentile": 0.5,
        }
        failures: Dict[str, str] = {}
        for agent_id, runner in self.agent_runners.items():
            print(f"  -> Warming up: {agent_id} ", end="", flush=True)
            try:
                action = runner(dummy_state)
                print(f"[OK] -> {action}")
            except Exception as e:
                reason = str(e).strip() or e.__class__.__name__
                failures[agent_id] = reason
                print(f"[FAILED] -> {reason}")
        return failures

    def run_tournament(self, skip_warmup: bool = False):
        """
        Runs the whole tournament.

        FIX 14: skip_warmup=True skips the warmup phase (used in multi-run mode
        for runs > 1 to avoid O(agents × subprocess_spawn) overhead per run).
        """
        if not skip_warmup:
            self.warmup_agents()

        print(f"Tournament loop starting for {self.state.max_rounds} rounds...")
        while self.state.current_round < self.state.max_rounds:
            if self.state.current_round > 0 and self.state.current_round % 10 == 0:
                print(
                    f"  [Engine] Processing round "
                    f"{self.state.current_round} / {self.state.max_rounds} ..."
                )

            midpoint = self.state.max_rounds // 2
            if self.state.current_round == midpoint:
                # FIX 7: pass agent_runners so drift actually swaps the callables
                affected = apply_drift_event(self.state, self.agent_runners)
                if self.on_event:
                    self.on_event(
                        f"Drift Event! 30% of bots ({len(affected)}) have "
                        f"changed strategies and reset state."
                    )

            self.play_round()

        print("  [Engine] Tournament simulation complete! Loop successfully exited.")
