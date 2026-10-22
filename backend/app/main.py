# backend/app/main.py
import threading
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.ml.predict import load_model_artifacts
from app.routes import admin, chat, games, player_card, predictions, takes
from app.services.tests.chat_health import check_chat_health



def _bootstrap_if_empty():
    from app.services.nba_service import bootstrap_history
    from app.services.supabase_service import supabase_client
    if not supabase_client or not settings.BALLDONTLIE_API_KEY:
        return
    try:
        res = supabase_client.table("games").select("game_id", count="exact").limit(1).execute()
        if (res.count or 0) >= 500:
            logger.info(f"History bootstrap skipped: {res.count} games already stored")
            return
    except Exception as e:
        logger.error(f"History bootstrap check failed: {e}")
        return
    today = date.today()
    current = today.year if today.month >= 10 else today.year - 1
    logger.info("Games table nearly empty, starting history bootstrap...")
    bootstrap_history([current - 1, current])

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CourtIQ API starting up...")

    # ML model
    try:
        load_model_artifacts()
        logger.info("ML model artifacts loaded successfully")
    except FileNotFoundError:
        logger.warning("ML model artifacts not found — predictions will use Gemini fallback. Run bootstrap + train first.")
    except Exception as e:
        logger.error(f"ML model load failed: {e}")

    # Scheduler
    if settings.ENABLE_SCHEDULER:
        start_scheduler()
        logger.info("Background scheduler started")

    # One-time history load: if the games table is nearly empty, pull last season
    # and the current season from balldontlie in the background.
    if settings.BOOTSTRAP_ON_STARTUP:
        threading.Thread(target=_bootstrap_if_empty, daemon=True).start()

    # Chatbot health check — only runs in production to avoid wasting
    # free tier quota on every hot-reload during development.
    if settings.ENVIRONMENT == "production":
        logger.info("Running chatbot health check...")
        result = await check_chat_health()  # now fully async — no executor needed
        if result["status"] == "ok":
            logger.info(f"Chatbot health check ✅ OK ({result['response_ms']}ms)")
        else:
            logger.warning(f"Chatbot health check ❌ FAILED — chat will not work. Details: {result}")
    else:
        logger.info("Chatbot health check skipped (development mode — set ENVIRONMENT=production to enable)")

    yield

    # Shutdown
    if settings.ENABLE_SCHEDULER:
        stop_scheduler()
    logger.info("CourtIQ API shut down")


app = FastAPI(
    title="CourtIQ API",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games.router,       prefix="/api")
app.include_router(predictions.router, prefix="/api")
app.include_router(player_card.router, prefix="/api")
app.include_router(takes.router,       prefix="/api")
app.include_router(admin.router,       prefix="/api")
app.include_router(chat.router,        prefix="/api")


@app.get("/health")
def health():
    from app.ml.predict import model_loaded
    return {
        "status": "ok",
        "service": "courtiq-api",
        "ml_model_loaded": model_loaded(),
        "environment": settings.ENVIRONMENT,
    }
