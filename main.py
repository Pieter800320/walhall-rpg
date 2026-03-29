"""
Der Schatten von Walhall
========================
Main entry point. Boots the game, loads or creates a save state,
then hands control to the terminal UI.
"""

from dotenv import load_dotenv
load_dotenv()

from engine.game_state import load_state, create_new_state
from ui.terminal_ui import run_game


def main():
    # Try to load existing save; if none exists, start fresh
    state = load_state()
    if state is None:
        state = create_new_state()

    run_game(state)


if __name__ == "__main__":
    main()
