"""
engine/srs_engine.py
=====================
Spaced Repetition System — tracks per-word and per-grammar-rule
difficulty scores. Resurfaces weak items into quests naturally.
Data is persisted to save/mistakes.json.
"""

import json
import os

MISTAKES_PATH = os.path.join(os.path.dirname(__file__), "..", "save", "mistakes.json")


def load_mistakes() -> dict:
    """Load the mistakes log. Returns empty dict if file doesn't exist."""
    if not os.path.exists(MISTAKES_PATH):
        return {}
    with open(MISTAKES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_mistakes(mistakes: dict) -> None:
    """Persist mistakes log to disk."""
    os.makedirs(os.path.dirname(MISTAKES_PATH), exist_ok=True)
    with open(MISTAKES_PATH, "w", encoding="utf-8") as f:
        json.dump(mistakes, f, indent=2, ensure_ascii=False)


def log_mistake(item: str, category: str = "grammar") -> None:
    """
    Record a mistake for a word or grammar rule.
    item: the word or rule name e.g. "Dativ case", "separable verbs"
    category: "grammar" | "vocabulary" | "spelling"
    """
    # TODO: increment difficulty score for this item
    pass


def log_correct(item: str) -> None:
    """Record a correct answer — reduces difficulty score over time."""
    # TODO: decay difficulty score for this item
    pass


def get_weak_items(n: int = 5) -> list[str]:
    """Return the N items with the highest difficulty scores."""
    # TODO: sort mistakes by score, return top N
    return []


def build_srs_context() -> str:
    """
    Build a short summary of current weak points for injection
    into AI prompts. e.g. 'Player struggles with: Dativ case, Perfekt tense.'
    """
    weak = get_weak_items(5)
    if not weak:
        return ""
    return "Der Spieler hat Schwierigkeiten mit: " + ", ".join(weak) + "."
