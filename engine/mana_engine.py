"""
engine/mana_engine.py
======================
Manages the Mana resource — the in-game gate for AI-powered hints
and explanations. Mana regenerates over time at 10 per hour (max 100).
"""

from datetime import datetime
from engine.game_state import GameState, save_state

MANA_REGEN_PER_HOUR = 10

# Mana costs per command
MANA_COSTS = {
    "/hint":       10,
    "/translate":  15,
    "/erkläre":    20,
    "/wiederholen": 5,
}


def regen_mana(state: GameState) -> int:
    """
    Calculate and apply mana regenerated since last play session.
    Returns the amount of mana regenerated.
    TODO: track last_mana_regen timestamp in save state.
    """
    pass


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
