import os
import glob
import shutil
from typing import Dict

def load_agent_filepaths(submissions_dir: str) -> Dict[str, str]:
    """
    Returns a dictionary mapping team_id -> team_directory_path.
    Expects submissions_dir to contain subfolders per team:
    submissions/<team_id>/my_agent.py
    
    Automatically copies sandbox/agent_runner.py into each team's directory to ensure isolation.
    """
    teams = {}
    if not os.path.exists(submissions_dir):
        return teams
        
    runner_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "agent_runner.py"))
        
    for team_id in os.listdir(submissions_dir):
        team_dir = os.path.join(submissions_dir, team_id)
        if not os.path.isdir(team_dir):
            continue
            
        agent_file = os.path.join(team_dir, "my_agent.py")
        if os.path.exists(agent_file):
            # Lightweight security check for obvious traverses
            with open(agent_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if "../" in content or "..\\" in content:
                    print(f"WARNING: Skipping {team_id} due to detected path traversal substrings!")
                    continue
                    
            # Inject runner
            dest_runner = os.path.join(team_dir, "agent_runner.py")
            if os.path.exists(runner_src):
                shutil.copy2(runner_src, dest_runner)
            
            teams[team_id] = os.path.abspath(team_dir)
            
    return teams
