import sys
import json
import importlib.util
import builtins

# PHASE 1: Safely neutralize system-level filesystem and network access dynamically
dangerous_modules = [
    "os", "subprocess", "socket", "urllib", "requests", 
    "pathlib", "shutil"
]
for mod in dangerous_modules:
    sys.modules[mod] = None

# Builtin restrictions blocking malicious code from traversing file structures
real_open = builtins.open
def safe_open(file, *args, **kwargs):
    if str(file).endswith("my_agent.py"):
        return real_open(file, *args, **kwargs)
    raise PermissionError("Blocked by Sandbox")
builtins.open = safe_open

def main():
    # 1. Read JSON state from raw stdin perfectly
    raw_input = builtins.input()
    try:
        state = json.loads(raw_input)
    except Exception as e:
        sys.stderr.write(f"JSON_ERR: {e}\n")
        print("COOPERATE")
        return

    # 2. Dynamically load the participant's code while Python internals are still alive
    agent_file = "my_agent.py"
    try:
        spec = importlib.util.spec_from_file_location("participant_agent", agent_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        sys.stderr.write(f"LOAD_ERR: {e}\n")
        print("COOPERATE")
        return

    # 3. Extract the `decide` method
    if not hasattr(module, 'decide'):
        sys.stderr.write("NO_DECIDE_ERR\n")
        print("COOPERATE")
        return

    # --- PHASE 2: ABSOLUTE LOCKDOWN ---
    # We successfully compiled and loaded the module natively!
    # Now we aggressively aggressively murder Python's evaluation engines BEFORE yielding control
    builtins.eval = None
    builtins.exec = None
    
    # We murder the sys module globally so the agent cannot inspect module references
    sys.modules["sys"] = None
    
    # 4. Safely hand execution control natively to the agent!
    try:
        action = module.decide(state)
        # We explicitly print exactly the token to push it back down stdout
        print(str(action).strip())
    except Exception as e:
        # sys is dead, we can't reliably push to stderr anymore, just fail gracefully
        print("COOPERATE")

if __name__ == "__main__":
    main()
