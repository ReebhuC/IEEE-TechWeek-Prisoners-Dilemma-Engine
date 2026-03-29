import json
import os
from datetime import datetime
from core.state import TournamentState

class TournamentLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.events_file = os.path.join(log_dir, f"events_{timestamp}.jsonl")
        self.leaderboard_file = os.path.join(log_dir, f"leaderboard_{timestamp}.csv")
        self.summary_file = os.path.join(log_dir, f"summary_{timestamp}.json")
        
    def log_event(self, event_type: str, details: dict):
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "details": details
        }
        with open(self.events_file, "a") as f:
            f.write(json.dumps(event) + "\n")
            
    def export_leaderboard(self, state: TournamentState):
        agents = sorted(state.agents.values(), key=lambda a: a.resource_score, reverse=True)
        
        with open(self.leaderboard_file, "w") as f:
            f.write("agent_id,strategy,is_bot,score,elo,reputation,adaptability\n")
            for a in agents:
                adaptability = a.get_adaptability_score()
                f.write(f"{a.agent_id},{a.strategy_type},{a.is_bot},{a.resource_score},{a.elo_rating:.2f},{a.reputation_score:.2f},{adaptability:.2f}\n")
                
    def export_summary(self, state: TournamentState):
        summary = {
            "max_rounds": state.max_rounds,
            "final_round": state.current_round,
            "agents": []
        }
        for a in state.agents.values():
            summary["agents"].append({
                "agent_id": a.agent_id,
                "strategy_type": a.strategy_type,
                "is_bot": a.is_bot,
                "final_score": a.resource_score,
                "elo_rating": a.elo_rating,
                "total_coops": a.action_history.count("COOPERATE"),
                "total_defects": a.action_history.count("DEFECT"),
                "total_ignores": a.action_history.count("IGNORE"),
                "adaptability_score": a.get_adaptability_score()
            })
            
        with open(self.summary_file, "w") as f:
            json.dump(summary, f, indent=2)
