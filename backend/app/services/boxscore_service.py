# backend/app/services/boxscore_service.py
#
# Player box scores for today's real games, from ESPN's free public scoreboard
# and game-summary endpoints (no API key). balldontlie's free plan doesn't
# include player stats, and NBA.com's live-data CDN blocks server requests.

import json
import logging
from datetime import datetime

import httpx
import pytz

from app.services.supabase_service import redis_get, redis_set

logger = logging.getLogger(__name__)

ET = pytz.timezone("America/New_York")
SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"

# ESPN abbreviations that differ from the ones balldontlie (and this app) use.
ESPN_TO_APP = {"GS": "GSW", "NY": "NYK", "SA": "SAS", "NO": "NOP", "UTAH": "UTA", "WSH": "WAS"}


def _abbr(espn_abbr: str) -> str:
    return ESPN_TO_APP.get(espn_abbr, espn_abbr)


def _num(v) -> int:
    try:
        return int(str(v).replace("+", ""))
    except (TypeError, ValueError):
        return 0


def _made_att(v) -> tuple[int, int]:
    try:
        made, att = str(v).split("-")
        return int(made), int(att)
    except ValueError:
        return 0, 0


def _players(team_block: dict, side: str) -> list[dict]:
    out = []
    for group in team_block.get("statistics", []):
        labels = group.get("labels") or group.get("names") or []
        for a in group.get("athletes", []):
            if a.get("didNotPlay") or not a.get("stats"):
                continue
            s = dict(zip(labels, a["stats"]))
            fgm, fga = _made_att(s.get("FG"))
            ath = a.get("athlete", {})
            out.append({
                "player_id": str(ath.get("id")),
                "side": side,
                "name": ath.get("displayName", ""),
                "pos": (ath.get("position") or {}).get("abbreviation", ""),
                "starter": bool(a.get("starter")),
                "minutes": s.get("MIN", "0"),
                "pts": _num(s.get("PTS")),
                "reb": _num(s.get("REB")),
                "ast": _num(s.get("AST")),
                "stl": _num(s.get("STL")),
                "blk": _num(s.get("BLK")),
                "turnovers": _num(s.get("TO")),
                "fgm": fgm,
                "fga": fga,
                "plus_minus": _num(s.get("+/-")),
                # Overlay data (rank / form / matchup) isn't in the live feed.
                "last5_pts": [],
                "league_rank_pts": None,
                "league_rank_reb": None,
                "league_rank_ast": None,
                "matchup_avg_pts": None,
            })
    return out


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

    def empty(status: str) -> dict:
        return {"available": False, "status": status, "players": []}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            today = datetime.now(ET).strftime("%Y%m%d")
            r = await client.get(SCOREBOARD_URL, params={"dates": today})
            r.raise_for_status()
            event = None
            for ev in r.json().get("events", []):
                teams = {c["homeAway"]: _abbr(c["team"]["abbreviation"])
                         for c in ev["competitions"][0]["competitors"]}
                if teams.get("home") == home_abbr and teams.get("away") == away_abbr:
                    event = ev
                    break
            if not event:
                return empty("not_found")

            state = event["status"]["type"]["state"]  # pre / in / post
            if state == "pre":
                result = empty("scheduled")
                await redis_set(cache_key, json.dumps(result), 120)
                return result

            r = await client.get(SUMMARY_URL, params={"event": event["id"]})
            r.raise_for_status()
            players = []
            for block in r.json().get("boxscore", {}).get("players", []):
                abbr = _abbr(block.get("team", {}).get("abbreviation", ""))
                side = "home" if abbr == home_abbr else "away"
                players += _players(block, side)

            final = state == "post"
            result = {"available": bool(players), "status": "final" if final else "live", "players": players}
            await redis_set(cache_key, json.dumps(result), 3600 if final else 30)
            return result
    except Exception as e:
        logger.error(f"Box score fetch failed for {away_abbr}@{home_abbr}: {e}")
        return empty(f"error: {e.__class__.__name__}")
