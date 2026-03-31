import time
import os
import random
import argparse
from core.engine import TournamentEngine
from bots.strategies import BUILT_IN_BOTS
from sandbox.loader import load_agent_filepaths
from sandbox.runner import run_agent_in_sandbox
from server.app import start_server_thread, emit_leaderboard, emit_event
from utils.logger import TournamentLogger

# FIX 4: Push leaderboard every N rounds, not only at 100%
_LEADERBOARD_UPDATE_INTERVAL = 10


def main():
    parser = argparse.ArgumentParser(description="Prisoner's Dilemma Tournament Engine")
    parser.add_argument("--rounds", type=int, default=500, help="Number of rounds")
    parser.add_argument("--agents-dir", type=str, default="submissions",
                        help="Directory for custom agents")
    parser.add_argument("--runs", type=int, default=1,
                        help="Number of multi-runs for averaging")
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="Per-call agent timeout in seconds (default 5.0). "
                             "Increase if teams load large torch models from disk.")
    parser.add_argument("--grace-period", type=int, default=50,
                        help="Rounds before timeout strikes start counting (default 50). "
                             "Early-round variance shouldn't perma-ban agents.")
    args = parser.parse_args()

    # SECTION 6: FAIRNESS — deterministic engine shuffle seed
    random.seed(42)

    logger = TournamentLogger()

    def handle_round_end(state):
        # FIX 4: Emit leaderboard every N rounds AND at the very end
        is_final = (state.current_round == state.max_rounds)
        is_interval = (state.current_round % _LEADERBOARD_UPDATE_INTERVAL == 0)
        if is_final or is_interval:
            agents = sorted(
                state.agents.values(), key=lambda a: a.resource_score, reverse=True
            )
            leaderboard_data = [
                {
                    "agent_id": a.agent_id,
                    "strategy_type": a.strategy_type,
                    "score": a.resource_score,
                    "elo": a.elo_rating,
                }
                for a in agents
            ]
            if is_final:
                print("  [Frontend] Webpage Dashboard Updated (FINAL SCORES)!")
            emit_leaderboard(leaderboard_data)
            if is_final:
                time.sleep(0.05)  # Yield OS scheduling so Werkzeug drains the socket

    def handle_event(msg):
        emit_event(msg)
        logger.log_event("UPDATE", {"message": msg})
        print(f"[EVENT] {msg}")

    if not os.path.exists(args.agents_dir):
        os.makedirs(args.agents_dir)

    print("Starting Flask web server on port 5000...")
    start_server_thread(port=5000)
    time.sleep(1)

    aggregate_scores = {}
    aggregate_elo = {}

    for run in range(1, args.runs + 1):
        print(f"\n--- TOURNAMENT RUN {run}/{args.runs} ---")

        # FIX 14: Only warmup on the first run — saves O(agents × subprocess) per run
        is_first_run = (run == 1)

        engine = TournamentEngine(
            max_rounds=args.rounds,
            on_round_end=handle_round_end,
            on_event=handle_event,
        )

        for name, bot_class in BUILT_IN_BOTS.items():
            engine.register_agent(
                agent_id=f"Bot_{name}",
                is_bot=True,
                runner_func=bot_class().decide,
                strategy_type=name,
            )

        custom_agents = load_agent_filepaths(args.agents_dir)
        for team_id, team_dir in custom_agents.items():
            def make_sandbox_runner(t_dir=team_dir, a_id=team_id):
                tracker = {"strikes": 0}

                def runner(state):
                    current_round = state.get("round", 0)
                    # Warmup calls use round == -1, never count as strikes
                    is_warmup = (current_round == -1)
                    # Grace period: early-round variance is high, don't penalize
                    in_grace = (current_round < args.grace_period)

                    if tracker["strikes"] >= 5:
                        return "COOPERATE"
                    try:
                        return run_agent_in_sandbox(
                            t_dir,
                            a_id,
                            state,
                            timeout=args.timeout,
                            raise_on_error=is_warmup,
                        )
                    except TimeoutError:
                        if not is_warmup and not in_grace:
                            # Only accumulate strikes after the grace period
                            tracker["strikes"] += 1
                            if tracker["strikes"] == 5:
                                print(
                                    f"  [Engine] {a_id} HIT 5 TIMEOUT STRIKES! "
                                    f"Perma-banned to COOPERATE for rest of tournament."
                                )
                        elif in_grace and not is_warmup:
                            print(
                                f"  [Engine] {a_id} timed out in grace period "
                                f"(round {current_round}) — no strike counted."
                            )
                        raise  # Let engine/warmup catch it and print [FAILED]

                return runner

            engine.register_agent(
                agent_id=team_id,
                is_bot=False,
                runner_func=make_sandbox_runner(),
                strategy_type="Participant",
            )

        if is_first_run:
            warmup_failures = engine.warmup_agents()
            excluded = {}
            for agent_id, reason in warmup_failures.items():
                agent_state = engine.state.agents.get(agent_id)
                if agent_state and not agent_state.is_bot:
                    excluded[agent_id] = reason

            if excluded:
                print("  [Engine] Warmup failures (excluded from tournament):")
                emit_event("Warmup failures detected. Excluding broken participant agents.")
                for agent_id, reason in excluded.items():
                    engine.agent_runners.pop(agent_id, None)
                    engine.state.agents.pop(agent_id, None)
                    msg = f"Excluded {agent_id}: {reason}"
                    print(f"    - {msg}")
                    emit_event(msg)
            else:
                emit_event("Warmup completed with no participant exclusions.")

        # Forcibly clear any stale leaderboard data from un-refreshed browser tabs
        emit_leaderboard([])

        emit_event(f"Tournament Run {run} Started!")
        # Warmup already handled in main on first run; skip inside engine.
        engine.run_tournament(skip_warmup=True)

        emit_event(f"Tournament Run {run} Completed Successfully!")

        logger.export_leaderboard(engine.state)
        if run == args.runs:
            logger.export_summary(engine.state)

        for a_id, a in engine.state.agents.items():
            aggregate_scores[a_id] = aggregate_scores.get(a_id, 0) + a.resource_score
            aggregate_elo[a_id] = aggregate_elo.get(a_id, 0) + a.elo_rating

    print("\n Tournament Complete!")
    if args.runs > 1:
        print("\n=== MULTI-RUN AVERAGE RESULTS ===")
        avg_list = []
        for a_id in aggregate_scores:
            s = aggregate_scores[a_id] / args.runs
            e = aggregate_elo[a_id] / args.runs
            avg_list.append((a_id, s, e))
        avg_list.sort(key=lambda x: x[1], reverse=True)
        for rank, (a, s, e) in enumerate(avg_list, start=1):
            print(f"{rank}. {a} | Avg Score: {s:.1f} | Avg Elo: {e:.1f}")

    print("Logs exported successfully.")
    print("Pushing final data to browser and gracefully spinning down server...")
    time.sleep(2.0)
    print("Engine Shutdown Complete. Port 5000 formally released.")


if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
