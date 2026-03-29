import time
import os
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
    parser.add_argument("--agents-dir", type=str, default="agents", help="Directory for custom agents")
    args = parser.parse_args()
    
    logger = TournamentLogger()
    
    def handle_round_end(state):
        if state.current_round % 10 == 0:
            agents = sorted(state.agents.values(), key=lambda a: a.resource_score, reverse=True)
            leaderboard_data = [{
                "agent_id": a.agent_id,
                "strategy_type": a.strategy_type,
                "score": a.resource_score,
                "elo": a.elo_rating
            } for a in agents]
            emit_leaderboard(leaderboard_data)
            
    def handle_event(msg):
        emit_event(msg)
        logger.log_event("UPDATE", {"message": msg})
        print(f"[EVENT] {msg}")

    engine = TournamentEngine(max_rounds=args.rounds, on_round_end=handle_round_end, on_event=handle_event)
    
    # 1. Load Built-in Bots (run natively inside process, but we register their decide method)
    # The requirement asks them to be alongside participants, but native bots don't need sandboxing
    for name, bot_class in BUILT_IN_BOTS.items():
        engine.register_agent(
            agent_id=f"Bot_{name}",
            is_bot=True,
            runner_func=bot_class().decide,
            strategy_type=name
        )
        
    # 2. Load custom agents (isolated subprocess sandboxing)
    if not os.path.exists(args.agents_dir):
        os.makedirs(args.agents_dir)
        
    custom_agents_paths = load_agent_filepaths(args.agents_dir)
    for agent_id, filepath in custom_agents_paths.items():
        # Using late binding for loop variables!
        def make_sandbox_runner(path=filepath, a_id=agent_id):
            return lambda state: run_agent_in_sandbox(path, a_id, state, timeout=2.0)
            
        engine.register_agent(
            agent_id=agent_id,
            is_bot=False,
            runner_func=make_sandbox_runner(),
            strategy_type="Participant"
        )
        print(f"Loaded custom agent from {filepath}: {agent_id}")
        
    # Start web server
    print("Starting Flask web server on port 5000...")
    start_server_thread(port=5000)
    time.sleep(1) # short wait to ensure bound
    
    print("Starting tournament...")
    emit_event("Tournament Started!")
    
    engine.run_tournament()
    
    print("Tournament Finished!")
    emit_event("Tournament Finished! Leaderboard stabilized.")
    
    logger.export_leaderboard(engine.state)
    logger.export_summary(engine.state)
    print("Logs exported successfully.")
    
    print("Tournament complete. Check http://localhost:5000")
    print("Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")

if __name__ == "__main__":
    # Windows native spawn needs freeze_support for multiprocessing if compiled, good practice.
    from multiprocessing import freeze_support
    freeze_support()
    main()
