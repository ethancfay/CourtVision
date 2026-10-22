# backend/app/services/gemini_service.py
# Fully migrated from google.generativeai to Groq.
# AsyncGroq is natively async — no run_in_executor needed anywhere.
# pip install groq

import json
import logging

from groq import AsyncGroq, APIConnectionError, APIStatusError, RateLimitError

from app.config import settings

logger = logging.getLogger(__name__)

# ─── CLIENT ──────────────────────────────────────────────────────────────────
client = AsyncGroq(api_key=settings.GROQ_API_KEY)

# Model is configurable with GROQ_MODEL (default openai/gpt-oss-120b).
MODEL = settings.GROQ_MODEL
# gpt-oss models reason before answering; keep that short so answers fit the token limit.
EXTRA = {"reasoning_effort": "low"} if MODEL.startswith("openai/gpt-oss") else {}


# ─── SHARED ASYNC CALLER (non-streaming JSON responses) ──────────────────────

async def _call_groq(system: str, user: str) -> dict:
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_completion_tokens=2048,
            response_format={"type": "json_object"},  # guarantees valid JSON back
            extra_body=EXTRA or None,
        )
        text = response.choices[0].message.content or ""
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"[Groq] JSON parse failed: {e} | raw: {text[:200]}")
        raise
    except RateLimitError as e:
        logger.error(f"[Groq] Rate limited: {e}")
        raise
    except APIConnectionError as e:
        logger.error(f"[Groq] Connection error: {e}")
        raise
    except APIStatusError as e:
        logger.error(f"[Groq] API error {e.status_code}: {e.message}")
        raise


# ─── GAME PREDICTION ─────────────────────────────────────────────────────────

PREDICTION_SYSTEM = """You are a sharp NBA analyst. Return ONLY valid JSON with these exact keys:
- winner: string (full team name)
- winner_abbr: string (3-letter abbreviation)
- confidence: integer between 55 and 88
- score_home: integer (predicted home team final score)
- score_away: integer (predicted away team final score)
- key_factors: array of exactly 3 strings, each under 15 words, specific and stat-based
No explanation. No markdown. Raw JSON object only."""


async def generate_prediction(game: dict) -> dict:
    user = (
        f"Game: {game['home_team_name']} (home) vs {game['away_team_name']} (away).\n"
        f"Home record: {game.get('home_record', 'N/A')}. Away record: {game.get('away_record', 'N/A')}.\n"
        f"Home last 5: {game.get('home_last5', 'W W L W L')}. Away last 5: {game.get('away_last5', 'L W W L W')}.\n"
        f"Home rest days: {game.get('home_rest', 2)}. Away rest days: {game.get('away_rest', 1)}."
    )
    return await _call_groq(PREDICTION_SYSTEM, user)


# ─── PLAYER CARD ─────────────────────────────────────────────────────────────

PLAYER_CARD_SYSTEM = """You are an NBA scout. Return ONLY valid JSON with these exact keys:
- report: string, exactly 3 sentences, specific and data-driven
- projection: object with keys pts, reb, ast (each a string range like "22-26", "8-11", "4-7")
- trend: string, must be exactly "hot", "cold", or "neutral"
No explanation. No markdown. Raw JSON object only."""


async def generate_player_card(data: dict) -> dict:
    user = (
        f"Player: {data['player_name']}.\n"
        f"Season averages: {data['season_avg'].get('pts', 'N/A')} PPG, "
        f"{data['season_avg'].get('reb', 'N/A')} RPG, {data['season_avg'].get('ast', 'N/A')} APG.\n"
        f"Last 5 games (points): {', '.join(str(x) for x in data['last5'])}.\n"
        f"Tonight vs: {data['opponent']}."
    )
    return await _call_groq(PLAYER_CARD_SYSTEM, user)


# ─── TAKE VERDICT ────────────────────────────────────────────────────────────

TAKE_VERDICT_SYSTEM = """You are a data-driven NBA analyst. Return ONLY valid JSON with these exact keys:
- steelman: string, exactly one sentence under 20 words, supports the take with a specific stat
- challenge: string, exactly one sentence under 20 words, pushes back with a specific counter-stat
- verdict_label: string, must be exactly "Backed by data", "Partially supported", or "Overblown"
No explanation. No markdown. Raw JSON object only."""


async def generate_take_verdict(take_text: str) -> dict:
    user = f'Media take: "{take_text}"'
    return await _call_groq(TAKE_VERDICT_SYSTEM, user)


# ─── CHAT STREAMING ──────────────────────────────────────────────────────────

CHAT_SYSTEM_INSTRUCTION = (
    "You are CourtIQ, an expert AI basketball assistant. "
    "You provide concise, insightful, and data-driven answers about NBA news, player stats, "
    "and general basketball knowledge. Keep responses under 3 paragraphs. "
    "Be friendly, energetic, and talk like a sharp basketball analyst."
)


async def generate_chat_stream(messages: list):
    """
    Native async streaming via AsyncGroq — no threading or queues needed.
    Yields text chunks as they arrive from the model.
    """
    formatted = [{"role": "system", "content": CHAT_SYSTEM_INSTRUCTION}]
    for msg in messages:
        role = "assistant" if msg.role == "assistant" else "user"
        formatted.append({"role": role, "content": msg.content})

    try:
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=formatted,
            temperature=0.7,
            max_completion_tokens=2048,
            stream=True,
            extra_body=EXTRA or None,
        )
        async for chunk in stream:
            text = chunk.choices[0].delta.content or ""
            if text:
                yield text
    except RateLimitError as e:
        logger.error(f"[Groq chat] Rate limited: {e}")
        yield "Sorry, I'm getting too many requests right now. Try again in a moment."
    except APIConnectionError as e:
        logger.error(f"[Groq chat] Connection error: {e}")
        yield "Sorry, I couldn't reach the AI service. Check your connection."
    except Exception as e:
        logger.error(f"[Groq chat] Unexpected error: {e}")
        yield "Sorry, something went wrong. Please try again."
