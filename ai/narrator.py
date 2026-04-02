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


def evaluate_langtext(player_name: str, scenario: str, player_text: str,
                      min_words: int, cefr: str = "B2") -> dict:
    """
    Evaluate a long-form German writing challenge using Sonnet.
    Returns full assessment dict.
    """
    from ai.prompts import langtext_prompt
    import json as _json
    prompt = langtext_prompt(player_name, scenario, player_text, min_words, cefr)
    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = _json.loads(raw.strip())
        return {
            "correct":          bool(result.get("correct", False)),
            "word_count":       result.get("word_count", len(player_text.split())),
            "grammar_score":    result.get("grammar_score", 0),
            "vocabulary_score": result.get("vocabulary_score", 0),
            "coherence_score":  result.get("coherence_score", 0),
            "task_score":       result.get("task_score", 0),
            "overall_feedback": result.get("overall_feedback", ""),
            "best_sentence":    result.get("best_sentence", ""),
            "correction":       result.get("correction", ""),
        }
    except Exception as e:
        return {
            "correct": False, "word_count": len(player_text.split()),
            "grammar_score": 0, "vocabulary_score": 0,
            "coherence_score": 0, "task_score": 0,
            "overall_feedback": f"Evaluation error: {str(e)}",
            "best_sentence": "", "correction": "",
        }


def generate_flashcards(chapter_data: dict, cefr: str = "B2",
                        seen_words: list = None) -> list:
    """
    Generate 5 vocabulary flashcards for the current chapter using Haiku.
    Returns list of { german, english, example } dicts.
    """
    from ai.prompts import runentafel_generate_prompt
    import json as _json
    prompt = runentafel_generate_prompt(chapter_data, cefr, seen_words or [])
    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return _json.loads(raw.strip())
    except Exception as e:
        return [{"german": "der Fehler", "english": "the error",
                 "example": f"Ein Fehler ist aufgetreten: {str(e)}"}]


def evaluate_flashcard(german: str, english: str,
                       player_answer: str, cefr: str = "B2") -> dict:
    """
    Evaluate a single flashcard answer using Haiku.
    Returns { correct: bool, feedback: str }
    """
    from ai.prompts import runentafel_evaluate_prompt
    import json as _json
    prompt = runentafel_evaluate_prompt(german, english, player_answer, cefr)
    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = _json.loads(raw.strip())
        return {
            "correct":  bool(result.get("correct", False)),
            "feedback": result.get("feedback", ""),
        }
    except Exception as e:
        return {"correct": False, "feedback": f"Evaluation error: {str(e)}"}


def elder_scroll_lookup(word: str, cefr: str = "B2") -> str:
    """
    Look up a German word using Haiku. Returns a German-language definition.
    """
    from ai.prompts import elder_scroll_prompt
    prompt = elder_scroll_prompt(word, cefr)
    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Die Schriftrolle schweigt. ({str(e)})"


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
    """Generate personalised episode epilogue with retry logic."""
    import time
    from ai.prompts import epilogue_prompt
    prompt = epilogue_prompt(player_name, ending, stats)

    for attempt in range(3):
        try:
            model = SONNET_MODEL if attempt < 2 else HAIKU_MODEL
            response = client.messages.create(
                model=model,
                max_tokens=600,
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
            if "overloaded" in str(e).lower() and attempt < 2:
                time.sleep(3)
                continue
            return "[Epilog nicht verfügbar — bitte neu laden.]"
    return "[Epilog nicht verfügbar.]"


def narrate_chapter(player_name: str, chapter_data: dict, cefr: str = "B2") -> str:
    """Generate immersive chapter opening text. Falls back to Haiku if Sonnet overloaded."""
    import time
    srs = build_srs_context()
    prompt = narrator_prompt(player_name, chapter_data, srs, cefr)

    for attempt in range(3):
        try:
            model = SONNET_MODEL if attempt < 2 else HAIKU_MODEL
            response = client.messages.create(
                model=model,
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
            err = str(e)
            if "overloaded" in err.lower() and attempt < 2:
                time.sleep(3)
                continue
            if attempt == 2:
                return f"[{player_name} betritt {chapter_data.get('title', 'das nächste Kapitel')}. Die Schatten warten...]"
    return "[Erzählung nicht verfügbar — bitte neu laden.]"


def explain_grammar(player_name: str, grammar_focus: str, example_sentence: str) -> str:
    """Full grammar explanation as Brunhilde, always in German."""
    prompt = f"""Grammatikregel: {grammar_focus}
Beispiel: {example_sentence}
Spieler: {player_name}

Erkläre die Regel in 3 kurzen Punkten auf Deutsch. Halte den Ton einer weisen Seherin."""
    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=400,
            system="Du bist Brunhilde, eine weise Waldseherin in einem deutschen Lernspiel. Antworte IMMER und AUSSCHLIESSLICH auf Deutsch. Niemals Englisch. Keine Markdown-Formatierung.",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Brunhilde schweigt. ({str(e)})"
