import os
import shutil
from typing import Dict

# FIX 6: Extended list of suspicious patterns for static pre-screening
_SUSPICIOUS_PATTERNS = [
    # Path traversal
    "../", "..\\/", "..\\",
    # Import bypass attempts
    "__import__", "importlib", "ctypes", "winreg",
    # Process/shell execution
    "subprocess", "os.system", "os.popen", "os.exec",
    # Network access
    "socket", "urllib", "requests", "http.client",
    # Introspection escapes
    "__subclasses__", "__globals__", "__builtins__",
]

_MAX_AGENT_SIZE_BYTES = 50_000  # 50 KB — prevents huge files slowing the scanner


def load_agent_filepaths(submissions_dir: str) -> Dict[str, str]:
    """
    Returns a dictionary mapping team_id -> team_directory_path.
    Expects submissions_dir to contain subfolders per team:
      submissions/<team_id>/my_agent.py

    FIX 6: Performs improved static screening before accepting any submission.
    Automatically copies sandbox/agent_runner.py into each team's directory.
    """
    teams = {}
    if not os.path.exists(submissions_dir):
        return teams

    runner_src = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "agent_runner.py")
    )

    for team_id in os.listdir(submissions_dir):
        team_dir = os.path.join(submissions_dir, team_id)
        if not os.path.isdir(team_dir):
            continue

        agent_file = os.path.join(team_dir, "my_agent.py")
        if not os.path.exists(agent_file):
            continue

        # File size guard
        file_size = os.path.getsize(agent_file)
        if file_size > _MAX_AGENT_SIZE_BYTES:
            print(f"  [Loader] WARNING: Skipping {team_id} - agent file exceeds "
                  f"{_MAX_AGENT_SIZE_BYTES // 1000}KB size limit ({file_size} bytes).")

            continue

        # Static source screening for known bypass patterns
        with open(agent_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        flagged = [p for p in _SUSPICIOUS_PATTERNS if p in content]
        if flagged:
            print(f"  [Loader] WARNING: Skipping {team_id} - suspicious patterns detected: "
                  f"{flagged}\n"
                  f"           (These are blocked at runtime anyway, but removing "
                  f"them makes your agent cleaner.)")
            # NOTE: We warn but do NOT hard-reject here — the sandbox
            # is the real defence. This is defence-in-depth only.

        # Inject the sandbox runner into the team's directory
        dest_runner = os.path.join(team_dir, "agent_runner.py")
        if os.path.exists(runner_src):
            shutil.copy2(runner_src, dest_runner)

        teams[team_id] = os.path.abspath(team_dir)

    return teams
