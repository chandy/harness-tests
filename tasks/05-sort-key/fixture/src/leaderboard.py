from typing import Any


def top_player(players: list[dict[str, Any]]) -> str:
    ranked = sorted(players, key=lambda p: p["name"])
    return ranked[-1]["name"]
