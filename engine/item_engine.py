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
    """Calculate combined XP multiplier from all inventory items."""
    multiplier = 1.0
    for item_name in state.inventory:
        item = ITEMS.get(item_name)
        if item:
            multiplier *= item["effect"].get("xp_multiplier", 1.0)
    return round(multiplier, 4)


def get_mana_regen_bonus(state: GameState) -> int:
    """Sum of mana regen bonuses from all inventory items."""
    bonus = 0
    for item_name in state.inventory:
        item = ITEMS.get(item_name)
        if item:
            bonus += item["effect"].get("mana_regen_bonus", 0)
    return bonus


def get_fast_xp_bonus(state: GameState) -> int:
    """Extra XP awarded on fast answers from Bogen."""
    bonus = 0
    for item_name in state.inventory:
        item = ITEMS.get(item_name)
        if item:
            bonus += item["effect"].get("fast_xp_bonus", 0)
    return bonus


def has_word_highlight(state: GameState) -> bool:
    """Returns True if Wotan's Auge is in inventory."""
    return "Wotan's Auge" in state.inventory


def add_item(state: GameState, item_name: str) -> bool:
    """Add an item to inventory if it exists. Returns True on success."""
    if item_name not in ITEMS:
        return False
    if item_name not in state.inventory:
        state.inventory.append(item_name)
    return True


def describe_item(item_name: str) -> str:
    """Return the description of an item by name."""
    item = ITEMS.get(item_name)
    if not item:
        return "Unbekannter Gegenstand."
    return item["description"]