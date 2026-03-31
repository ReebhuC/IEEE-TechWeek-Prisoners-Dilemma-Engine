# Operator Runbook — IEEE TechWeek Prisoner's Dilemma Engine

## Pre-Event Setup (do this the night before)

```bash
# 1. Install all dependencies (pinned versions)
pip install -r requirements.txt

# 2. Verify engine starts cleanly
python main.py --rounds 10
# → Should print "Engine Shutdown Complete" within ~30 seconds
# → Open http://localhost:5000 — leaderboard should appear
```

---

## Quick Start (event day)

```bash
# Standard 500-round tournament
python main.py --rounds 500

# Open the live dashboard in a browser
# → http://localhost:5000
```

The leaderboard updates **every 10 rounds** automatically.

---

## Adding Team Submissions

Each team must submit a single file: `submissions/<team_name>/my_agent.py`

```
submissions/
  team_alpha/
    my_agent.py     ← only this file needed
  team_beta/
    my_agent.py
```

The engine injects the sandbox runner automatically — teams do **not** submit `agent_runner.py`.

### File Requirements
- Function named `decide(state: dict) -> str`
- Returns exactly `"COOPERATE"`, `"DEFECT"`, or `"IGNORE"`
- Must run in under **2 seconds** per call
- Must use under **256 MB** of RAM

---

## Common Commands

| Command | Purpose |
|---|---|
| `python main.py` | Standard 500-round tournament (5s timeout, 50-round grace period) |
| `python main.py --rounds 100` | Quick 100-round test |
| `python main.py --runs 3` | 3-run average (for finals) |
| `python main.py --timeout 8.0` | Longer timeout if teams load large models (~200MB+) |
| `python main.py --grace-period 100` | Extend grace period to 100 rounds |
| `python main.py --agents-dir custom/` | Use a different submissions folder |
| `python tests/test_phase8.py` | Full system rehearsal test |

---

## Strike System

Agents that time out (> default 5s per call) accumulate **strikes**:
- **Grace period** (first 50 rounds by default): timeouts happen, agent defaults to COOPERATE, **no strike counted**. This forgives early-round system load spikes and model cold-start times.
- **1–4 strikes** → agent continues playing (defaults to COOPERATE on that call)
- **5 strikes** → permanently forced to `COOPERATE` for the rest of the tournament

Strikes do **not** accumulate during warmup or the grace period.

Tuning tips:
- Increase `--timeout 8.0` if teams are loading large PyTorch models (>100MB)
- Increase `--grace-period 100` if you want more forgiveness
- Teams using `torch.load()` per call should save small models (<50MB) to avoid slow cold starts

---

## Recovery Procedures

### Engine crashed mid-tournament
```bash
# Restart cleanly — port 5000 is released on crash
python main.py --rounds 500
```
If port 5000 is still in use:
```bash
# Windows: Find and kill the process using port 5000
netstat -ano | findstr :5000
taskkill /PID <pid> /F
```

### Browser shows blank leaderboard
- The leaderboard pushes every 10 rounds — wait up to 30 seconds
- Hard-refresh the browser (Ctrl+Shift+R)
- If still blank, restart the engine (the browser reconnects automatically via Socket.IO)

### Agent perma-banned before it should be
- Check if the agent's `decide()` is genuinely slow (> 2s)
- If it's a false positive, restart the engine — strikes reset each run

### Logs directory too large
- Log rotation keeps only the 10 most recent runs automatically
- Manual cleanup: `del logs\*` (Windows) or `rm logs/*` (bash)

---

## Architecture Overview

```
main.py               → Entry point, CLI args, multi-run loop
core/engine.py        → Tournament loop, round pairing, drift event
core/state.py         → AgentState, TournamentState, score tracking
core/features.py      → Feature vector computation (what agents see)
core/game.py          → Payoff matrix (C/D/I resolution)
core/scoring.py       → Elo rating update
core/events.py        → Mid-tournament drift event
sandbox/runner.py     → Subprocess isolation (sys.executable, memory guard)
sandbox/agent_runner.py → Sandboxed Python process (import allowlist)
sandbox/loader.py     → Loads team directories, injects runner
server/app.py         → Flask + Socket.IO live dashboard backend
server/templates/     → index.html dashboard frontend
utils/logger.py       → CSV/JSON log export + rotation
bots/strategies.py    → Built-in bot strategies
submissions/          → Team agent submissions go here
```

---

## Security Notes

- Participant code runs in an **isolated subprocess** with process-level isolation
- Dangerous modules are **blacklisted** at startup: `os`, `subprocess`, `socket`, `urllib`, `requests`, `pathlib`, `shutil`, `ctypes`, `winreg`, `signal`, `mmap`
- Participants **can** freely use: `numpy`, `pandas`, `json`, `random`, `math`, `collections`, `typing`, and all other non-system libraries
- `eval`, `exec`, and `compile` are disabled post-load
- `open()` is restricted to only reading `my_agent.py` itself
- Memory is capped at **256 MB** per agent call (requires `psutil`)
- The dashboard is restricted to **localhost CORS only**
