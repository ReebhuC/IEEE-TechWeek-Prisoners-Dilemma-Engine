def decide(state):
    """
    Template agent: Cooperates if we are in the top 50%, 
    otherwise Defects aggressively.
    """
    if state.get("resource_percentile", 0.5) > 0.5:
        return "COOPERATE"
    else:
        return "DEFECT"
