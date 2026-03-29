"""
engine/xp_engine.py
====================
Handles all XP gain, level-up logic, and CEFR level mapping.
No AI calls — pure Python.
"""

from engine.game_state import GameState, save_state

# XP required to reach each level (cumulative thresholds)
# Levels 1-5 = A1, 6-12 = A2, 13-20 = B1, 21-30 = B2, 31-40 = C1
XP_PER_LEVEL = {i: i * 100 for i in range(1, 41)}

CEFR_MAP = {
    range(1, 6):   "A1",
    range(6, 13):  "A2",
    range(13, 21): "B1",
    range(21, 31): "B2",
    range(31, 41): "C1",
}

# XP rewards
XP_CORRECT_BASE    = 10
XP_FAST_BONUS      = 5       # answer under 20 seconds
XP_STREAK_BONUS    = 25      # every 5 correct in a row
XP_QUEST_COMPLETE  = 100     # base quest completion reward
XP_DAILY_STREAK    = 15      # for maintaining daily streak


def award_xp(state: GameState, amount: int) -> dict:
    """
    Add XP to the state, handle level-ups, persist.
    Returns a result dict: { xp_gained, levelled_up, new_level }
    """
    # TODO: implement level-up loop and XP threshold checks
    pass


def get_cefr_level(level: int) -> str:
    """Return CEFR string for a given game level."""
    for level_range, cefr in CEFR_MAP.items():
        if level in level_range:
            return cefr
    return "C1"


def xp_needed_for_next_level(current_level: int) -> int:
    """XP required to advance from current_level to current_level + 1."""
    return XP_PER_LEVEL.get(current_level + 1, 9999)
