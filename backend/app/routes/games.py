# backend/app/routes/games.py
import logging

from fastapi import APIRouter

from app.services import boxscore_service, nba_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/games")
async def get_games():
    logger.info("Fetching today's games")
    # BUG FIX: Original games.py checked Redis, then called nba_service.get_today_games()
    # which *also* checked Redis as its first step — a double cache read on every miss.
    # It also always re-cached with ttl=30, overwriting the smart live/upcoming TTL
    # logic inside nba_service. Fix: let nba_service own the full fetch+cache pipeline.
    # This route is now a clean single-responsibility wrapper.
    try:
        games = await nba_service.get_today_games()
        return games
    except Exception as e:
        logger.error(f"Failed to fetch games: {e}")
        from app.data.seed_mock import MOCK_GAMES
        return MOCK_GAMES


@router.get("/boxscore")
async def get_boxscore(home: str, away: str):
    """Player box score for one of today's games, by team abbreviations."""
    return await boxscore_service.get_boxscore(home, away)
