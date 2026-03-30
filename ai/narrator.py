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
HAIKU_MODEL  = "claude-haiku-4-5-20251001"


def generate_diary_entry(player_name: str, chapter_data: dict, cefr: str = "B2") -> str:
    """
    Generate and return a diary entry for the given chapter using Sonnet.
    Caller is responsible for caching via diary.py.
    """
    from ai.prompts import diary_entry_prompt
    prompt = diary_entry_prompt(player_name, chapter_data, cefr)
    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        import re
        text = response.content[0].text.strip()
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'^#{1,3}\s.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text
    except Exception as e:
        return f"[Diary entry unavailable: {str(e)}]"


def evaluate_leseverstehen(player_name: str, diary_entry: str,
                            question: str, player_answer: str, cefr: str = "B2") -> dict:
    """
    Use Haiku to evaluate a reading comprehension answer.
    Returns: { correct: bool, explanation: str, grammar_focus: str }
    """
    from ai.prompts import leseverstehen_prompt
    import json as _json
    prompt = leseverstehen_prompt(player_name, diary_entry, question, player_answer, cefr)
    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = _json.loads(raw.strip())
        return {
            "correct":       bool(result.get("correct", False)),
            "explanation":   result.get("explanation", ""),
            "grammar_focus": "reading comprehension",
        }
    except Exception as e:
        return {"correct": False, "explanation": f"Evaluation error: {str(e)}", "grammar_focus": "reading comprehension"}


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


def narrate_chapter(player_name: str, chapter_data: dict, cefr: str = "B2") -> str:
    """Generate immersive chapter opening text using Sonnet."""
    srs = build_srs_context()
    prompt = narrator_prompt(player_name, chapter_data, srs, cefr)

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