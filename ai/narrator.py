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


def narrate_epilogue(player_name: str, ending: str, stats: dict) -> str:
    """
    Generate the personalised episode epilogue using Sonnet.
    Called once when chapter 9 completes.
    ending: "rache" | "vergebung"
    """
    from ai.prompts import epilogue_prompt
    prompt = epilogue_prompt(player_name, ending, stats)

    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        import re
        text = response.content[0].text.strip()
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'^#{1,3}\s.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^>\s.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text
    except Exception as e:
        return f"[Epilogue unavailable: {str(e)}]"


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
        import re
        text = response.content[0].text.strip()
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'^#{1,3}\s.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^>\s.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text
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