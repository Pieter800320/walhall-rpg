# Der Schatten von Walhall 🗡️

A German-learning RPG. The act of learning IS the gameplay.

## Structure

```
walhall-rpg/
├── engine/          # Core game logic (no AI, no UI)
├── ai/              # All Anthropic API calls
├── story/           # Episode content as JSON
├── save/            # Player save state
├── ui/              # Terminal dashboard (rich)
├── alerts/          # Telegram notifications
└── .github/         # GitHub Actions workflows
```

## Setup

1. Copy `.env.example` to `.env` and fill in your keys
2. `pip install -r requirements.txt`
3. `python main.py`

## Requirements

- Python 3.10+
- Anthropic API key (console.anthropic.com)
- Telegram bot token (for streak alerts)
