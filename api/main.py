"""
api/main.py
============
FastAPI backend for Der Schatten von Walhall.
Serves game state and proxies all AI calls for the React frontend.
The terminal version (main.py) runs independently alongside this.
"""

import os
import sys
from datetime import date

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from engine.game_state import load_state, save_state, create_new_state, GameState
from engine.xp_engine import award_xp, calculate_answer_xp, get_cefr_level
from engine.mana_engine import spend_mana, can_afford, regen_mana, MANA_COSTS
from engine.item_engine import get_active_multiplier
from engine.srs_engine import log_mistake, log_correct, build_srs_context
from engine.diary import get_entry, store_entry, get_all_entries_text
from engine.flashcard import mark_seen, mana_reward
from ai.evaluator import evaluate_answer, get_hint, evaluate_satzbau
from ai.narrator import (narrate_chapter, explain_grammar, narrate_epilogue,
                          generate_diary_entry, evaluate_leseverstehen,
                          elder_scroll_lookup, generate_flashcards,
                          evaluate_flashcard, evaluate_langtext)

import json

STORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "story")
SAVE_DIR  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "save")

def get_save_path(slot: str = "default") -> str:
    """Return the save file path for a given slot."""
    safe = "".join(c for c in slot if c.isalnum() or c in "_-")[:40] or "default"
    # Default slot uses the original filename for backward compatibility
    if safe == "default":
        return os.path.join(SAVE_DIR, "save_state.json")
    return os.path.join(SAVE_DIR, f"save_{safe}.json")

def load_state_slot(slot: str = "default"):
    path = get_save_path(slot)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return GameState(**data)

def save_state_slot(state: GameState, slot: str = "default") -> None:
    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(get_save_path(slot), "w", encoding="utf-8") as f:
        json.dump(state.model_dump(), f, indent=2, ensure_ascii=False)

app = FastAPI(title="Walhall RPG API", version="1.0")

# Ensure save directory exists on Railway
os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "save"), exist_ok=True)

# Allow React dev server and Railway frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helper ────────────────────────────────────────────────────────

def load_chapter_data(episode: int, act: int, chapter: int) -> dict | None:
    path = os.path.join(STORY_DIR, f"ep{episode}_act{act}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for ch in data.get("chapters", []):
        if ch["chapter"] == chapter:
            return ch
    return None


# ── Request models ────────────────────────────────────────────────

class NewGameRequest(BaseModel):
    player_name: str
    cefr_preference: str = "B2"
    slot: str = "default"

class AnswerRequest(BaseModel):
    challenge_id: str
    challenge_type: str
    prompt_en: str
    prompt_de: str = ""
    correct_de: str = ""
    player_answer: str
    grammar_focus: str = ""
    min_words: int = 0
    diary_entry: str = ""
    leseverstehen_question: str = ""
    challenge_index: int = 0
    tier: int = 3
    item_reward: str = ""
    slot: str = "default"

class CommandRequest(BaseModel):
    command: str
    word: str = ""
    prompt_en: str = ""
    grammar_focus: str = ""
    example_answer: str = ""
    slot: str = "default"

class ChapterRequest(BaseModel):
    episode: int
    act: int
    chapter: int
    slot: str = "default"

class FlashcardAnswerRequest(BaseModel):
    german: str
    english: str
    player_answer: str
    slot: str = "default"

class LangtextRequest(BaseModel):
    scenario: str
    player_text: str
    min_words: int = 50
    slot: str = "default"


# ── Routes ────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Walhall RPG API is running"}


@app.get("/debug")
def debug():
    """Shows file structure on Railway for debugging."""
    import glob
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return {
        "base_dir": base,
        "story_dir": STORY_DIR,
        "story_files": glob.glob(os.path.join(STORY_DIR, "*.json")),
        "save_dir_exists": os.path.exists(os.path.join(base, "save")),
        "api_dir": os.path.dirname(os.path.abspath(__file__)),
    }


@app.get("/api/state")
def get_state(slot: str = "default"):
    """Return current game state."""
    state = load_state_slot(slot)
    if state is None:
        return {"exists": False}
    regen_mana(state)
    save_state_slot(state, slot)
    return {"exists": True, "state": state.model_dump()}


@app.post("/api/new-game")
def new_game(req: NewGameRequest):
    """Start a new game with the given name and CEFR level."""
    state = GameState(
        player_name=req.player_name,
        cefr_preference=req.cefr_preference,
        last_played=str(date.today()),
        mana=60,
        mana_max=100,
        gold=5,
    )
    save_state_slot(state, req.slot)
    return {"state": state.model_dump()}


@app.get("/api/chapter/{episode}/{act}/{chapter}")
def get_chapter(episode: int, act: int, chapter: int, slot: str = "default"):
    """Load chapter data including narration."""
    state = load_state_slot(slot)
    if not state:
        raise HTTPException(status_code=404, detail="No save state found")

    ch = load_chapter_data(episode, act, chapter)
    if not ch:
        return {"exists": False}

    # Get or generate narration (separate key from diary)
    narration = get_entry(episode, act, f"narration_{chapter}")
    if narration is None:
        narration = narrate_chapter(state.player_name, ch, state.cefr_preference)
        store_entry(episode, act, f"narration_{chapter}", narration)

    # Get or generate diary entry (separate key)
    diary = get_entry(episode, act, f"diary_{chapter}")
    if diary is None:
        diary = generate_diary_entry(state.player_name, ch, state.cefr_preference)
        store_entry(episode, act, f"diary_{chapter}", diary)

    # Inject diary into leseverstehen challenges
    for c in ch.get("challenges", []):
        if c.get("type") == "leseverstehen":
            c["_diary_entry"] = diary

    # Reset hint counter for new chapter
    state.chapter_hints_used = 0
    save_state(state)

    # Restore challenge_index so refresh resumes from correct position
    saved_index = state.challenge_index if state.chapter == chapter and state.act == act else 0

    return {
        "exists":          True,
        "chapter":         ch,
        "narration":       narration,
        "diary":           diary,
        "challenge_index": saved_index,
    }


@app.post("/api/magic-portal")
def magic_portal(body: dict):
    """Reveal the correct answer. Costs 9 Mana + 2 Gold."""
    slot = body.get("slot","default")
    state = load_state_slot(slot)
    if not state:
        raise HTTPException(status_code=404, detail="No save state")

    PORTAL_COST_MANA = 9
    PORTAL_COST_GOLD = 2
    if state.mana < PORTAL_COST_MANA:
        return {"success": False, "message": f"Nicht genug Mana. Pforte kostet {PORTAL_COST_MANA} Mana."}
    if state.gold < PORTAL_COST_GOLD:
        return {"success": False, "message": f"Nicht genug Gold. Pforte kostet {PORTAL_COST_GOLD} Gold."}

    state.mana -= PORTAL_COST_MANA
    state.gold -= PORTAL_COST_GOLD
    correct_answer = body.get("correct_answer", "")
    xp_reward = body.get("xp_reward", 10)
    grammar_focus = body.get("grammar_focus", "")
    challenge_index = body.get("challenge_index", 0)

    # Award half XP
    half_xp = max(1, xp_reward // 2)
    xp_result = award_xp(state, half_xp)
    state.challenge_index = challenge_index + 1
    if grammar_focus:
        log_mistake(grammar_focus)  # still log as needing work

    save_state_slot(state, slot)
    return {
        "success":       True,
        "correct_answer": correct_answer,
        "xp_gained":     half_xp,
        "levelled_up":   xp_result["levelled_up"],
        "state":         state.model_dump(),
    }


@app.post("/api/answer")
def submit_answer(req: AnswerRequest):
    """Evaluate a player answer and return result + updated state."""
    state = load_state_slot(req.slot)
    if not state:
        raise HTTPException(status_code=404, detail="No save state")

    state.accuracy_attempts += 1
    state.challenge_index = req.challenge_index

    # Route to correct evaluator
    if req.challenge_type == "__save__":
        # Progress save only — no evaluation
        state.challenge_index = req.challenge_index
        save_state(state)
        return {"correct": True, "explanation": "", "grammar_focus": "",
                "xp_gained": 0, "levelled_up": False, "state": state.model_dump()}

    if req.challenge_type == "satzbau":
        result = evaluate_satzbau(req.correct_de or req.prompt_en,
                                   req.player_answer, state.cefr_preference)
    elif req.challenge_type == "langtext":
        if len(req.player_answer.split()) < req.min_words:
            save_state(state)
            return {
                "correct": False,
                "explanation": f"Zu kurz — {len(req.player_answer.split())} Wörter. Mindestens {req.min_words} benötigt.",
                "word_count": len(req.player_answer.split()),
                "state": state.model_dump(),
            }
        result = evaluate_langtext(
            state.player_name, req.prompt_en, req.player_answer,
            req.min_words, state.cefr_preference
        )
    elif req.challenge_type == "leseverstehen":
        result = evaluate_leseverstehen(
            state.player_name, req.diary_entry,
            req.leseverstehen_question, req.player_answer,
            state.cefr_preference
        )
    else:
        result = evaluate_answer(
            state.player_name, req.prompt_de or req.prompt_en,
            req.player_answer, state.cefr_preference
        )

    # XP, Mana, Gold rewards from tier
    xp_gained = 0
    mana_gained = 0
    gold_gained = 0
    levelled_up = False

    if result["correct"]:
        state.accuracy_total += 1
        tier = req.tier if hasattr(req, 'tier') else 3
        multiplier = get_active_multiplier(state)
        if state.dice_active:
            multiplier *= 2.0
            state.dice_active = False

        xp_gained   = max(1, int(tier * 2 * multiplier))
        mana_gained  = tier * 2
        gold_gained  = max(0, tier - 2)

        xp_result   = award_xp(state, xp_gained)
        levelled_up = xp_result["levelled_up"]
        state.mana  = min(state.mana + mana_gained, state.mana_max)
        state.gold += gold_gained

        # Add item reward to inventory
        if req.item_reward and req.item_reward not in state.inventory:
            state.inventory.append(req.item_reward)
        if req.grammar_focus:
            log_correct(req.grammar_focus)
        # Update skill scores
        gf = req.grammar_focus.lower()
        if any(w in gf for w in ["vocab","wort","word"]):
            state.skills.vocabulary = min(100, state.skills.vocabulary + 2)
        elif any(w in gf for w in ["writing","schreib","long","text"]):
            state.skills.writing = min(100, state.skills.writing + 3)
        else:
            state.skills.grammar = min(100, state.skills.grammar + 1)
    else:
        if req.grammar_focus:
            log_mistake(req.grammar_focus)

    save_state_slot(state, req.slot)

    return {
        **result,
        "xp_gained":   xp_gained,
        "mana_gained":  mana_gained,
        "gold_gained":  gold_gained,
        "levelled_up": levelled_up,
        "state":       state.model_dump(),
    }


@app.post("/api/command")
def handle_command(req: CommandRequest):
    """Handle game commands: /stein, /translate, /erkläre, /scroll, /würfeln."""
    state = load_state_slot(req.slot)
    if not state:
        raise HTTPException(status_code=404, detail="No save state")

    cmd = req.command

    if cmd == "/stein":
        if state.mana < 3:
            return {"success": False, "message": "Nicht genug Mana. Stein kostet 3 Mana."}
        state.mana -= 3
        save_state_slot(state, req.slot)
        hint = get_hint(state.player_name, req.prompt_en, state.cefr_preference)
        return {"success": True, "result": hint, "state": state.model_dump()}

    if cmd == "/translate":
        if state.mana < 6:
            return {"success": False, "message": "Nicht genug Mana. Zungengabe kostet 6 Mana."}
        state.mana -= 6
        save_state_slot(state, req.slot)
        return {"success": True, "state": state.model_dump()}

    if cmd == "/erkläre":
        if state.mana < 6:
            return {"success": False, "message": "Nicht genug Mana. Weissagung kostet 6 Mana."}
        if state.gold >= 1:
            state.mana -= 6
            state.gold -= 1
        else:
            # No gold — costs double mana instead
            if state.mana < 12:
                return {"success": False, "message": "Kein Gold verfügbar. Weissagung kostet dann 12 Mana."}
            state.mana -= 12
        save_state_slot(state, req.slot)
        explanation = explain_grammar(
            state.player_name, req.grammar_focus, req.example_answer
        )
        return {"success": True, "result": explanation, "state": state.model_dump()}

    if cmd == "/scroll":
        if "Ältere Schriftrolle" not in state.inventory:
            return {"success": False, "message": "Du besitzt die Ältere Schriftrolle nicht."}
        definition = elder_scroll_lookup(req.word, state.cefr_preference)
        return {"success": True, "result": definition, "state": state.model_dump()}

    if cmd == "/würfeln":
        if "Glückswürfel" not in state.inventory:
            return {"success": False, "message": "Du hast keine Glückswürfel."}
        if state.dice_active:
            return {"success": False, "message": "Die Würfel sind bereits aktiv!"}
        import random
        success_chance = 0.55 + (state.accuracy_pct / 100 * 0.30)
        won = random.random() < success_chance
        if won:
            state.dice_active = True
        else:
            state.mana = max(0, state.mana - 15)
        save_state_slot(state, req.slot)
        return {"success": True, "won": won, "state": state.model_dump()}

    if cmd == "/level":
        return {"success": True, "current_level": state.cefr_preference}

    return {"success": False, "message": f"Unbekannter Befehl: {cmd}"}


@app.post("/api/set-level")
def set_level(body: dict):
    """Update the player's CEFR preference."""
    slot = body.get("slot", "default")
    state = load_state_slot(slot)
    if not state:
        raise HTTPException(status_code=404, detail="No save state")
    state.cefr_preference = body.get("cefr", "B2")
    save_state_slot(state, slot)
    return {"state": state.model_dump()}


@app.get("/api/diary")
def get_diary(slot: str = "default"):
    """Return all diary entries for episode 1."""
    state = load_state_slot(slot)
    if not state:
        raise HTTPException(status_code=404, detail="No save state")
    entries = get_all_entries_text(state.episode)
    return {"entries": entries}


@app.post("/api/flashcards/generate")
def generate_cards(req: ChapterRequest):
    """Generate 5 flashcards for the given chapter."""
    state = load_state_slot(req.slot)
    if not state:
        raise HTTPException(status_code=404, detail="No save state")
    ch = load_chapter_data(req.episode, req.act, req.chapter)
    if not ch:
        raise HTTPException(status_code=404, detail="Chapter not found")
    from engine.flashcard import load_flashcard_history
    seen = list(load_flashcard_history().keys())
    cards = generate_flashcards(ch, state.cefr_preference, seen)
    return {"cards": cards}


@app.post("/api/flashcards/evaluate")
def evaluate_card(req: FlashcardAnswerRequest):
    """Evaluate a single flashcard answer."""
    state = load_state_slot(req.slot)
    if not state:
        raise HTTPException(status_code=404, detail="No save state")
    result = evaluate_flashcard(
        req.german, req.english, req.player_answer, state.cefr_preference
    )
    mark_seen(req.german)
    return result


@app.post("/api/flashcards/complete")
def complete_flashcards(body: dict):
    """Award Mana for completing a flashcard round."""
    slot = body.get("slot","default")
    state = load_state_slot(slot)
    if not state:
        raise HTTPException(status_code=404, detail="No save state")
    correct = body.get("correct", 0)
    total   = body.get("total", 5)
    mana = mana_reward(correct, total)
    state.mana = min(state.mana + mana, state.mana_max)
    save_state_slot(state, slot)
    return {"mana_gained": mana, "state": state.model_dump()}


@app.post("/api/reset")
def reset_game(body: dict = {}):
    """Delete a specific slot save file."""
    slot = body.get("slot","default") if body else "default"
    path = get_save_path(slot)
    if os.path.exists(path):
        os.remove(path)
    return {"reset": True}


@app.post("/api/complete-chapter")
def complete_chapter(body: dict):
    """Award completion XP and advance chapter."""
    slot = body.get("slot","default")
    state = load_state_slot(slot)
    if not state:
        raise HTTPException(status_code=404, detail="No save state")
    completion_xp   = body.get("completion_xp", 50)
    next_chapter    = body.get("next_chapter")
    ending_answer   = body.get("ending_answer", "")

    xp_result = award_xp(state, completion_xp)

    # Detect ending choice if chapter 9
    if body.get("chapter") == 9:
        state.episode_1_ending = _detect_ending(ending_answer)

    if next_chapter:
        state.chapter = next_chapter
        if next_chapter >= 4 and state.act == 1:
            state.act = 2
        elif next_chapter >= 8 and state.act == 2:
            state.act = 3

    save_state_slot(state, slot)

    # Generate epilogue if episode complete
    epilogue = None
    if state.episode_1_ending and not next_chapter:
        stats = {
            "level": state.level, "accuracy_pct": state.accuracy_pct,
            "streak": state.streak, "inventory": state.inventory,
        }
        epilogue = narrate_epilogue(state.player_name, state.episode_1_ending, stats)

    return {
        "xp_result": xp_result,
        "epilogue": epilogue,
        "ending": state.episode_1_ending,
        "state": state.model_dump(),
    }


def _detect_ending(answer: str) -> str:
    answer_lower = answer.lower()
    rache    = ["rache","zerstör","vernicht","töt","gefährlich","kann nicht","darf nicht"]
    vergeb   = ["vergeb","befreie","heilen","vergebung","verstehe","loslassen","freiheit"]
    rs = sum(1 for w in rache  if w in answer_lower)
    vs = sum(1 for w in vergeb if w in answer_lower)
    return "rache" if rs > vs else "vergebung"


@app.post("/api/streak")
def update_streak():
    """Call once per session to update daily streak."""
    state = load_state_slot(req.slot)
    if not state:
        raise HTTPException(status_code=404, detail="No save state")
    today = str(date.today())
    streak_reward = 0
    if state.last_played != today:
        state.streak += 1
        state.last_played = today
        # Every 5 days — Gold bonus
        if state.streak % 5 == 0:
            state.gold += 10
            streak_reward = 10
        save_state_slot(state, slot)
    return {"streak": state.streak, "streak_reward": streak_reward, "state": state.model_dump()}