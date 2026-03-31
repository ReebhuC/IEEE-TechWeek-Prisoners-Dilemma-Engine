"""
Diagnostic script: measures timing impact of security changes and identifies
new compatibility problems with the allowlist.
"""
import subprocess
import sys
import json
import os
import shutil
import tempfile
import time
import threading

STATE = json.dumps({
    "aggression_score": 0.5, "cooperation_trend": 0.5, "volatility": 0.5,
    "noisy_reputation": 0.5, "opponent_energy": 100, "round": 1,
    "tournament_phase": "early", "resource_percentile": 0.5
}) + "\n"

RUNNER_SRC = os.path.abspath("sandbox/agent_runner.py")

def run_agent_code(agent_code: str, timeout=5) -> tuple:
    """Returns (stdout, stderr) for a given agent source code."""
    tmp = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmp, "my_agent.py"), "w") as f:
            f.write(agent_code)
        shutil.copy(RUNNER_SRC, os.path.join(tmp, "agent_runner.py"))
        p = subprocess.run(
            [sys.executable, "-u", "agent_runner.py"],
            input=STATE, capture_output=True, text=True, cwd=tmp, timeout=timeout
        )
        return p.stdout.strip(), p.stderr.strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ── SECTION 1: MODULE ALLOWLIST COMPATIBILITY ────────────────────────────────
print("=" * 60)
print("SECTION 1: MODULE ALLOWLIST — what participants can import")
print("=" * 60)

modules_to_test = {
    # stdlib participants might commonly use
    "json":        "import json\ndef decide(s): return 'COOPERATE'\n",
    "os":          "import os\ndef decide(s): return 'COOPERATE'\n",
    "sys":         "import sys\ndef decide(s): return 'COOPERATE'\n",
    "random":      "import random\ndef decide(s): return 'COOPERATE'\n",
    "math":        "import math\ndef decide(s): return 'COOPERATE'\n",
    "io":          "import io\ndef decide(s): return 'COOPERATE'\n",
    "typing":      "import typing\ndef decide(s): return 'COOPERATE'\n",
    "collections": "import collections\ndef decide(s): return 'COOPERATE'\n",
    "struct":      "import struct\ndef decide(s): return 'COOPERATE'\n",
    "pathlib":     "import pathlib\ndef decide(s): return 'COOPERATE'\n",
    # third-party participants might want
    "numpy":       "import numpy as np\ndef decide(s): return 'COOPERATE'\n",
    "pandas":      "import pandas as pd\ndef decide(s): return 'COOPERATE'\n",
    "sklearn":     "import sklearn\ndef decide(s): return 'COOPERATE'\n",
    # importlib bypass attempt
    "importlib_bypass": "import importlib\nos=importlib.import_module('os')\ndef decide(s): return 'COOPERATE'\n",
}

for label, code in modules_to_test.items():
    out, err = run_agent_code(code)
    if err == "" and out == "COOPERATE":
        status = "✅ ALLOWED — works fine"
    elif "blocked by security policy" in err:
        status = "🚫 BLOCKED by allowlist → agent silently COOPERATES"
    elif "LOAD_ERR" in err:
        if "No module named" in err or "ModuleNotFoundError" in err:
            status = "⚠  NOT INSTALLED on this machine → silently COOPERATES"
        else:
            status = f"❌ LOAD_ERR: {err[10:70]}"
    elif out == "COOPERATE" and err:
        status = f"⚠  HAD STDERR but returned COOPERATE: {err[:60]}"
    else:
        status = f"? out={out!r} err={err[:50]!r}"
    print(f"  {label:20s} {status}")

# ── SECTION 2: SUBPROCESS TIMING ─────────────────────────────────────────────
print()
print("=" * 60)
print("SECTION 2: SUBPROCESS TIMING per call (n=10 samples)")
print("=" * 60)

normal_code = "def decide(s): return 'COOPERATE'\n"
times = []
for i in range(10):
    t0 = time.perf_counter()
    run_agent_code(normal_code)
    times.append(time.perf_counter() - t0)

avg_ms = sum(times) / len(times) * 1000
min_ms = min(times) * 1000
max_ms = max(times) * 1000

print(f"  Per-call avg: {avg_ms:.0f}ms  min: {min_ms:.0f}ms  max: {max_ms:.0f}ms")

# Extrapolate to full tournament
for n_teams in [10, 15, 20, 30]:
    for n_rounds in [200, 500]:
        total_calls = n_teams * n_rounds  # 1 subprocess call per custom agent per round
        total_s = total_calls * (avg_ms / 1000)
        print(f"  {n_teams} teams × {n_rounds} rounds → ~{total_calls} calls "
              f"→ est. {total_s/60:.1f} min")

# ── SECTION 3: MEMORY GUARD THREAD BUG ───────────────────────────────────────
print()
print("=" * 60)
print("SECTION 3: psutil memory guard — race condition check")
print("=" * 60)

# Run 5 calls and watch stderr for NoSuchProcess errors
import io as _io
errors_seen = []
for i in range(5):
    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "my_agent.py"), "w") as f:
        f.write("def decide(s): return 'COOPERATE'\n")
    shutil.copy(RUNNER_SRC, os.path.join(tmp, "agent_runner.py"))

    # Replicate runner logic so we see thread tracebacks
    captured = _io.StringIO()
    import sys as _sys
    old_stderr = _sys.stderr

    proc = subprocess.Popen(
        [sys.executable, "-u", "agent_runner.py"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=tmp
    )
    _memory_killed = [False]
    _stop = threading.Event()
    def _guard():
        try:
            import psutil
            ps = psutil.Process(proc.pid)
            while not _stop.is_set() and proc.poll() is None:
                try:
                    mem = ps.memory_info().rss / 1_048_576
                    if mem > 256:
                        proc.kill(); _memory_killed[0] = True; return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return
                _stop.wait(0.05)
        except Exception as e:
            errors_seen.append(str(e))
    t = threading.Thread(target=_guard, daemon=True); t.start()
    try:
        out, _ = proc.communicate(input=STATE, timeout=3.0)
    except subprocess.TimeoutExpired:
        proc.kill(); proc.communicate()
    finally:
        _stop.set()
    shutil.rmtree(tmp, ignore_errors=True)

if errors_seen:
    print(f"  ❌ Race condition confirmed: {errors_seen[0]}")
    print(f"     Occurred {len(errors_seen)}/5 times")
else:
    print("  ✅ No race conditions detected in 5 runs")

print()
print("Done.")
