# backend/app/services/nba_service.py

import asyncio
import json
import logging
from datetime import date, datetime
from functools import partial
import time

import pytz

from dateutil.parser import parse as parse_dt

from balldontlie import BalldontlieAPI
from balldontlie.exceptions import AuthenticationError, BallDontLieException, RateLimitError

from app.config import settings
from app.data.seed_mock import MOCK_GAMES
from app.services.supabase_service import redis_get, redis_set, supabase_client

logger = logging.getLogger(__name__)

# NBA schedules run on US Eastern time. The server clock is UTC, so after 8 PM ET
# date.today() would already be tomorrow and show the wrong slate of games.
ET = pytz.timezone("America/New_York")


def nba_today() -> str:
    return datetime.now(ET).date().isoformat()

_bdl = BalldontlieAPI(api_key=settings.BALLDONTLIE_API_KEY)

# ─── BDL → NBA API TEAM ID MAP ───────────────────────────────────────────────
# BUG FIX (root cause of identical predictions):
# balldontlie uses its own team IDs (1-30).
# The ML model was trained on nba_api data which uses official NBA IDs (161061XXXX).
# When features.py looks up team history by home_team_id, it finds zero matches
# because "10" != "1610612746", so every team gets fallback values:
# home_pts=110.0, away_pts=110.0, home_win_pct=0.5 → identical predictions for all games.
# Fix: translate balldontlie IDs to official NBA IDs before passing to predict_game.
BDL_TO_NBA_TEAM_ID = {
    "1":  "1610612737",  # Atlanta Hawks
    "2":  "1610612738",  # Boston Celtics
    "3":  "1610612751",  # Brooklyn Nets
    "4":  "1610612766",  # Charlotte Hornets
    "5":  "1610612741",  # Chicago Bulls
    "6":  "1610612739",  # Cleveland Cavaliers
    "7":  "1610612742",  # Dallas Mavericks
    "8":  "1610612743",  # Denver Nuggets
    "9":  "1610612765",  # Detroit Pistons
    "10": "1610612744",  # Golden State Warriors
    "11": "1610612745",  # Houston Rockets
    "12": "1610612754",  # Indiana Pacers
    "13": "1610612746",  # LA Clippers
    "14": "1610612747",  # Los Angeles Lakers
    "15": "1610612763",  # Memphis Grizzlies
    "16": "1610612748",  # Miami Heat
    "17": "1610612749",  # Milwaukee Bucks
    "18": "1610612750",  # Minnesota Timberwolves
    "19": "1610612740",  # New Orleans Pelicans
    "20": "1610612752",  # New York Knicks
    "21": "1610612760",  # Oklahoma City Thunder
    "22": "1610612753",  # Orlando Magic
    "23": "1610612755",  # Philadelphia 76ers
    "24": "1610612756",  # Phoenix Suns
    "25": "1610612757",  # Portland Trail Blazers
    "26": "1610612758",  # Sacramento Kings
    "27": "1610612759",  # San Antonio Spurs
    "28": "1610612761",  # Toronto Raptors
    "29": "1610612762",  # Utah Jazz
    "30": "1610612764",  # Washington Wizards
}


def _safe_int(value) -> int | None:
    """Convert any numeric value to int, returning None for missing values."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _fetch_games_sync(today: str) -> list:
    resp = _bdl.nba.games.list(dates=[today])
    raw_games = resp.data if hasattr(resp, "data") else []
    return [_transform_game(g) for g in raw_games]


async def get_today_games() -> list:
    today = nba_today()
    cache_key = f"live:games:{today}"

    # 1. Redis cache
    cached = await redis_get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    # 2. balldontlie SDK
    try:
        loop = asyncio.get_event_loop()
        games = await loop.run_in_executor(None, partial(_fetch_games_sync, today))

        if games:
            if supabase_client:
                for g in games:
                    try:
                        supabase_client.table("games").upsert(g).execute()
                    except Exception as e:
                        logger.warning(f"Supabase upsert failed for game {g.get('game_id')}: {e}")

            has_live = any(g["status"] == "live" for g in games)
            ttl = 30 if has_live else 300
            await redis_set(cache_key, json.dumps(games), ttl)
            return games

        logger.info(f"balldontlie SDK: no games scheduled for {today}")
        return []

    except AuthenticationError:
        logger.error("balldontlie AuthenticationError — check BALLDONTLIE_API_KEY in .env")
    except RateLimitError:
        logger.warning("balldontlie rate limit hit — falling back to Supabase")
    except BallDontLieException as e:
        logger.error(f"balldontlie SDK error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching games: {e}")

    # 3. Supabase fallback
    if supabase_client:
        try:
            result = (
                supabase_client.table("games")
                .select("*")
                .eq("game_date", today)
                .execute()
            )
            if result.data:
                logger.info(f"Returning {len(result.data)} games from Supabase cache")
                return result.data
        except Exception as e:
            logger.error(f"Supabase fallback failed: {e}")

    logger.warning("⚠️  Returning MOCK data — all real sources failed.")
    return MOCK_GAMES


def _transform_game(g) -> dict:
    home = g.home_team
    away = g.visitor_team

    bdl_home_id = str(home.id)
    bdl_away_id = str(away.id)

    # Translate to NBA official IDs so the ML feature extractor can match
    # team history in the Supabase games table (which was built from nba_api).
    nba_home_id = BDL_TO_NBA_TEAM_ID.get(bdl_home_id, bdl_home_id)
    nba_away_id = BDL_TO_NBA_TEAM_ID.get(bdl_away_id, bdl_away_id)

    # BUG FIX: home_team_score/visitor_team_score come as float 0.0 for unstarted
    # games. Supabase INTEGER columns reject "0.0" strings. _safe_int converts
    # float → int and None → None cleanly.
    home_score = _safe_int(getattr(g, "home_team_score", None))
    away_score = _safe_int(getattr(g, "visitor_team_score", None))

    # For unstarted games, store NULL not 0 — 0 implies the game started 0-0
    if home_score == 0 and away_score == 0 and getattr(g, "period", 0) == 0:
        home_score = None
        away_score = None

    # balldontlie puts the tip-off time in `datetime`, or in `status` for games
    # that haven't started (e.g. "2026-10-22T23:00:00Z"). Show it as "7:00 PM ET".
    status_raw = g.status or ""
    dt_str = getattr(g, "datetime", None) or (status_raw if status_raw[:2] == "20" else None)
    tipoff_time = None
    if dt_str:
        try:
            tipoff_time = parse_dt(dt_str).astimezone(ET).strftime("%-I:%M %p ET")
        except Exception:
            tipoff_time = None

    return {
        "game_id": str(g.id),
        "game_date": g.date[:10] if g.date else None,
        "home_team_id": nba_home_id,       # NBA official ID for ML feature lookup
        "away_team_id": nba_away_id,       # NBA official ID for ML feature lookup
        "home_team_name": home.full_name,
        "away_team_name": away.full_name,
        "home_team_abbr": home.abbreviation,
        "away_team_abbr": away.abbreviation,
        "home_score": home_score,
        "away_score": away_score,
        "status": _map_status(g.status or ""),
        "quarter": _safe_int(getattr(g, "period", None)),
        "clock": getattr(g, "time", None),
        "tipoff_time": tipoff_time,
    }


def _map_status(s: str) -> str:
    s_lower = s.lower()
    if "final" in s_lower:
        return "final"
    if any(x in s_lower for x in ["qtr", "half", "ot", "overtime"]):
        return "live"
    return "upcoming"

# ─── HISTORY BOOTSTRAP ───────────────────────────────────────────────────────
# Loads past games from balldontlie into the Supabase games table so the ML
# feature extractor has recent results for every team. Runs as a background job
# from the admin route. The free balldontlie tier allows 5 requests/minute, so
# requests are spaced out.
def bootstrap_history(seasons: list[int], delay_seconds: float = 13.0) -> int:
    if not supabase_client:
        logger.error("bootstrap_history: Supabase is not configured")
        return 0
    total = 0
    for season in seasons:
        cursor = None
        while True:
            try:
                resp = _bdl.nba.games.list(seasons=[season], per_page=100, cursor=cursor)
            except RateLimitError:
                logger.warning("bootstrap_history: rate limited, waiting 60s")
                time.sleep(60)
                continue
            except Exception as e:
                logger.error(f"bootstrap_history: season {season} failed: {e}")
                break
            rows = [_transform_game(g) for g in (resp.data or [])]
            if rows:
                try:
                    supabase_client.table("games").upsert(rows).execute()
                    total += len(rows)
                    logger.info(f"bootstrap_history: season {season}, {total} games saved so far")
                except Exception as e:
                    logger.error(f"bootstrap_history: upsert failed: {e}")
            meta = getattr(resp, "meta", None)
            cursor = getattr(meta, "next_cursor", None) if meta else None
            if not cursor:
                break
            time.sleep(delay_seconds)
    logger.info(f"bootstrap_history: done, {total} games saved")
    return total
