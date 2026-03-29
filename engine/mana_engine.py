"""
engine/mana_engine.py
======================
Manages the Mana resource — the in-game gate for AI-powered hints
and explanations. Mana regenerates over time at 10 per hour (max 100).
"""

from datetime import datetime, timezone
from engine.game_state import GameState, save_state

MANA_REGEN_PER_HOUR = 10

# Mana costs per command
MANA_COSTS = {
    "/hint":        10,
    "/translate":   15,
    "/erkläre":     20,
    "/wiederholen":  5,
}


def regen_mana(state: GameState) -> int:
    """
    Calculate and apply mana regenerated since last session.
    Uses last_played date — regenerates 10 mana per hour offline, capped at max.
    Returns the amount regenerated.
    """
    if not state.last_played:
        return 0

    try:
        last = datetime.fromisoformat(state.last_played).replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        hours_passed = (now - last).total_seconds() / 3600
        regen = min(int(hours_passed * MANA_REGEN_PER_HOUR), state.mana_max - state.mana)
        if regen > 0:
            state.mana = min(state.mana + regen, state.mana_max)
            save_state(state)
        return regen
    except Exception:
        return 0


def spend_mana(state: GameState, command: str) -> bool:
    """
    Attempt to spend mana for a command.
    Returns True if successful, False if insufficient mana.
    """
    cost = MANA_COSTS.get(command, 0)
    if state.mana < cost:
        return False
    state.mana -= cost
    save_state(state)
    return True


def can_afford(state: GameState, command: str) -> bool:
    """Check if player has enough mana for a command without spending it."""
    return state.mana >= MANA_COSTS.get(command, 0)
