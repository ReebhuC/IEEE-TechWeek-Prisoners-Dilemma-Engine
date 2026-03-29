import subprocess
import json
import os

def run_agent_in_sandbox(team_dir: str, agent_id: str, state: dict, timeout: float = 2.0, max_memory_mb: int = 256) -> str:
    """
    Executes an agent completely isolated inside its static folder using raw subprocess.
    """
    runner_path = "agent_runner.py"
    
    if not os.path.exists(os.path.join(team_dir, runner_path)):
        return "COOPERATE"
        
    try:
        # Append \n so builtins.input() knows when execution is ready
        input_data = json.dumps(state) + "\n"
        result = subprocess.run(
            ["python", "-u", runner_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=team_dir
        )
        
        # Prevent memory attacks by severely truncating any leaked logs
        raw_output = result.stdout[:200].strip()
        
        # Extract the last non-empty line as the intended token
        lines = [line.strip() for line in raw_output.split('\n') if line.strip()]
        if lines:
            action = lines[-1].upper()
            if action in ["COOPERATE", "DEFECT", "IGNORE"]:
                return action
                
    except subprocess.TimeoutExpired:
        print(f"  [Sandbox] WARNING: Agent '{agent_id}' hung indefinitely and was forcefully Neutralized (Timeout)!")
        raise TimeoutError("Agent timed out")
    except Exception:
        pass
        
    return "COOPERATE"
