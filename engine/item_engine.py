"""
engine/item_engine.py
======================
Defines all items and their passive/active effects.
Items modify XP multipliers, mana regen, and speed bonuses.
"""

from engine.game_state import GameState

# Full item catalogue
ITEMS = {
    "Schwert": {
        "type": "weapon",
        "description": "Ein treues Schwert. Erhöht XP für korrekte Antworten.",
        "effect": {"xp_multiplier": 1.2},
    },
    "Stab": {
        "type": "weapon",
        "description": "Ein magischer Stab. Erhöht Manaregeneration.",
        "effect": {"mana_regen_bonus": 2},
    },
    "Bogen": {
        "type": "weapon",
        "description": "Ein schneller Bogen. Bonus-XP für schnelle Antworten.",
        "effect": {"fast_xp_bonus": 10},
    },
    "Grammatikrolle": {
        "type": "scroll",
        "description": "Einmalige Verwendung: vollständige Grammatikerklärung.",
        "effect": {"one_time": "grammar_explanation"},
    },
    "Runenstein": {
        "type": "artifact",
        "description": "Passiv: +5% XP auf alle Antworten.",
        "effect": {"xp_multiplier": 1.05},
    },
    "Wotan's Auge": {
        "type": "artifact",
        "description": "Passiv: unbekannte Wörter im Storymodus werden hervorgehoben.",
        "effect": {"highlight_words": True},
    },
    "Dämmerklinge": {
        "type": "weapon",
        "description": "Leuchtet, wenn eine Antwort korrekt ist.",
        "effect": {"visual_correct_pulse": True, "xp_multiplier": 1.15},
    },
}


def get_active_multiplier(state: GameState) -> float:
    """Calculate combined XP multiplier from all equipped items."""
    # TODO: multiply all xp_multiplier effects from inventory items
    return 1.0


def get_mana_regen_bonus(state: GameState) -> int:
    """Sum of mana regen bonuses from all inventory items."""
    # TODO: sum mana_regen_bonus effects from inventory items
    return 0


def add_item(state: GameState, item_name: str) -> bool:
    """Add an item to inventory if it exists. Returns True on success."""
    if item_name not in ITEMS:
        return False
    if item_name not in state.inventory:
        state.inventory.append(item_name)
    return True
