# backend/app/routes/admin.py
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from app.config import settings
from app.jobs.ingest_games import run_ingest_games
from app.jobs.retrain import run_retrain
from app.ml.evaluate import get_model_status
from app.services.nba_service import bootstrap_history

router = APIRouter()


def _check_token(token: str | None):
    # Admin routes are public URLs, so they need a shared secret.
    if not settings.ADMIN_TOKEN or token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Missing or wrong X-Admin-Token")


@router.post("/admin/trigger-ingest")
async def trigger_ingest(background_tasks: BackgroundTasks, x_admin_token: str | None = Header(default=None)):
    _check_token(x_admin_token)
    background_tasks.add_task(run_ingest_games)
    return {"status": "ingest job queued"}


@router.post("/admin/trigger-retrain")
async def trigger_retrain(background_tasks: BackgroundTasks, x_admin_token: str | None = Header(default=None)):
    _check_token(x_admin_token)
    background_tasks.add_task(run_retrain)
    return {"status": "retrain job queued"}


@router.post("/admin/bootstrap-history")
async def trigger_bootstrap_history(background_tasks: BackgroundTasks, x_admin_token: str | None = Header(default=None)):
    """Load last season and the current season from balldontlie (takes several minutes)."""
    _check_token(x_admin_token)
    today = date.today()
    current = today.year if today.month >= 10 else today.year - 1  # NBA season starts in October
    seasons = [current - 1, current]
    background_tasks.add_task(bootstrap_history, seasons)
    return {"status": "history bootstrap queued", "seasons": seasons}


@router.get("/admin/model-status")
async def model_status():
    return get_model_status()
