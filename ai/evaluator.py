"""
ai/evaluator.py
================
Uses Claude Haiku to evaluate player answers quickly and cheaply.
Returns a structured result the game engine can act on immediately.
"""

import os
import json
import anthropic
from ai.prompts import evaluator_prompt, hint_prompt
from engine.srs_engine import build_srs_context

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

HAIKU_MODEL = "claude-haiku-4-5-20251001"


def evaluate_answer(player_name: str, challenge: str, player_answer: str) -> dict:
    """
    Send answer to Haiku for evaluation.
    Returns: { correct: bool, explanation: str, grammar_focus: str }
    """
    srs = build_srs_context()
    prompt = evaluator_prompt(player_name, challenge, player_answer, srs)

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)

        # Ensure all expected keys exist
        return {
            "correct":       bool(result.get("correct", False)),
            "explanation":   result.get("explanation", ""),
            "grammar_focus": result.get("grammar_focus", ""),
        }

    except json.JSONDecodeError:
        # Haiku returned something we couldn't parse — fail safe
        return {
            "correct":       False,
            "explanation":   "Could not evaluate answer. Please try again.",
            "grammar_focus": "",
        }
    except Exception as e:
        return {
            "correct":       False,
            "explanation":   f"API error: {str(e)}",
            "grammar_focus": "",
        }


def get_hint(player_name: str, challenge: str) -> str:
    """
    Get a grammar hint from Haiku without revealing the answer.
    Returns hint text as a plain string.
    """
    srs = build_srs_context()
    prompt = hint_prompt(player_name, challenge, srs)

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Brunhilde schweigt. (API error: {str(e)})"
