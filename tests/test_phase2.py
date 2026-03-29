import sys
import os
import glob
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.engine import TournamentEngine
from sandbox.loader import load_agent_filepaths
from sandbox.runner import run_agent_in_sandbox

def main():
    print("--- PHASE 2: STATE VALIDATION ---")
    
    # Cleanup any old dumps
    for _ in range(2):
        for f in glob.glob("phase2_state_*.json"):
            try: os.remove(f)
            except: pass
            
    engine = TournamentEngine(max_rounds=5) 
    
    agents_dir = os.path.join(os.path.dirname(__file__), "phase2_agents")
    custom_agents_paths = load_agent_filepaths(agents_dir)
    
    path = custom_agents_paths.get("validator")
    
    for i in range(2):
        a_id = f"validator_{i}"
        def make_sandbox_runner(p=path, a=a_id):
            return lambda state: run_agent_in_sandbox(p, a, state, timeout=2.0)
            
        engine.register_agent(a_id, False, make_sandbox_runner(), "Participant")
        
    engine.run_tournament()
    
    dumps = glob.glob("phase2_state_*.json")
    print(f"Recorded state dumps: {len(dumps)}")
    assert len(dumps) > 0, "No state dumps captured!"
    
    all_keys = [
        "aggression_score", "cooperation_trend", "volatility", 
        "noisy_reputation", "opponent_energy", "round", 
        "tournament_phase", "resource_percentile"
    ]
    
    for dump in dumps:
        with open(dump, "r") as f:
            state = json.load(f)
            
        for k in all_keys:
            assert k in state, f"Missing key: {k}"
            
        for k in ["aggression_score", "cooperation_trend", "volatility", "noisy_reputation", "resource_percentile"]:
            val = state[k]
            assert 0.0 <= val <= 1.0, f"Bounds exceeded for {k}: {val}"
            
        assert state["tournament_phase"] in ["early", "mid", "late"]
        assert isinstance(state["opponent_energy"], (int, float))
        assert isinstance(state["round"], int)

    print("\nPhase 2: ALL STATE VALIDATIONS PASSED.")

    # Cleanup
    for f in dumps:
        try: os.remove(f)
        except: pass

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
