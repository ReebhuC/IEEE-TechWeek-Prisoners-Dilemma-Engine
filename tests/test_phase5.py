import sys
import os
import contextlib

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.engine import TournamentEngine
from sandbox.loader import load_agent_filepaths
from sandbox.runner import run_agent_in_sandbox

def main():
    print("--- PHASE 5: ADVERSARIAL TESTING ---")
    
    engine = TournamentEngine(max_rounds=5) 
    
    agents_dir = os.path.join(os.path.dirname(__file__), "dummy_agents")
    custom_agents_paths = load_agent_filepaths(agents_dir)
    
    for agent_id, filepath in custom_agents_paths.items():
        # Late binding using default argument for loop safety
        def make_sandbox_runner(path=filepath, a_id=agent_id):
            return lambda state: run_agent_in_sandbox(path, a_id, state, timeout=0.5)
            
        engine.register_agent(
            agent_id=agent_id,
            is_bot=False,
            runner_func=make_sandbox_runner(),
            strategy_type="Participant"
        )
        
    engine.run_tournament()
    
    print("\n[PHASE 5 RESULTS]")
    for a in engine.state.agents.values():
        coops = a.action_history.count("COOPERATE")
        defects = a.action_history.count("DEFECT")
        print(f"Agent: {a.agent_id} | Score: {a.resource_score} | C: {coops} | D: {defects}")
        assert defects == 0, f"{a.agent_id} somehow defected instead of defaulting to COOPERATE!"
        assert coops > 0, f"{a.agent_id} failed to register cooperate fallback!"
        
    print("\nPhase 5: ADVERSARIAL TESTING PASSED. Sandbox isolated all failures cleanly.")

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    # Suppress output so the 1000x spam doesn't clutter console natively if it escapes
    with open(os.devnull, 'w') as f, contextlib.redirect_stdout(sys.stdout):
        main()
