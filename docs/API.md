# Prisoner's Dilemma Tournament API

To participate, you must write a Python script containing a single top-level function named `decide`.

## Function Signature
```python
def decide(state: dict) -> str:
    # Your code here
    return "COOPERATE"
```

## Input `state` Dictionary
You will receive the following features (all numeric values are partially obfuscated with Gaussian noise to simulate fog of war):
- `aggression_score` (float 0-1): Opponent's defect rate.
- `cooperation_trend` (float 0-1): Opponent's recent cooperation rate over last 10 turns.
- `volatility` (float 0-1): Opponent's frequency of switching strategies.
- `noisy_reputation` (float): An overall tracking score.
- `opponent_energy` (int/float): The opponent's actual resource score.
- `round` (int): Current round number.
- `tournament_phase` (str): 'early', 'mid', or 'late'.
- `resource_percentile` (float 0-1): Your current percentile rank among all players.

## Valid Returns
You must return one of three strings:
1. `"COOPERATE"`
2. `"DEFECT"`
3. `"IGNORE"`

Failure to return a valid string, or exceeding the 2-second timeout, will forcibly default your action to `"COOPERATE"`.

## Runtime Environment and Dependencies
- Your agent runs under the exact same Python interpreter as the tournament host (`sys.executable`).
- If your code imports a package that is not installed on the host machine, warmup/load will fail and your agent can be excluded before the tournament starts.
- There is no strict third-party package allowlist in this project today. Instead, the sandbox blocks specific high-risk modules/APIs (process spawning, network access, write operations, etc.).
- Practical recommendation: ensure host dependencies are installed from `requirements.txt` and communicate any extra participant package requirements ahead of time.
