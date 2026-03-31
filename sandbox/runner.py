import subprocess
import json
import os
import sys
import threading
import time


class AgentLoadError(RuntimeError):
    """Raised when an agent's subprocess fails to load or produce a valid action."""
    pass


def run_agent_in_sandbox(team_dir: str, agent_id: str, state: dict,
                         timeout: float = 5.0, max_memory_mb: int = 256,
                         raise_on_error: bool = False) -> str:
    """
    Executes an agent completely isolated inside its static folder.

    FIX 3: Uses sys.executable to guarantee the same Python interpreter as the engine.
    FIX 2: Enforces a memory limit via a psutil watchdog thread.

    Args:
        raise_on_error: If True, raises AgentLoadError instead of returning COOPERATE
                        when the subprocess produces an error. Used during warmup so
                        broken agents can be detected and excluded.
    """
    runner_path = "agent_runner.py"

    if not os.path.exists(os.path.join(team_dir, runner_path)):
        return "COOPERATE"

    try:
        input_data = json.dumps(state) + "\n"

        # FIX 3: sys.executable pins the exact interpreter — no PATH ambiguity
        proc = subprocess.Popen(
            [sys.executable, "-u", runner_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=team_dir,
        )

        # FIX 2: Memory watchdog — kills the subprocess if it exceeds the limit
        _memory_killed = [False]
        _stop_guard = threading.Event()

        def _memory_guard():
            try:
                import psutil
                ps = psutil.Process(proc.pid)
                while not _stop_guard.is_set() and proc.poll() is None:
                    try:
                        mem_mb = ps.memory_info().rss / 1_048_576
                        if mem_mb > max_memory_mb:
                            proc.kill()
                            _memory_killed[0] = True
                            return
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        return
                    time.sleep(0.05)
            except ImportError:
                pass  # psutil unavailable — install via: pip install psutil

        guard = threading.Thread(target=_memory_guard, daemon=True)
        guard.start()

        try:
            stdout, stderr = proc.communicate(input=input_data, timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()  # drain pipes to avoid OS-level deadlock
            raise TimeoutError("Agent timed out")
        finally:
            _stop_guard.set()  # always stop the memory guard

        if _memory_killed[0]:
            msg = f"Agent '{agent_id}' exceeded {max_memory_mb}MB memory limit."
            print(f"  [Sandbox] !! {msg}")
            if raise_on_error:
                raise AgentLoadError(msg)
            return "COOPERATE"

        # Truncate output to prevent stdout-flooding memory attacks
        raw_output = stdout[:200].strip()
        stderr_output = stderr.strip() if stderr else ""

        if raise_on_error and stderr_output:
            # Warmup should reject agents that failed to load/parse even if stdout fell back.
            first_line = stderr_output.splitlines()[0] if stderr_output.splitlines() else stderr_output
            if first_line.startswith(("JSON_ERR", "LOAD_ERR", "NO_DECIDE_ERR")):
                raise AgentLoadError(f"Agent '{agent_id}' failed: {first_line}")

        # Extract the last non-empty line as the intended action token
        lines = [line.strip() for line in raw_output.split("\n") if line.strip()]
        if lines:
            action = lines[-1].upper()
            if action in ("COOPERATE", "DEFECT", "IGNORE"):
                return action

        # Subprocess produced no valid action — collect the error reason
        if stderr_output:
            # Surface the first meaningful error line from the subprocess
            error_line = next(
                (l for l in stderr_output.splitlines() if l.strip()
                 and not l.startswith("Exception ignored")),
                stderr_output.splitlines()[0] if stderr_output.splitlines() else "unknown error"
            )
        else:
            error_line = f"no valid action returned (stdout={raw_output!r})"

        if raise_on_error:
            raise AgentLoadError(f"Agent '{agent_id}' failed: {error_line}")

    except TimeoutError:
        msg = f"Agent '{agent_id}' timed out during warmup."
        print(f"  [Sandbox] !! {msg}")
        raise
    except AgentLoadError:
        raise  # Always propagate load errors
    except Exception as e:
        if raise_on_error:
            raise AgentLoadError(f"Agent '{agent_id}' runner exception: {e}")

    return "COOPERATE"
