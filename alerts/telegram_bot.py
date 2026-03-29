"""
alerts/telegram_bot.py
=======================
Sends Telegram notifications:
  - Daily streak reminder if player hasn't played today
  - Session summary after completing a play session
  - Level-up celebration
  - Item reward notification
"""

import os
import requests
from datetime import date
from engine.game_state import load_state

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(text: str) -> None:
    """Send a plain text message to the configured chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Credentials not set — skipping.")
        return
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    })


def send_streak_reminder() -> None:
    """
    Called by GitHub Actions daily cron.
    Sends a reminder only if the player hasn't played today.
    """
    state = load_state()
    if state is None:
        return  # No save file yet

    today = str(date.today())
    if state.last_played == today:
        return  # Already played — no reminder needed

    msg = (
        f"⚔️ <b>{state.player_name}</b>, Nebelhain braucht dich.\n\n"
        f"🔥 Streak: {state.streak} Tage\n"
        f"📖 Weiter bei: Akt {state.act}, Kapitel {state.chapter}\n\n"
        f"<i>Die Wälder werden dunkler ohne dich.</i>"
    )
    send_message(msg)


def send_session_summary(xp_gained: int, items_gained: list[str], levelled_up: bool) -> None:
    """Send a summary message after a completed play session."""
    state = load_state()
    if state is None:
        return

    lines = [f"✅ <b>{state.player_name}</b> — Sitzung abgeschlossen!\n"]
    lines.append(f"⭐ +{xp_gained} XP")
    lines.append(f"📊 Level {state.level} · {state.xp}/{state.xp_to_next} XP")
    lines.append(f"🔥 Streak: {state.streak} Tage")

    if levelled_up:
        lines.append(f"\n🎉 <b>LEVEL UP!</b> Du bist jetzt Level {state.level}!")

    if items_gained:
        lines.append(f"\n🗡️ Neue Gegenstände: {', '.join(items_gained)}")

    send_message("\n".join(lines))


def send_level_up(new_level: int, cefr: str) -> None:
    """Dedicated level-up celebration message."""
    state = load_state()
    if state is None:
        return

    msg = (
        f"🎉 <b>LEVEL UP!</b>\n\n"
        f"{state.player_name} erreicht Level {new_level} ({cefr})!\n\n"
        f"<i>Brunhilde nickt anerkennend.</i>"
    )
    send_message(msg)
