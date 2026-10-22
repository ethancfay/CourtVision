# backend/app/services/chat_health.py
import asyncio
import logging

from groq import AsyncGroq, APIConnectionError, APIStatusError, RateLimitError

from app.config import settings

logger = logging.getLogger(__name__)

HEALTH_PROMPT = "What team does LeBron James play for? One sentence only."


async def check_chat_health() -> dict:
    """
    Async health check using Groq. Call directly with await — no executor needed.
    Returns {"status": "ok"|"error", "response_ms": int, ...}
    """
    import time
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    start = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": HEALTH_PROMPT}],
            max_completion_tokens=300,
            temperature=0.0,
        )
        elapsed = round((time.perf_counter() - start) * 1000)
        text = response.choices[0].message.content or ""
        logger.info(f"[chat:health] ✅ OK ({elapsed}ms): '{text.strip()}'")
        return {"status": "ok", "response_ms": elapsed, "reply": text.strip()}

    except RateLimitError as e:
        elapsed = round((time.perf_counter() - start) * 1000)
        logger.error(f"[chat:health] ❌ RATE LIMITED ({elapsed}ms) — {e}")
        return {"status": "error", "response_ms": elapsed, "error": "rate_limited"}
    except APIConnectionError as e:
        elapsed = round((time.perf_counter() - start) * 1000)
        logger.error(f"[chat:health] ❌ CONNECTION ERROR ({elapsed}ms) — check network/firewall: {e}")
        return {"status": "error", "response_ms": elapsed, "error": "connection_error"}
    except APIStatusError as e:
        elapsed = round((time.perf_counter() - start) * 1000)
        if e.status_code in (401, 403):
            logger.error(f"[chat:health] ❌ AUTH FAILURE ({elapsed}ms) — check GROQ_API_KEY in .env")
        else:
            logger.error(f"[chat:health] ❌ API ERROR {e.status_code} ({elapsed}ms) — {e.message}")
        return {"status": "error", "response_ms": elapsed, "error": f"http_{e.status_code}"}
    except Exception as e:
        elapsed = round((time.perf_counter() - start) * 1000)
        logger.error(f"[chat:health] ❌ FAILED ({elapsed}ms) — {e}")
        return {"status": "error", "response_ms": elapsed, "error": str(e)}


def check_chat_health_sync() -> dict:
    """Sync wrapper for use in non-async contexts (e.g. startup hooks)."""
    return asyncio.run(check_chat_health())
