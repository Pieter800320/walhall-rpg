"""
ai/narrator.py
===============
Uses Claude Sonnet for rich, mana-gated operations:
- Chapter opening narration
- Full grammar explanations (as Brunhilde)
- Adaptive quest generation
"""

import os
import anthropic
from ai.prompts import narrator_prompt, explanation_prompt
from engine.srs_engine import build_srs_context

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SONNET_MODEL = "claude-sonnet-4-6"


def narrate_chapter(player_name: str, chapter_data: dict) -> str:
    """
    Generate immersive chapter opening text using Sonnet.
    Called once per chapter transition (mana not required — story progression).
    Returns narration as a plain string.
    """
    srs = build_srs_context()
    prompt = narrator_prompt(player_name, chapter_data, srs)

    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"[Narration unavailable: {str(e)}]"


def explain_grammar(player_name: str, grammar_focus: str, example_sentence: str) -> str:
    """
    Full grammar explanation as Brunhilde. Mana-gated — only called
    after mana_engine confirms the player can afford /erkläre.
    Returns explanation as a plain string.
    """
    prompt = explanation_prompt(player_name, grammar_focus, example_sentence)

    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Brunhilde schweigt. ({str(e)})"
