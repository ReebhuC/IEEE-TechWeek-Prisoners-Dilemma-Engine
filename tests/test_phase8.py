import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.engine import TournamentEngine
from bots.strategies import BUILT_IN_BOTS
from sandbox.loader import load_agent_filepaths
from sandbox.runner import run_agent_in_sandbox
from utils.logger import TournamentLogger

def setup_phase8_agents():
    agents_dir = os.path.join(os.path.dirname(__file__), "phase8_agents")
    os.makedirs(agents_dir, exist_ok=True)
    # create 10 simple agents
    for i in range(10):
        with open(os.path.join(agents_dir, f"sandbox_participant_{i}.py"), "w") as f:
            f.write("def decide(state):\n    return 'COOPERATE'\n")
    return agents_dir

def main():
    print("--- PHASE 8: FULL SYSTEM REHEARSAL ---")
    agents_dir = setup_phase8_agents()
    
    # Track UI hooks without socketio native
    leaderboard_calls = []
    events_logged = []
    logger = TournamentLogger(log_dir="tests/phase8_logs")
    
    def handle_round_end(state):
        if state.current_round % 10 == 0:
            agents = sorted(state.agents.values(), key=lambda a: a.resource_score, reverse=True)
            leaderboard_data = [{
                "agent_id": a.agent_id,
                "strategy_type": a.strategy_type,
                "score": a.resource_score,
                "elo": a.elo_rating
            } for a in agents]
            leaderboard_calls.append(leaderboard_data)
            
    def handle_event(msg):
        events_logged.append(msg)
        logger.log_event("UPDATE", {"message": msg})

    engine = TournamentEngine(max_rounds=500, on_round_end=handle_round_end, on_event=handle_event)
    
    # Register 10 external agents
    custom_agents_paths = load_agent_filepaths(agents_dir)
    for agent_id, filepath in custom_agents_paths.items():
        def make_sandbox_runner(path=filepath, a_id=agent_id):
            return lambda state: run_agent_in_sandbox(path, a_id, state, timeout=0.1)
            
        engine.register_agent(
            agent_id=agent_id,
            is_bot=False,
            runner_func=make_sandbox_runner(),
            strategy_type="Participant"
        )
        
    for name, bot_class in BUILT_IN_BOTS.items():
        engine.register_agent(f"Bot_{name}", True, bot_class().decide, name)
        
    engine.run_tournament()
    
    logger.export_leaderboard(engine.state)
    logger.export_summary(engine.state)
    
    # Assertions
    assert len(leaderboard_calls) > 0, "No leaderboards were hooked into UI"
    drift_present = any("Drift Event" in ev for ev in events_logged)
    assert drift_present, "Drift event not forwarded to UI event log"
    assert os.path.exists(logger.events_file), "Logger failed to create events file"
    assert os.path.exists(logger.leaderboard_file), "Logger failed to export leaderboard"
    assert os.path.exists(logger.summary_file), "Logger failed to export summary"
    
    print("\n[PHASE 8 RESULTS]")
    print(f"Total Leaderboard UI Broadcasts: {len(leaderboard_calls)}")
    print(f"Drift UI Broadcast Successfully Verified: {drift_present}")
    print("Phase 8: FULL SYSTEM REHEARSAL PASSED. Engine is fully competitive-event ready.")

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
