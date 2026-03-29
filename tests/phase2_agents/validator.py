import json
import time

def decide(state):
    # Dump state to a unique file so we can assert on it natively
    filename = f"phase2_state_{time.time_ns()}.json"
    with open(filename, "w") as f:
        json.dump(state, f)
    return "COOPERATE"
