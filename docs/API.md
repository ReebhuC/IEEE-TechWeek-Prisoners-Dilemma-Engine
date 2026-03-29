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
