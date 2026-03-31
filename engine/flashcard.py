"""
engine/flashcard.py
====================
The Runentafel — a vocabulary flashcard system.
Words are drawn from the current chapter's language focus and SRS weak items.
Completing a round restores Mana instead of awarding XP,
making it a recovery mechanic when the player is running low.
"""

import json
import os

FLASHCARD_PATH = os.path.join(os.path.dirname(__file__), "..", "save", "flashcards.json")


def load_flashcard_history() -> dict:
    """Load seen flashcard words to avoid repetition."""
    if not os.path.exists(FLASHCARD_PATH):
        return {}
    with open(FLASHCARD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_flashcard_history(history: dict) -> None:
    os.makedirs(os.path.dirname(FLASHCARD_PATH), exist_ok=True)
    with open(FLASHCARD_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def mark_seen(word: str) -> None:
    """Mark a word as seen in a flashcard round."""
    history = load_flashcard_history()
    history[word.lower()] = history.get(word.lower(), 0) + 1
    save_flashcard_history(history)


def get_seen_count(word: str) -> int:
    history = load_flashcard_history()
    return history.get(word.lower(), 0)


def mana_reward(correct: int, total: int) -> int:
    """
    Calculate mana reward for a flashcard round.
    Perfect round: +25 Mana. Each correct answer: +5 Mana. Min 0.
    """
    base = correct * 5
    if correct == total:
        base += 10  # perfect round bonus
    return base