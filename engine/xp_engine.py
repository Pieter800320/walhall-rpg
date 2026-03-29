"""
engine/xp_engine.py
====================
Handles all XP gain, level-up logic, and CEFR level mapping.
No AI calls — pure Python.
"""

from engine.game_state import GameState, save_state

# XP required to REACH each level (i.e. total XP needed from level 1)
XP_THRESHOLDS = {i: i * 100 for i in range(1, 42)}

CEFR_MAP = [
    (range(1,  6),  "A1"),
    (range(6,  13), "A2"),
    (range(13, 21), "B1"),
    (range(21, 31), "B2"),
    (range(31, 41), "C1"),
]

# XP rewards
XP_CORRECT_BASE   = 10
XP_FAST_BONUS     = 5    # answer under 20 seconds
XP_STREAK_BONUS   = 25   # every 5 correct in a row
XP_QUEST_COMPLETE = 100  # base quest completion reward
XP_DAILY_STREAK   = 15   # for maintaining daily streak


def award_xp(state: GameState, amount: int) -> dict:
    """
    Add XP to state, handle level-ups, persist to disk.
    Returns: { xp_gained, levelled_up, new_level, old_level }
    """
    old_level = state.level
    state.xp += amount

    # Level-up loop — player may gain multiple levels at once
    levelled_up = False
    while True:
        xp_needed = xp_needed_for_next_level(state.level)
        if state.xp >= xp_needed and state.level < 40:
            state.xp -= xp_needed
            state.level += 1
            levelled_up = True
        else:
            break

    # Update xp_to_next for the UI progress bar
    state.xp_to_next = xp_needed_for_next_level(state.level)

    save_state(state)

    return {
        "xp_gained":   amount,
        "levelled_up": levelled_up,
        "old_level":   old_level,
        "new_level":   state.level,
    }


def get_cefr_level(level: int) -> str:
    """Return CEFR string for a given game level."""
    for level_range, cefr in CEFR_MAP:
        if level in level_range:
            return cefr
    return "C1"


def xp_needed_for_next_level(current_level: int) -> int:
    """XP required to advance from current_level to current_level + 1."""
    return XP_THRESHOLDS.get(current_level + 1, 9999)


def calculate_answer_xp(correct: bool, fast: bool, streak: int, multiplier: float = 1.0) -> int:
    """
    Calculate total XP for a single answer.
    correct:    was the answer correct?
    fast:       answered in under 20 seconds?
    streak:     current correct-answer streak count
    multiplier: item bonus multiplier from item_engine
    """
    if not correct:
        return 0

    xp = XP_CORRECT_BASE
    if fast:
        xp += XP_FAST_BONUS
    if streak > 0 and streak % 5 == 0:
        xp += XP_STREAK_BONUS

    return int(xp * multiplier)
