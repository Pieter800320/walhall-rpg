"""
engine/srs_engine.py
=====================
Spaced Repetition System — tracks per-word and per-grammar-rule
difficulty scores. Resurfaces weak items into quests naturally.
Data is persisted to save/mistakes.json.

Score logic:
  - Each mistake adds +3 to the item's score
  - Each correct answer subtracts -1 (minimum 0)
  - Items with score >= 3 are considered "weak"
  - build_srs_context() injects the top 5 into every AI prompt
"""

import json
import os
from datetime import datetime, timezone

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
    Record a mistake. Increments difficulty score by 3.
    item: grammar rule or vocab item e.g. "Dativ case"
    """
    if not item:
        return
    mistakes = load_mistakes()
    if item not in mistakes:
        mistakes[item] = {
            "score": 0,
            "category": category,
            "last_seen": None,
            "attempts": 0,
            "errors": 0,
        }
    mistakes[item]["score"] = mistakes[item]["score"] + 3
    mistakes[item]["attempts"] = mistakes[item]["attempts"] + 1
    mistakes[item]["errors"] = mistakes[item]["errors"] + 1
    mistakes[item]["last_seen"] = datetime.now(timezone.utc).isoformat()
    save_mistakes(mistakes)


def log_correct(item: str) -> None:
    """
    Record a correct answer. Decays difficulty score by 1 (min 0).
    """
    if not item:
        return
    mistakes = load_mistakes()
    if item not in mistakes:
        return  # Never seen before — nothing to decay
    mistakes[item]["score"] = max(0, mistakes[item]["score"] - 1)
    mistakes[item]["attempts"] = mistakes[item]["attempts"] + 1
    mistakes[item]["last_seen"] = datetime.now(timezone.utc).isoformat()
    save_mistakes(mistakes)


def get_weak_items(n: int = 5) -> list[str]:
    """Return the N items with the highest difficulty scores (score >= 3)."""
    mistakes = load_mistakes()
    weak = {k: v for k, v in mistakes.items() if v["score"] >= 3}
    sorted_items = sorted(weak.items(), key=lambda x: x[1]["score"], reverse=True)
    return [item for item, _ in sorted_items[:n]]


def get_all_stats() -> list[dict]:
    """Return full mistake stats for all tracked items, sorted by score."""
    mistakes = load_mistakes()
    stats = []
    for item, data in mistakes.items():
        stats.append({
            "item": item,
            "score": data["score"],
            "category": data["category"],
            "attempts": data["attempts"],
            "errors": data["errors"],
            "accuracy": round((1 - data["errors"] / max(data["attempts"], 1)) * 100),
        })
    return sorted(stats, key=lambda x: x["score"], reverse=True)


def build_srs_context() -> str:
    """
    Build a short summary of current weak points for injection
    into AI prompts e.g. 'Player struggles with: Dativ case, Perfekt tense.'
    Returns empty string if no weak items yet.
    """
    weak = get_weak_items(5)
    if not weak:
        return ""
    return "The player currently struggles with: " + ", ".join(weak) + ". Weave these into the challenge where natural."