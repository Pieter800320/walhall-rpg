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
from ai.narrator import narrate_chapter, explain_grammar, narrate_epilogue, generate_diary_entry, evaluate_leseverstehen, elder_scroll_lookup
from engine.diary import get_entry, store_entry, get_all_entries_text

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


def render_command_bar(state: GameState = None) -> None:
    hints_left = ""
    if state:
        left = state.hints_per_chapter - state.chapter_hints_used
        hints_left = f" ({max(0,left)} übrig)"
    has_dice   = state and "Glückswürfel" in state.inventory
    has_scroll = state and "Ältere Schriftrolle" in state.inventory
    dice_cmd   = "  [magenta]/würfeln[/]" if has_dice else ""
    scroll_cmd = "  [magenta]/scroll[/]" if has_scroll else ""
    console.print(
        f"  [magenta]/stein[/]{hints_left}  [magenta]/translate[/] ·15  "
        f"[magenta]/erkläre[/] ·20  [magenta]/wiederholen[/] ·5  "
        f"[magenta]/diary[/]  [magenta]/level[/]{dice_cmd}{scroll_cmd}  [magenta]/quit[/]",
        style=GREY
    )


# ── Name screen ───────────────────────────────────────────────────

CEFR_OPTIONS = {
    "1": ("A1", "Absolute beginner — simple present tense, basic words"),
    "2": ("A2", "Elementary — past tense, common phrases"),
    "3": ("B1", "Intermediate — modal verbs, opinions, longer sentences"),
    "4": ("B2", "Upper-intermediate — complex grammar, arguments"),
    "5": ("C1", "Advanced — near-native, idiomatic, complex discourse"),
}


def show_level_screen(current: str = None) -> str:
    """Display CEFR level selection. Returns chosen level string e.g. 'B2'."""
    console.print()
    console.print(Rule(title="[bold yellow]Sprachniveau wählen[/]", style=GOLD))
    console.print()
    if current:
        console.print(f"  Aktuelles Niveau: [bold cyan]{current}[/]", style=GREY)
        console.print()
    for key, (level, desc) in CEFR_OPTIONS.items():
        console.print(f"  [bold yellow]{key}[/]  {level} — {desc}", style=GREY)
    console.print()
    choice = Prompt.ask("  Dein Niveau (1-5)", default="4")
    level, _ = CEFR_OPTIONS.get(choice, ("B2", ""))
    return level


def show_name_screen() -> tuple:
    """Styled first-launch name + level prompt. Returns (name, cefr)."""
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
    name = name.strip() or "Grimnir"
    cefr = show_level_screen()
    return name, cefr


# ── Challenge loop ────────────────────────────────────────────────

def run_challenge(state: GameState, challenge: dict) -> bool:
    """
    Display one challenge, handle player input and commands.
    Returns True if the player answered correctly.
    """
    prompt_text   = challenge.get("prompt_en", challenge.get("prompt_de", ""))
    grammar_focus = challenge.get("grammar_focus", "")
    challenge_type = challenge.get("type", "")
    options       = challenge.get("options", [])
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

        # Multiple choice options
        if challenge_type == "multiple_choice" and options:
            console.print()
            for i, opt in enumerate(options, 1):
                console.print(f"  [bold yellow]{i}[/]  {opt}", style=GREY)

        console.print()
        render_command_bar(state)
        console.print()

        # ── Get input ──
        try:
            raw = Prompt.ask(f"  [bold yellow]{state.player_name}[/]")
        except (KeyboardInterrupt, EOFError):
            break

        inp = raw.strip()

        # Resolve number input for multiple choice
        if challenge_type == "multiple_choice" and options and inp.isdigit():
            idx = int(inp) - 1
            if 0 <= idx < len(options):
                inp = options[idx]

        # ── Commands ──
        if inp == "/quit":
            console.print("  Auf Wiedersehen!", style=GREY)
            raise SystemExit

        if inp == "/level":
            state.cefr_preference = show_level_screen(state.cefr_preference)
            save_state(state)
            console.print(f"  [cyan]Niveau geändert zu {state.cefr_preference}.[/]")
            time.sleep(1)
            continue

        if inp == "/wiederholen":
            if spend_mana(state, "/wiederholen"):
                last_result = None
                continue
            else:
                console.print("  [red]Nicht genug Mana.[/]")
                time.sleep(1)
                continue

        if inp == "/stein":
            hints_left = state.hints_per_chapter - state.chapter_hints_used
            if hints_left <= 0:
                console.print("  [red]Der Offenbarungsstein ist erschöpft. Kein Hinweis mehr in diesem Kapitel.[/]")
                time.sleep(2)
                continue
            state.chapter_hints_used += 1
            save_state(state)
            console.print()
            console.print(f"  [magenta]✦ Offenbarungsstein leuchtet ({hints_left - 1} verbleibend):[/]", style=PURPLE)
            hint = get_hint(state.player_name, prompt_text, state.cefr_preference)
            console.print(Panel(hint, border_style=PURPLE, padding=(0, 2)))
            Prompt.ask("  [Weiter — Enter drücken]")
            continue

        if inp == "/würfeln":
            if "Glückswürfel" not in state.inventory:
                console.print("  [red]Du hast keine Glückswürfel.[/]")
                time.sleep(1)
                continue
            if state.dice_active:
                console.print("  [yellow]Die Würfel sind bereits aktiv![/]")
                time.sleep(1)
                continue
            import random
            # Weight success by accuracy — min 55%, max 85%
            accuracy = state.accuracy_pct / 100
            success_chance = 0.55 + (accuracy * 0.30)
            roll = random.random()
            console.print()
            console.print("  🎲 Du wirfst die Glückswürfel...", style=GOLD)
            time.sleep(1)
            if roll < success_chance:
                state.dice_active = True
                save_state(state)
                console.print("  [bold green]✦ Glück! Deine nächste korrekte Antwort bringt doppelte XP![/]")
            else:
                state.mana = max(0, state.mana - 15)
                save_state(state)
                console.print("  [bold red]✖ Pech! Die Würfel wenden sich gegen dich. -15 Mana.[/]")
            time.sleep(2)
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

        if inp == "/diary":
            entries = get_all_entries_text(state.episode)
            console.print()
            console.print(Panel(
                entries,
                title="[bold yellow]📖 Grimnirs Tagebuch[/]",
                border_style=GOLD, padding=(1, 2)
            ))
            Prompt.ask("  [Weiter — Enter drücken]")
            continue

        if inp.startswith("/scroll"):
            if "Ältere Schriftrolle" not in state.inventory:
                console.print("  [red]Du besitzt die Ältere Schriftrolle nicht.[/]")
                time.sleep(1)
                continue
            parts = inp.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                console.print("  [yellow]Verwendung: /scroll <deutsches Wort>[/]")
                time.sleep(1)
                continue
            word = parts[1].strip()
            console.print(f"\n  [yellow]✦ Die Ältere Schriftrolle öffnet sich...[/]")
            definition = elder_scroll_lookup(word, state.cefr_preference)
            console.print(Panel(
                definition,
                title=f"[bold yellow]📜 {word}[/]",
                border_style=GOLD, padding=(1, 2)
            ))
            Prompt.ask("  [Weiter — Enter drücken]")
            continue

        if not inp:
            continue

        # ── Leseverstehen challenge type ──────────────────────────
        if challenge_type == "leseverstehen":
            diary_entry = challenge.get("_diary_entry", "")
            question    = challenge.get("leseverstehen_question", "")
            console.print("  [grey50]Brunhilde bewertet deine Antwort...[/]")
            result = evaluate_leseverstehen(
                state.player_name, diary_entry, question, inp, state.cefr_preference
            )
        else:
            # ── Standard evaluate ─────────────────────────────────
            console.print("  [grey50]Brunhilde bewertet deine Antwort...[/]")
            result = evaluate_answer(state.player_name, prompt_text, inp, state.cefr_preference)

        last_result = result

        # Update accuracy stats
        state.accuracy_attempts += 1

        if result["correct"]:
            state.accuracy_total += 1
            state.streak = getattr(state, "_answer_streak", 0) + 1
            state._answer_streak = state.streak
            state._last_answer = inp

            # XP — apply dice multiplier if active
            multiplier = get_active_multiplier(state)
            if state.dice_active:
                multiplier *= 2.0
                state.dice_active = False
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
            if multiplier >= 2.0:
                console.print("  [bold yellow]🎲 Würfelbonus! Doppelte XP![/]")
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


def detect_ending_choice(answer: str) -> str:
    """
    Detect whether the player chose Rache or Vergebung from their free-text answer.
    Looks for keywords. Defaults to 'vergebung' if ambiguous.
    """
    answer_lower = answer.lower()
    rache_words    = ["rache", "zerstör", "vernicht", "enden", "töt", "gefährlich", "kann nicht", "darf nicht"]
    vergebung_words = ["vergeb", "befreie", "befreit", "heilen", "vergebung", "verstehe", "loslassen", "freiheit"]

    rache_score    = sum(1 for w in rache_words if w in answer_lower)
    vergebung_score = sum(1 for w in vergebung_words if w in answer_lower)

    return "rache" if rache_score > vergebung_score else "vergebung"


def show_epilogue(state: GameState) -> None:
    """Display the personalised episode epilogue and completion screen."""
    ending = state.episode_1_ending or "vergebung"

    console.clear()
    console.print(render_top_bar(state))
    console.print()
    console.print(Rule(title="[bold yellow]EPISODE I — ABGESCHLOSSEN[/]", style=GOLD))
    console.print()

    ending_label = "VERGEBUNG" if ending == "vergebung" else "RACHE"
    ending_color = GREEN if ending == "vergebung" else RED
    console.print(f"  Deine Wahl: [bold {ending_color}]{ending_label}[/]", style=GREY)
    console.print()
    console.print("  [grey50]Brunhilde schreibt deine Geschichte...[/]")

    stats = {
        "level":        state.level,
        "accuracy_pct": state.accuracy_pct,
        "streak":       state.streak,
        "inventory":    state.inventory,
    }
    epilogue_text = narrate_epilogue(state.player_name, ending, stats)

    console.print()
    console.print(Panel(epilogue_text, border_style=GOLD, padding=(1, 2)))
    console.print()

    # Stats summary
    console.print(Rule(style=GOLD))
    console.print(f"  [bold yellow]Abschlussbericht — {state.player_name}[/]")
    console.print(f"  Level {state.level}  ·  Genauigkeit {state.accuracy_pct}%  ·  Streak {state.streak} Tage", style=GREY)
    console.print(f"  Inventar: {', '.join(state.inventory) or '(leer)'}", style=GREY)
    console.print()

    seal = "🌿 VERGEBUNG" if ending == "vergebung" else "⚔️  RACHE"
    console.print(f"  [bold yellow]✦ EPISODE I COMPLETE · {seal} ✦[/]")
    console.print()
    Prompt.ask("  [Enter drücken um fortzufahren]")


# ── Chapter runner ────────────────────────────────────────────────

def run_chapter(state: GameState, chapter_data: dict) -> None:
    """Narrate chapter opening, run all challenges, award completion XP."""

    # Reset hint counter for this chapter
    state.chapter_hints_used = 0
    save_state(state)

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

    narration = narrate_chapter(state.player_name, chapter_data, state.cefr_preference)
    console.print()
    console.print(Panel(narration, border_style=BLUE, padding=(1, 2)))
    Prompt.ask("\n  [Weiter — Enter drücken]")

    # Generate diary entry for this chapter (cached after first run)
    ch_num = chapter_data.get("chapter", 0)
    diary_entry = get_entry(state.episode, state.act, ch_num)
    if diary_entry is None:
        diary_entry = generate_diary_entry(state.player_name, chapter_data, state.cefr_preference)
        store_entry(state.episode, state.act, ch_num, diary_entry)

    # Inject diary entry into any leseverstehen challenges
    challenges = chapter_data.get("challenges", [])
    for ch in challenges:
        if ch.get("type") == "leseverstehen":
            ch["_diary_entry"] = diary_entry
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

    # Detect ending choice after chapter 9
    if chapter_data.get("chapter") == 9:
        last_answer = getattr(state, "_last_answer", "")
        state.episode_1_ending = detect_ending_choice(last_answer)

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
        state.player_name, state.cefr_preference = show_name_screen()
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
    render_command_bar(state)
    Prompt.ask("\n  [Spiel beginnen — Enter drücken]")

    # Chapter loop
    while True:
        chapter_data = load_chapter(state.episode, state.act, state.chapter)
        if chapter_data is None:
            # Check if episode 1 just completed
            if state.episode == 1 and state.episode_1_ending is not None:
                show_epilogue(state)
            else:
                console.print("\n  [bold yellow]Ende dieses Aktes. Fortsetzung folgt![/]")
            break
        run_chapter(state, chapter_data)