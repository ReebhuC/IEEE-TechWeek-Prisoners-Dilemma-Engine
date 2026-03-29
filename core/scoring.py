def update_elo(rating1: float, rating2: float, payoff1: int, payoff2: int, k_factor: int = 32) -> tuple[float, float]:
    """
    Calculates new Elo ratings for two interacting agents.
    Wins and losses are judged by strictly higher or lower payoff.
    """
    expected1 = 1 / (1 + 10 ** ((rating2 - rating1) / 400))
    expected2 = 1 / (1 + 10 ** ((rating1 - rating2) / 400))
    
    if payoff1 > payoff2:
        score1, score2 = 1.0, 0.0
    elif payoff1 < payoff2:
        score1, score2 = 0.0, 1.0
    else:
        score1, score2 = 0.5, 0.5
        
    new_rating1 = rating1 + k_factor * (score1 - expected1)
    new_rating2 = rating2 + k_factor * (score2 - expected2)
    
    return new_rating1, new_rating2
