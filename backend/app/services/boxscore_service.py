# backend/app/services/boxscore_service.py
#
# Player box scores for today's real games, from NBA.com's free public live-data
# files (no API key). balldontlie's free plan doesn't include player stats.

import json
import logging
import re

import httpx

from app.services.supabase_service import redis_get, redis_set

logger = logging.getLogger(__name__)

SCOREBOARD_URL = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
BOXSCORE_URL = "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{}.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Accept": "application/json",
}


def _minutes(iso: str | None) -> str:
    """'PT28M14.00S' -> '28:14'."""
    m = re.match(r"PT(\d+)M(\d+)", iso or "")
    return f"{int(m.group(1))}:{int(m.group(2)):02d}" if m else "0:00"


def _player(p: dict, side: str) -> dict:
    s = p.get("statistics", {})
    return {
        "player_id": str(p.get("personId")),
        "side": side,
        "name": p.get("name") or f"{p.get('firstName', '')} {p.get('familyName', '')}".strip(),
        "pos": p.get("position") or "",
        "starter": p.get("starter") == "1",
        "minutes": _minutes(s.get("minutes")),
        "pts": s.get("points", 0),
        "reb": s.get("reboundsTotal", 0),
        "ast": s.get("assists", 0),
        "stl": s.get("steals", 0),
        "blk": s.get("blocks", 0),
        "turnovers": s.get("turnovers", 0),
        "fgm": s.get("fieldGoalsMade", 0),
        "fga": s.get("fieldGoalsAttempted", 0),
        "plus_minus": int(s.get("plusMinusPoints", 0) or 0),
        # Overlay data (rank / form / matchup) isn't in the live feed.
        "last5_pts": [],
        "league_rank_pts": None,
        "league_rank_reb": None,
        "league_rank_ast": None,
        "matchup_avg_pts": None,
    }


async def _get_json(client: httpx.AsyncClient, url: str) -> dict | None:
    r = await client.get(url)
    if r.status_code != 200:
        logger.info(f"NBA CDN {r.status_code} for {url}")
        return None
    return r.json()


async def get_boxscore(home_abbr: str, away_abbr: str) -> dict:
    """Return {"available": bool, "status": str, "players": [...]} for today's game."""
    home_abbr, away_abbr = home_abbr.upper(), away_abbr.upper()
    cache_key = f"boxscore:{away_abbr}@{home_abbr}"
    cached = await redis_get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    empty = {"available": False, "status": "unavailable", "players": []}
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
            board = await _get_json(client, SCOREBOARD_URL)
            if not board:
                return empty
            game = next(
                (g for g in board.get("scoreboard", {}).get("games", [])
                 if g["homeTeam"]["teamTricode"] == home_abbr
                 and g["awayTeam"]["teamTricode"] == away_abbr),
                None,
            )
            if not game:
                return empty
            # gameStatus: 1 = scheduled, 2 = live, 3 = final
            if game.get("gameStatus") == 1:
                result = {"available": False, "status": "scheduled", "players": []}
                await redis_set(cache_key, json.dumps(result), 120)
                return result

            box = await _get_json(client, BOXSCORE_URL.format(game["gameId"]))
            if not box:
                return empty
            g = box.get("game", {})
            players = [
                _player(p, side)
                for side, team in (("home", g.get("homeTeam", {})), ("away", g.get("awayTeam", {})))
                for p in team.get("players", [])
                if p.get("played") == "1"
            ]
            final = game.get("gameStatus") == 3
            result = {"available": bool(players), "status": "final" if final else "live", "players": players}
            await redis_set(cache_key, json.dumps(result), 3600 if final else 30)
            return result
    except Exception as e:
        logger.error(f"Box score fetch failed for {away_abbr}@{home_abbr}: {e}")
        return empty
