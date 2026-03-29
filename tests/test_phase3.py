import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.engine import TournamentEngine
from bots.strategies import BUILT_IN_BOTS

def main():
    print("--- PHASE 3: BOT BEHAVIOR VERIFICATION ---")
    
    # 200 rounds as planned
    engine = TournamentEngine(max_rounds=200)
    
    for name, bot_class in BUILT_IN_BOTS.items():
        engine.register_agent(
            agent_id=f"Bot_{name}",
            is_bot=True, 
            runner_func=bot_class().decide,
            strategy_type=name
        )
        
    engine.run_tournament()
    
    print("\n[PHASE 3 RESULTS]")
    for a in engine.state.agents.values():
        coops = a.action_history.count("COOPERATE")
        defects = a.action_history.count("DEFECT")
        ignores = a.action_history.count("IGNORE")
        total = max(1, len(a.action_history))
        
        c_rate = coops / total
        d_rate = defects / total
        i_rate = ignores / total
        print(f"Agent: {a.agent_id} | C-Rate: {c_rate:.2f} | D-Rate: {d_rate:.2f} | I-Rate: {i_rate:.2f}")
        
        # Verify Behaviors
        if "Aggressor" in a.agent_id:
            assert d_rate == 1.0, "Aggressor did not always defect!"
        elif "Cooperator" in a.agent_id:
            assert c_rate == 1.0, "Cooperator did not always cooperate!"
        elif "Random" in a.agent_id:
            assert 0.1 <= c_rate <= 0.6
            assert 0.1 <= d_rate <= 0.6
            assert 0.1 <= i_rate <= 0.6
            
    print("\nPhase 3: BOT BEHAVIOR VERIFICATION PASSED.")

if __name__ == "__main__":
    main()
