"""
ui/terminal_ui.py
==================
The main terminal interface using the `rich` library.
Renders the 4-panel dashboard and handles all player input.
"""

import json
import os
import time
from datetime import date

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.rule import Rule

from engine.game_state import GameState, save_state
from engine.xp_engine import get_cefr_level, award_xp, calculate_answer_xp
from engine.mana_engine import spend_mana, can_afford, regen_mana
from engine.item_engine import get_active_multiplier
from engine.srs_engine import log_mistake, log_correct
from ai.evaluator import evaluate_answer, get_hint
from ai.narrator import narrate_chapter, explain_grammar

console = Console()

# ── Colour constants ──────────────────────────────────────────────
GOLD   = "yellow"
PURPLE = "magenta"
BLUE   = "cyan"
RED    = "red"
GREEN  = "green"
GREY   = "bright_black"

STORY_DIR = os.path.join(os.path.dirname(__file__), "..", "story")


# ── Renderers ─────────────────────────────────────────────────────

def render_top_bar(state: GameState) -> Panel:
    cefr = get_cefr_level(state.level)
    text = Text()
    text.append(f"⚔  {state.player_name}", style=f"bold {GOLD}")
    text.append(f"  │  Lvl {state.level} ({cefr})", style=BLUE)
    text.append(f"  │  Akt {state.act} · Kap {state.chapter}", style=GREY)
    text.append(f"  │  💠 {state.mana}/{state.mana_max}", style=PURPLE)
    text.append(f"  │  🪙 {state.gold}", style=GOLD)
    text.append(f"  │  🔥 {state.streak}d", style=RED)
    return Panel(text, style="on grey11", padding=(0, 1))


def render_stats(state: GameState) -> None:
    xp_pct  = int((state.xp / max(state.xp_to_next, 1)) * 30)
    xp_bar  = "█" * xp_pct + "░" * (30 - xp_pct)
    console.print(f"  XP  [{xp_bar}] {state.xp}/{state.xp_to_next}", style=GOLD)

    for label, val in [("Wortschatz", state.skills.vocabulary),
                       ("Grammatik ", state.skills.grammar),
                       ("Schreiben ", state.skills.writing)]:
        filled = int(val / 5)
        bar = "█" * filled + "░" * (20 - filled)
        console.print(f"  {label} [{bar}]", style=BLUE)

    console.print(f"  Genauigkeit: {state.accuracy_pct}%  │  Inventar: {', '.join(state.inventory) or '(leer)'}", style=GREY)


def render_command_bar() -> None:
    console.print(
        "  [magenta]/hint[/] ·10  [magenta]/translate[/] ·15  "
        "[magenta]/erkläre[/] ·20  [magenta]/wiederholen[/] ·5  "
        "[magenta]/quit[/]",
        style=GREY
    )


# ── Name screen ───────────────────────────────────────────────────

def show_name_screen() -> str:
    console.clear()
    console.print()
    console.print("  ╔══════════════════════════════════════════╗", style=GOLD)
    console.print("  ║     DER SCHATTEN VON WALHALL             ║", style=f"bold {GOLD}")
    console.print("  ║     Ein deutsches Lern-Rollenspiel       ║", style=GREY)
    console.print("  ╚══════════════════════════════════════════╝", style=GOLD)
    console.print()
    console.print('  "Wie lautet dein Name, Krieger?"', style=f"italic {PURPLE}")
    console.print()
    name = Prompt.ask("  Dein Name")
    return name.strip() or "Grimnir"


# ── Challenge loop ────────────────────────────────────────────────

def run_challenge(state: GameState, challenge: dict) -> bool:
    """
    Display one challenge, handle player input and commands.
    Returns True if the player answered correctly.
    """
    prompt_text = challenge.get("prompt_en", challenge.get("prompt_de", ""))
    grammar_focus = challenge.get("grammar_focus", "")
    start_time = time.time()
    last_result = None

    while True:
        # ── Draw screen ──
        console.clear()
        console.print(render_top_bar(state))
        console.print()
        render_stats(state)
        console.print()
        console.print(Rule(style=GOLD))

        # Show last result if any
        if last_result is not None:
            if last_result["correct"]:
                console.print(f"  [bold green]✔ Richtig![/]  {last_result['explanation']}")
            else:
                console.print(f"  [bold red]✖ Falsch.[/]  {last_result['explanation']}")
            console.print()

        # Challenge prompt
        console.print(Panel(prompt_text, title="[bold magenta]Herausforderung[/]",
                            border_style=PURPLE, padding=(1, 2)))
        console.print()
        render_command_bar()
        console.print()

        # ── Get input ──
        try:
            raw = Prompt.ask(f"  [bold yellow]{state.player_name}[/]")
        except (KeyboardInterrupt, EOFError):
            break

        inp = raw.strip()

        # ── Commands ──
        if inp == "/quit":
            console.print("  Auf Wiedersehen!", style=GREY)
            raise SystemExit

        if inp == "/wiederholen":
            if spend_mana(state, "/wiederholen"):
                last_result = None
                continue
            else:
                console.print("  [red]Nicht genug Mana.[/]")
                time.sleep(1)
                continue

        if inp == "/hint":
            if spend_mana(state, "/hint"):
                console.print()
                console.print("  [magenta]Brunhilde flüstert:[/]", style=PURPLE)
                hint = get_hint(state.player_name, prompt_text)
                console.print(Panel(hint, border_style=PURPLE, padding=(0, 2)))
                Prompt.ask("  [Weiter — Enter drücken]")
            else:
                console.print("  [red]Nicht genug Mana für /hint (10 benötigt).[/]")
                time.sleep(1)
            continue

        if inp == "/translate":
            if spend_mana(state, "/translate"):
                de = challenge.get("prompt_de", "Keine deutsche Version verfügbar.")
                console.print(Panel(de, title="Übersetzung", border_style=BLUE, padding=(0, 2)))
                Prompt.ask("  [Weiter — Enter drücken]")
            else:
                console.print("  [red]Nicht genug Mana für /translate (15 benötigt).[/]")
                time.sleep(1)
            continue

        if inp == "/erkläre":
            if spend_mana(state, "/erkläre"):
                example = challenge.get("correct_de", challenge.get("example_answer", ""))
                console.print()
                console.print("  [magenta]Brunhilde erklärt:[/]")
                explanation = explain_grammar(state.player_name, grammar_focus, example)
                console.print(Panel(explanation, border_style=PURPLE, padding=(1, 2)))
                Prompt.ask("  [Weiter — Enter drücken]")
            else:
                console.print("  [red]Nicht genug Mana für /erkläre (20 benötigt).[/]")
                time.sleep(1)
            continue

        if not inp:
            continue

        # ── Evaluate answer ──
        elapsed  = time.time() - start_time
        fast     = elapsed < 20.0

        console.print("  [grey50]Brunhilde bewertet deine Antwort...[/]")
        result = evaluate_answer(state.player_name, prompt_text, inp)
        last_result = result

        # Update accuracy stats
        state.accuracy_attempts += 1

        if result["correct"]:
            state.accuracy_total += 1
            state.streak = getattr(state, "_answer_streak", 0) + 1
            state._answer_streak = state.streak

            # XP
            multiplier = get_active_multiplier(state)
            xp = calculate_answer_xp(True, fast, state.streak, multiplier)
            xp_result = award_xp(state, xp)

            # SRS
            if grammar_focus:
                log_correct(grammar_focus)

            # Show result then break
            console.clear()
            console.print(render_top_bar(state))
            console.print()
            console.print(f"  [bold green]✔ Richtig![/]  +{xp} XP", style=GREEN)
            if fast:
                console.print("  [yellow]⚡ Schnelle Antwort! +5 Bonus[/]")
            if xp_result["levelled_up"]:
                console.print(f"\n  [bold yellow]🎉 LEVEL UP! Du bist jetzt Level {xp_result['new_level']}![/]")
            console.print(f"\n  {result['explanation']}", style=GREY)
            Prompt.ask("\n  [Weiter — Enter drücken]")
            save_state(state)
            return True

        else:
            state._answer_streak = 0
            if grammar_focus:
                log_mistake(grammar_focus)
            save_state(state)
            # Loop continues so player can try again


# ── Chapter runner ────────────────────────────────────────────────

def run_chapter(state: GameState, chapter_data: dict) -> None:
    """Narrate chapter opening, run all challenges, award completion XP."""

    # Narration
    console.clear()
    console.print(render_top_bar(state))
    console.print()
    console.print(Panel(
        f"[bold]{chapter_data['title']}[/]",
        title=f"[cyan]Kapitel {chapter_data['chapter']}[/]",
        border_style=BLUE, padding=(0, 2)
    ))
    console.print()
    console.print("  [grey50]Brunhilde bereitet die Geschichte vor...[/]")

    narration = narrate_chapter(state.player_name, chapter_data)
    console.print()
    console.print(Panel(narration, border_style=BLUE, padding=(1, 2)))
    Prompt.ask("\n  [Weiter — Enter drücken]")

    # Challenges
    challenges = chapter_data.get("challenges", [])
    for i, challenge in enumerate(challenges):
        correct = run_challenge(state, challenge)
        if correct:
            # Item reward
            item = challenge.get("item_reward")
            if item and item not in state.inventory:
                state.inventory.append(item)
                console.print(f"\n  [yellow]🗡️  Neuer Gegenstand: {item}![/]")
                Prompt.ask("  [Weiter — Enter drücken]")

    # Completion XP
    completion_xp = chapter_data.get("completion_xp", 50)
    xp_result = award_xp(state, completion_xp)
    state.chapter = chapter_data.get("unlocks_chapter", state.chapter + 1) or state.chapter
    save_state(state)

    console.clear()
    console.print(render_top_bar(state))
    console.print()
    console.print(f"  [bold green]✔ Kapitel abgeschlossen![/]  +{completion_xp} XP", style=GREEN)
    if xp_result["levelled_up"]:
        console.print(f"  [bold yellow]🎉 LEVEL UP! Level {xp_result['new_level']}![/]")
    Prompt.ask("\n  [Weiter — Enter drücken]")


# ── Story loader ──────────────────────────────────────────────────

def load_chapter(episode: int, act: int, chapter: int) -> dict | None:
    """Load chapter data from the correct story JSON file."""
    path = os.path.join(STORY_DIR, f"ep{episode}_act{act}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for ch in data.get("chapters", []):
        if ch["chapter"] == chapter:
            return ch
    return None


# ── Main game loop ────────────────────────────────────────────────

def run_game(state: GameState) -> None:
    """Main entry point. Handles name screen, mana regen, chapter loop."""

    # First launch
    if not state.player_name:
        state.player_name = show_name_screen()
        save_state(state)

    # Daily streak
    today = str(date.today())
    if state.last_played != today:
        state.streak += 1
        state.last_played = today
        save_state(state)

    # Mana regen since last session
    regen_mana(state)

    # Welcome screen
    console.clear()
    console.print(render_top_bar(state))
    console.print()
    console.print(f"  Willkommen zurück, [bold yellow]{state.player_name}[/].", style=GREY)
    console.print(f"  Akt {state.act} · Kapitel {state.chapter}", style=GREY)
    console.print()
    render_command_bar()
    Prompt.ask("\n  [Spiel beginnen — Enter drücken]")

    # Chapter loop
    while True:
        chapter_data = load_chapter(state.episode, state.act, state.chapter)
        if chapter_data is None:
            console.print("\n  [bold yellow]Ende dieses Aktes. Fortsetzung folgt![/]")
            break
        run_chapter(state, chapter_data)
