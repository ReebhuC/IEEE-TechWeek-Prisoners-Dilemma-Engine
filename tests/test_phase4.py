import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.engine import TournamentEngine
from bots.strategies import BUILT_IN_BOTS

def main():
    print("--- PHASE 4: DRIFT EVENT TESTING ---")
    
    drift_triggered = False
    
    def on_event(msg):
        nonlocal drift_triggered
        if "Drift Event" in msg:
            drift_triggered = True
            
    engine = TournamentEngine(max_rounds=300, on_event=on_event)
    
    for i in range(20):
        engine.register_agent(
            agent_id=f"Bot_{i}",
            is_bot=True, 
            runner_func=BUILT_IN_BOTS["Random"]().decide,
            strategy_type="Random"
        )
        
    engine.run_tournament()
    
    assert drift_triggered, "Drift event did not trigger!"
    
    drifted_count = 0
    for a in engine.state.agents.values():
        if a.strategy_type != "Random":
            drifted_count += 1
            
    print(f"Total drifted bots: {drifted_count}/20")
    assert drifted_count == 6, f"Expected exactly 6 bots to drift, got {drifted_count}"
    
    # Check if adaptability score populated for drifted bots
    for a in engine.state.agents.values():
        if a.strategy_type != "Random":
            assert a.pre_drift_score is not None, f"pre_drift_score missing for {a.agent_id}"
            assert a.post_drift_score is not None, f"post_drift_score missing for {a.agent_id}"
    
    print("\nPhase 4: DRIFT EVENT PASSED. Exactly 30% of bots changed strategy at round 250.")

if __name__ == "__main__":
    main()
