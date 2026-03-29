from enum import Enum

class Action(Enum):
    COOPERATE = "COOPERATE"
    DEFECT = "DEFECT"
    IGNORE = "IGNORE"

def normalize_action(action_str: str) -> str:
    action_str = str(action_str).strip().upper()
    if action_str in ["COOPERATE", "DEFECT", "IGNORE"]:
        return action_str
    # Invalid outputs default to COOPERATE
    return Action.COOPERATE.value

def resolve_interaction(action1: str, action2: str) -> tuple[int, int]:
    """
    Returns (payoff1, payoff2) based on the payoff matrix:
      (C, C) -> +3, +3
      (C, D) -> 0, +5
      (D, C) -> +5, 0
      (D, D) -> +1, +1
      IGNORE results in a small penalty (-1, 0).
    """
    a1 = normalize_action(action1)
    a2 = normalize_action(action2)

    if a1 == Action.IGNORE.value and a2 == Action.IGNORE.value:
        return (-1, -1)
    elif a1 == Action.IGNORE.value:
        return (-1, 0)
    elif a2 == Action.IGNORE.value:
        return (0, -1)

    if a1 == Action.COOPERATE.value and a2 == Action.COOPERATE.value:
        return (3, 3)
    elif a1 == Action.COOPERATE.value and a2 == Action.DEFECT.value:
        return (0, 5)
    elif a1 == Action.DEFECT.value and a2 == Action.COOPERATE.value:
        return (5, 0)
    elif a1 == Action.DEFECT.value and a2 == Action.DEFECT.value:
        return (1, 1)

    return (0, 0)
