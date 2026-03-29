"""
ui/terminal_ui.py
==================
The main terminal interface using the `rich` library.
Renders the 4-panel dashboard and handles all player input.
"""

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.text import Text
from rich.prompt import Prompt
from rich import box

from engine.game_state import GameState, save_state
from engine.xp_engine import get_cefr_level
from engine.mana_engine import spend_mana, can_afford
from ai.evaluator import evaluate_answer, get_hint
from ai.narrator import narrate_chapter

console = Console()


# ── Colour constants ──────────────────────────────────────────────
GOLD   = "yellow"
PURPLE = "magenta"
BLUE   = "cyan"
RED    = "red"
GREEN  = "green"
GREY   = "bright_black"


def render_top_bar(state: GameState) -> Panel:
    """Top bar: name, level, CEFR, location, mana, gold."""
    cefr = get_cefr_level(state.level)
    text = Text()
    text.append(f"⚔  {state.player_name}", style=f"bold {GOLD}")
    text.append(f"  │  Lvl {state.level} ({cefr})", style=BLUE)
    text.append(f"  │  Nebelwald · Akt {state.act}", style=GREY)
    text.append(f"  │  💠 {state.mana}/{state.mana_max} Mana", style=PURPLE)
    text.append(f"  │  🪙 {state.gold} Gold", style=GOLD)
    text.append(f"  │  🔥 {state.streak} Tage", style=RED)
    return Panel(text, style="on grey11", padding=(0, 1))


def render_stats_panel(state: GameState) -> Panel:
    """Left panel: XP bar, skill bars, accuracy."""
    lines = []

    # XP bar
    xp_pct = int((state.xp / max(state.xp_to_next, 1)) * 20)
    xp_bar = "█" * xp_pct + "░" * (20 - xp_pct)
    lines.append(Text(f"XP  [{xp_bar}]", style=GOLD))
    lines.append(Text(f"    {state.xp} / {state.xp_to_next}", style=GREY))
    lines.append(Text(""))

    # Skill bars
    for skill_name, val in [
        ("Wortschatz", state.skills.vocabulary),
        ("Grammatik ", state.skills.grammar),
        ("Schreiben ", state.skills.writing),
    ]:
        filled = int(val / 5)  # max skill ~100, bar width 20
        bar = "█" * filled + "░" * (20 - filled)
        lines.append(Text(f"{skill_name} [{bar}]", style=BLUE))

    lines.append(Text(""))
    lines.append(Text(f"Genauigkeit: {state.accuracy_pct}%", style=GREEN))

    # Inventory summary
    lines.append(Text(""))
    lines.append(Text("Inventar:", style=f"bold {GOLD}"))
    if state.inventory:
        for item in state.inventory:
            lines.append(Text(f"  · {item}", style=GREY))
    else:
        lines.append(Text("  (leer)", style=GREY))

    content = Text("\n").join(lines)
    return Panel(content, title="[bold yellow]Stats[/]", border_style=GOLD, padding=(1, 1))


def render_main_panel(content: str, mode: str = "story") -> Panel:
    """Centre panel: story text, challenge prompt, or combat view."""
    title_map = {
        "story":   "[bold cyan]Geschichte[/]",
        "challenge": "[bold magenta]Herausforderung[/]",
        "combat":  "[bold red]Kampf[/]",
        "result":  "[bold green]Ergebnis[/]",
    }
    return Panel(
        content,
        title=title_map.get(mode, ""),
        border_style=BLUE,
        padding=(1, 2),
    )


def render_command_panel() -> Panel:
    """Bottom right: quick command reference."""
    text = Text()
    text.append("/hint", style=f"bold {PURPLE}");  text.append(" · 10 Mana   ", style=GREY)
    text.append("/translate", style=f"bold {PURPLE}"); text.append(" · 15 Mana   ", style=GREY)
    text.append("/erkläre", style=f"bold {PURPLE}");  text.append(" · 20 Mana   ", style=GREY)
    text.append("/wiederholen", style=f"bold {PURPLE}"); text.append(" · 5 Mana", style=GREY)
    return Panel(text, title="[bold]Befehle[/]", border_style=GREY, padding=(0, 1))


def show_name_screen() -> str:
    """Styled first-launch name prompt."""
    console.clear()
    console.print()
    console.print("  ╔══════════════════════════════════════════╗", style=GOLD)
    console.print("  ║     DER SCHATTEN VON WALHALL             ║", style=f"bold {GOLD}")
    console.print("  ║     Ein deutsches Lern-Rollenspiel       ║", style=GREY)
    console.print("  ╚══════════════════════════════════════════╝", style=GOLD)
    console.print()
    console.print("  Die Dorfälteste tritt vor dich und spricht:", style=GREY)
    console.print()
    console.print('  "Wie lautet dein Name, Krieger?"', style=f"italic {PURPLE}")
    console.print()
    name = Prompt.ask("  Dein Name")
    return name.strip() or "Grimnir"


def run_challenge(state: GameState, challenge: dict) -> bool:
    """
    Run a single challenge from a chapter's challenge list.
    Returns True if answered correctly.
    TODO: implement full challenge loop with command handling.
    """
    pass


def run_chapter(state: GameState, chapter_data: dict) -> None:
    """
    Run a full chapter: narration → challenges → completion XP.
    TODO: implement chapter flow using run_challenge().
    """
    pass


def run_game(state: GameState) -> None:
    """
    Main game loop. Called from main.py.
    Handles name screen on first launch, then chapter progression.
    TODO: implement full game loop.
    """
    # First launch — get name
    if not state.player_name:
        state.player_name = show_name_screen()
        save_state(state)

    console.clear()
    console.print(render_top_bar(state))
    console.print()
    console.print(f"  Willkommen zurück, [bold yellow]{state.player_name}[/].", style=GREY)
    console.print("  [Spielschleife wird in Phase 1 implementiert]", style=GREY)
    console.print()
    console.print(render_command_panel())
