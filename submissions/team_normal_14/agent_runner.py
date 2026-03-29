import sys
import json
import importlib.util
import builtins
import traceback

# SAFETY JAIL: Neutralize dangerous module resolution dynamically
dangerous_modules = [
    "os", "subprocess", "socket", "urllib", "requests", 
    "pathlib", "shutil"
]
for mod in dangerous_modules:
    sys.modules[mod] = None

# Builtin restrictions blocking file modification/execution
builtins.open = None
builtins.eval = None
builtins.exec = None

# Drop sys effectively rendering import sys useless from inside the agent
sys.modules["sys"] = None

def main():
    # 1. Read JSON state from raw stdin
    raw_input = builtins.input()
    try:
        state = json.loads(raw_input)
    except Exception:
        print("COOPERATE")
        return

    # 2. Dynamically load the participant's code
    agent_file = "my_agent.py"
    try:
        spec = importlib.util.spec_from_file_location("participant_agent", agent_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        print("COOPERATE")
        return

    # 3. Extract the `decide` method
    if not hasattr(module, 'decide'):
        print("COOPERATE")
        return

    # 4. Safely evaluate and print
    try:
        action = module.decide(state)
        # We explicitly print exactly the token to push it back down stdout
        print(str(action).strip())
    except Exception:
        print("COOPERATE")

if __name__ == "__main__":
    main()
