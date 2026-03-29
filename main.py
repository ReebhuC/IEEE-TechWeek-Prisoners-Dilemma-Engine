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

def main():
    parser = argparse.ArgumentParser(description="Prisoner's Dilemma Tournament Engine")
    parser.add_argument("--rounds", type=int, default=500, help="Number of rounds")
    parser.add_argument("--agents-dir", type=str, default="submissions", help="Directory for custom agents")
    parser.add_argument("--runs", type=int, default=1, help="Number of multi-runs for averaging")
    args = parser.parse_args()
    
    # SECTION 6: FAIRNESS
    random.seed(42)
    
    logger = TournamentLogger()
    
    def handle_round_end(state):
        if state.current_round == state.max_rounds: # Only push at the very end
            agents = sorted(state.agents.values(), key=lambda a: a.resource_score, reverse=True)
            leaderboard_data = [{
                "agent_id": a.agent_id,
                "strategy_type": a.strategy_type,
                "score": a.resource_score,
                "elo": a.elo_rating
            } for a in agents]
            print(f"  [Frontend] Webpage Dashboard Updated (FINAL SCORES)!")
            emit_leaderboard(leaderboard_data)
            time.sleep(0.05) # Yield OS scheduling so Werkzeug can physically push the final socket payload
            
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
        engine = TournamentEngine(max_rounds=args.rounds, on_round_end=handle_round_end, on_event=handle_event)
        
        for name, bot_class in BUILT_IN_BOTS.items():
            engine.register_agent(
                agent_id=f"Bot_{name}",
                is_bot=True,
                runner_func=bot_class().decide,
                strategy_type=name
            )
            
        custom_agents = load_agent_filepaths(args.agents_dir)
        for team_id, team_dir in custom_agents.items():
            def make_sandbox_runner(t_dir=team_dir, a_id=team_id):
                tracker = {"strikes": 0}
                def runner(state):
                    if tracker["strikes"] >= 5:
                        return "COOPERATE"
                    try:
                        return run_agent_in_sandbox(t_dir, a_id, state, timeout=2.0)
                    except TimeoutError:
                        tracker["strikes"] += 1
                        if tracker["strikes"] == 5:
                            print(f"  [Engine] 🛑 {a_id} HIT 5 TIMEOUT STRIKES! Perma-banned to instantly COOPERATE for the rest of the tournament.")
                        raise # Let engine catch it to print FAILED during warmup, engine defaults to COOPERATE properly
                return runner
                
            engine.register_agent(
                agent_id=team_id,
                is_bot=False,
                runner_func=make_sandbox_runner(),
                strategy_type="Participant"
            )
            
        # Forcibly clear any stale HTML data lingering in un-refreshed browser tabs
        emit_leaderboard([])
            
        emit_event(f"Tournament Run {run} Started!")
        engine.run_tournament()
        
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
    
    # Give the background Thread Web Server 2 full seconds to completely drain its Socket 
    # and definitively push the absolute final scoreboard packets onto the browser
    print("Pushing final data to browser and gracefully spinning down server...")
    time.sleep(2.0)
    print("Engine Shutdown Complete. Port 5000 formally released. You can safely launch the next iteration!")

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
