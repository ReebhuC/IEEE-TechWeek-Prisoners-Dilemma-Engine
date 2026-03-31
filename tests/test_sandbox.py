import os
import sys
import tempfile
import shutil

# Ensure root directory is on path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sandbox.runner import run_agent_in_sandbox
from core.engine import TournamentEngine

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


def _make_temp_team(agent_source: str) -> str:
    team_dir = tempfile.mkdtemp(prefix="team_")
    with open(os.path.join(team_dir, "my_agent.py"), "w", encoding="utf-8") as f:
        f.write(agent_source)
    runner_src = os.path.join(os.path.dirname(__file__), "..", "sandbox", "agent_runner.py")
    shutil.copy2(os.path.abspath(runner_src), os.path.join(team_dir, "agent_runner.py"))
    return team_dir


def test_warmup_missing_dependency_is_excluded():
    team_dir = _make_temp_team("import this_package_does_not_exist\ndef decide(state):\n    return 'COOPERATE'\n")
    engine = TournamentEngine(max_rounds=1)
    team_id = "team_missing_dep"
    try:
        def runner(state):
            return run_agent_in_sandbox(
                team_dir,
                team_id,
                state,
                timeout=1.0,
                raise_on_error=(state.get("round", 0) == -1),
            )

        engine.register_agent(team_id, is_bot=False, runner_func=runner, strategy_type="Participant")
        failures = engine.warmup_agents()
        assert team_id in failures, "Expected missing dependency to fail warmup"
        assert "No module named" in failures[team_id], f"Unexpected reason: {failures[team_id]}"

        # Mirrors main.py exclusion behavior
        if team_id in failures:
            engine.agent_runners.pop(team_id, None)
            engine.state.agents.pop(team_id, None)
        assert team_id not in engine.agent_runners
        assert team_id not in engine.state.agents
        print("test_warmup_missing_dependency_is_excluded passed.")
    finally:
        shutil.rmtree(team_dir, ignore_errors=True)


def test_warmup_invalid_action_is_excluded():
    team_dir = _make_temp_team("def decide(state):\n    return 'MALFORMED_ACTION'\n")
    engine = TournamentEngine(max_rounds=1)
    team_id = "team_invalid_action"
    try:
        def runner(state):
            return run_agent_in_sandbox(
                team_dir,
                team_id,
                state,
                timeout=1.0,
                raise_on_error=(state.get("round", 0) == -1),
            )

        engine.register_agent(team_id, is_bot=False, runner_func=runner, strategy_type="Participant")
        failures = engine.warmup_agents()
        assert team_id in failures, "Expected invalid action to fail warmup"
        assert "no valid action returned" in failures[team_id], f"Unexpected reason: {failures[team_id]}"

        if team_id in failures:
            engine.agent_runners.pop(team_id, None)
            engine.state.agents.pop(team_id, None)
        assert team_id not in engine.agent_runners
        assert team_id not in engine.state.agents
        print("test_warmup_invalid_action_is_excluded passed.")
    finally:
        shutil.rmtree(team_dir, ignore_errors=True)

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    print("Running sandbox robustness tests...")
    test_sandbox_crasher()
    test_sandbox_loop()
    test_warmup_missing_dependency_is_excluded()
    test_warmup_invalid_action_is_excluded()
    print("All tests passed!")
