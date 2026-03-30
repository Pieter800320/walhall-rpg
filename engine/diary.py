"""
engine/diary.py
================
Manages Grimnir's Diary — a living record of the journey.
Entries are generated on demand by the AI and cached in save/diary.json.
Each entry is tied to a chapter and used for Leseverstehen challenges.
"""

import json
import os

DIARY_PATH = os.path.join(os.path.dirname(__file__), "..", "save", "diary.json")


def load_diary() -> dict:
    """Load all diary entries. Returns empty dict if none yet."""
    if not os.path.exists(DIARY_PATH):
        return {}
    with open(DIARY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_diary(diary: dict) -> None:
    """Persist diary to disk."""
    os.makedirs(os.path.dirname(DIARY_PATH), exist_ok=True)
    with open(DIARY_PATH, "w", encoding="utf-8") as f:
        json.dump(diary, f, indent=2, ensure_ascii=False)


def get_entry(episode: int, act: int, chapter: int) -> str | None:
    """Return a cached diary entry for this chapter, or None if not yet written."""
    diary = load_diary()
    key = f"ep{episode}_act{act}_ch{chapter}"
    return diary.get(key)


def store_entry(episode: int, act: int, chapter: int, text: str) -> None:
    """Cache a generated diary entry."""
    diary = load_diary()
    key = f"ep{episode}_act{act}_ch{chapter}"
    diary[key] = text
    save_diary(diary)


def get_all_entries_text(episode: int) -> str:
    """
    Return all diary entries for an episode as a single readable string.
    Used for /diary command to show the full journal.
    """
    diary = load_diary()
    lines = []
    for key, text in diary.items():
        if key.startswith(f"ep{episode}_"):
            lines.append(text)
    return "\n\n---\n\n".join(lines) if lines else "Das Tagebuch ist noch leer."