import os
import sys

# Ensure root directory is on path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sandbox.runner import run_agent_in_sandbox

def test_sandbox_crasher():
    filepath = os.path.join(os.path.dirname(__file__), "dummy_agents", "crasher.py")
    res = run_agent_in_sandbox(filepath, "crasher", {}, timeout=0.5)
    assert res == "COOPERATE", f"Expected COOPERATE, got {res}"
    print("test_sandbox_crasher passed.")
    
def test_sandbox_loop():
    filepath = os.path.join(os.path.dirname(__file__), "dummy_agents", "infinite_loop.py")
    res = run_agent_in_sandbox(filepath, "infinite_loop", {}, timeout=0.5)
    assert res == "COOPERATE", f"Expected COOPERATE, got {res}"
    print("test_sandbox_loop passed.")

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    print("Running sandbox robustness tests...")
    test_sandbox_crasher()
    test_sandbox_loop()
    print("All tests passed!")
