import json
import os
import re
from datetime import datetime
from core.state import TournamentState

_MAX_LOG_SETS = 10   # FIX 17: Keep at most this many timestamped log sets


class TournamentLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # FIX 17: Rotate out old log sets before creating new ones
        self._cleanup_old_logs()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.events_file = os.path.join(log_dir, f"events_{timestamp}.jsonl")
        self.leaderboard_file = os.path.join(log_dir, f"leaderboard_{timestamp}.csv")
        self.summary_file = os.path.join(log_dir, f"summary_{timestamp}.json")

    def _cleanup_old_logs(self):
        """
        FIX 17: Removes old log files so the /logs directory doesn't grow forever.
        Keeps only the _MAX_LOG_SETS most recent timestamp groups.
        """
        try:
            all_files = os.listdir(self.log_dir)
            # Collect all unique timestamps embedded in log filenames
            timestamps = set()
            for f in all_files:
                m = re.search(r"(\d{8}_\d{6})", f)
                if m:
                    timestamps.add(m.group(1))

            sorted_ts = sorted(timestamps)
            # Any timestamps beyond the keep window are expired
            expired = sorted_ts[:-_MAX_LOG_SETS] if len(sorted_ts) >= _MAX_LOG_SETS else []

            for ts in expired:
                for f in all_files:
                    if ts in f:
                        try:
                            os.remove(os.path.join(self.log_dir, f))
                        except OSError:
                            pass  # File already deleted or locked — skip silently
        except Exception:
            pass  # Log cleanup must never crash the engine

    def log_event(self, event_type: str, details: dict):
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "details": details,
        }
        with open(self.events_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    def export_leaderboard(self, state: TournamentState):
        agents = sorted(
            state.agents.values(), key=lambda a: a.resource_score, reverse=True
        )
        with open(self.leaderboard_file, "w") as f:
            f.write("agent_id,strategy,is_bot,score,elo,reputation,adaptability\n")
            for a in agents:
                adaptability = a.get_adaptability_score()
                f.write(
                    f"{a.agent_id},{a.strategy_type},{a.is_bot},"
                    f"{a.resource_score},{a.elo_rating:.2f},"
                    f"{a.reputation_score:.2f},{adaptability:.2f}\n"
                )

    def export_summary(self, state: TournamentState):
        summary = {
            "max_rounds": state.max_rounds,
            "final_round": state.current_round,
            "agents": [],
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
                "adaptability_score": a.get_adaptability_score(),
            })
        with open(self.summary_file, "w") as f:
            json.dump(summary, f, indent=2)
