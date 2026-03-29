import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.engine import TournamentEngine
from sandbox.loader import load_agent_filepaths
from sandbox.runner import run_agent_in_sandbox

def main():
    print("--- PHASE 1: MINIMAL SANITY TESTING ---")
    engine = TournamentEngine(max_rounds=50) 
    
    agents_dir = os.path.join(os.path.dirname(__file__), "phase1_agents")
    custom_agents_paths = load_agent_filepaths(agents_dir)
    
    for agent_id, filepath in custom_agents_paths.items():
        # Late binding using default argument
        def make_sandbox_runner(path=filepath, a_id=agent_id):
            return lambda state: run_agent_in_sandbox(path, a_id, state, timeout=2.0)
            
        engine.register_agent(
            agent_id=agent_id,
            is_bot=False,
            runner_func=make_sandbox_runner(),
            strategy_type="Participant"
        )
        
    engine.run_tournament()
    
    print("\n[PHASE 1 RESULTS]")
    for a in engine.state.agents.values():
        coops = a.action_history.count("COOPERATE")
        defects = a.action_history.count("DEFECT")
        print(f"Agent: {a.agent_id} | Score: {a.resource_score} | C: {coops} | D: {defects}")
        
    coop_agent = engine.state.agents.get("coop")
    defect_agent = engine.state.agents.get("defect")
    rand_agent = engine.state.agents.get("random_agent")
    
    assert coop_agent is not None, "Missing coop agent"
    assert defect_agent is not None, "Missing defect agent"
    assert rand_agent is not None, "Missing random agent"

    assert coop_agent.action_history.count("DEFECT") == 0, "Coop agent defected!"
    assert defect_agent.action_history.count("COOPERATE") == 0, "Defect agent cooperated!"

    print("\nPhase 1: SANITY CHECKS PASSED: No crashes, outputs correct, logic intact.")

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
