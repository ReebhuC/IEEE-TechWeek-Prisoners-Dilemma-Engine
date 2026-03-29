import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.engine import TournamentEngine
from bots.strategies import BUILT_IN_BOTS
from sandbox.loader import load_agent_filepaths
from sandbox.runner import run_agent_in_sandbox

def setup_phase6_agents():
    agents_dir = os.path.join(os.path.dirname(__file__), "phase6_agents")
    os.makedirs(agents_dir, exist_ok=True)
    for i in range(15):
        with open(os.path.join(agents_dir, f"sandbox_bot_{i}.py"), "w") as f:
            if i % 3 == 0:
                f.write("def decide(state):\n    return 'COOPERATE'\n")
            elif i % 3 == 1:
                f.write("def decide(state):\n    return 'DEFECT'\n")
            else:
                f.write("import random\ndef decide(state):\n    return random.choice(['COOPERATE', 'DEFECT'])\n")
    return agents_dir

def main():
    print("--- PHASE 6: SCALE TESTING ---")
    start_time = time.time()
    
    engine = TournamentEngine(max_rounds=500) 
    
    # 5 built-in
    for name, bot_class in BUILT_IN_BOTS.items():
        engine.register_agent(
            agent_id=f"Internal_{name}",
            is_bot=True,
            runner_func=bot_class().decide,
            strategy_type=name
        )
        
    agents_dir = setup_phase6_agents()
    custom_agents_paths = load_agent_filepaths(agents_dir)
    
    for agent_id, filepath in custom_agents_paths.items():
        # Late binding using default parameters
        def make_sandbox_runner(path=filepath, a_id=agent_id):
            return lambda state: run_agent_in_sandbox(path, a_id, state, timeout=0.5) 
            
        engine.register_agent(
            agent_id=agent_id,
            is_bot=False,
            runner_func=make_sandbox_runner(),
            strategy_type="Participant"
        )
        
    print(f"Starting 500 round tournament with {len(engine.state.agents)} agents...")
    def on_round(state):
        if state.current_round % 100 == 0:
            print(f"  Reached round {state.current_round}... ({time.time() - start_time:.1f}s)")
            
    engine.on_round_end = on_round
    
    try:
        engine.run_tournament()
    except Exception as e:
        print(f"FATAL ERROR DURING RUN: {e}")
        sys.exit(1)
        
    end_time = time.time()
    elapsed = end_time - start_time
    
    print("\n[PHASE 6 RESULTS]")
    print(f"Total agents: {len(engine.state.agents)}")
    print(f"Total rounds: 500")
    print(f"Time elapsed: {elapsed:.2f} seconds")
    
    assert elapsed < 1800, f"Too slow! Took {elapsed} seconds (limit 1800s / 30m)"
    assert engine.state.current_round == 500, "Did not finish 500 rounds!"
    
    print("\nPhase 6: SCALE TESTING PASSED. Stable without crashes, and lightning fast.")

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
