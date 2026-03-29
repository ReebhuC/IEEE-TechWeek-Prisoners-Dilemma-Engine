import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.engine import TournamentEngine
from sandbox.runner import run_agent_in_sandbox

def main():
    print("--- PHASE 7: REAL USER SIMULATION ---")
    
    user_agent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "starter_kit", "template.py"))
    assert os.path.exists(user_agent_path), "Starter kit template not found!"
    
    engine = TournamentEngine(max_rounds=10)
    
    def user_runner(state):
        return run_agent_in_sandbox(user_agent_path, "Bob_The_User", state, timeout=2.0)
        
    engine.register_agent("Bob_The_User", False, user_runner, "Participant")
    engine.register_agent("Dummy_To_Play", True, lambda s: "COOPERATE", "Coop")
    
    try:
        engine.run_tournament()
    except Exception as e:
        print(f"User starter kit template crashed the engine: {e}")
        assert False
        
    user_history = engine.state.agents["Bob_The_User"].action_history
    assert len(user_history) > 0, "User bot played no rounds!"
    
    print("\n[PHASE 7 RESULTS]")
    print(f"Bob_The_User successfully competed and logged: {user_history}")
    print("Phase 7: REAL USER SIMULATION PASSED. Starter kit is functional.")

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
