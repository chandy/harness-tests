from src.leaderboard import top_player


def test_top_by_score():
    players = [
        {"name": "Zoe", "score": 3},
        {"name": "Ada", "score": 10},
        {"name": "Bob", "score": 7},
    ]
    assert top_player(players) == "Ada"


def test_single_player():
    assert top_player([{"name": "Only", "score": 1}]) == "Only"
