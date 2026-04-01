"""
engine/game_state.py
====================
Defines the full save state model using Pydantic.
All game data lives here — this is the single source of truth.
Saved to / loaded from save/save_state.json.
"""

import json
import os
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field

SAVE_PATH = os.path.join(os.path.dirname(__file__), "..", "save", "save_state.json")


class Skills(BaseModel):
    vocabulary: int = 0
    grammar: int = 0
    writing: int = 0


class GameState(BaseModel):
    # Identity
    player_name: str = ""

    # Progression
    level: int = 1
    xp: int = 0
    xp_to_next: int = 100

    # Resources
    mana: int = 100
    mana_max: int = 100
    gold: int = 0

    # Stats
    streak: int = 0
    last_played: Optional[str] = None   # ISO date string e.g. "2026-03-29"
    accuracy_total: int = 0             # cumulative correct answers
    accuracy_attempts: int = 0          # cumulative attempts

    # Revelation Stone (hint) tracking — resets each chapter
    chapter_hints_used: int = 0
    hints_per_chapter: int = 3        # max free hints per chapter

    # Gambling dice state — active means next correct answer gets 2x XP
    dice_active: bool = False
    cefr_preference: str = "B2"   # A1 | A2 | B1 | B2 | C1
    episode: int = 1
    act: int = 1
    chapter: int = 1
    challenge_index: int = 0             # saves position within chapter on refresh
    episode_1_ending: Optional[str] = None   # "rache" | "vergebung" | None

    # Skills
    skills: Skills = Field(default_factory=Skills)

    # Inventory — list of item name strings
    inventory: list[str] = Field(default_factory=list)

    @property
    def accuracy_pct(self) -> int:
        if self.accuracy_attempts == 0:
            return 0
        return round((self.accuracy_total / self.accuracy_attempts) * 100)


def load_state() -> Optional[GameState]:
    """Load save state from disk. Returns None if no save file exists."""
    if not os.path.exists(SAVE_PATH):
        return None
    with open(SAVE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return GameState(**data)


def save_state(state: GameState) -> None:
    """Persist save state to disk."""
    os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(state.model_dump(), f, indent=2, ensure_ascii=False)


def create_new_state() -> GameState:
    """
    Called on first launch. Prompts the player for their name,
    then creates and saves a fresh state.
    """
    # TODO: in Phase 1 this will be called from terminal_ui.py
    # which handles the styled name prompt.
    # For now, a simple fallback:
    name = input('Wie lautet dein Name, Krieger? > ').strip()
    if not name:
        name = "Grimnir"
    state = GameState(player_name=name, last_played=str(date.today()))
    save_state(state)
    return state