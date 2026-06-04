from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.stats import StatsService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview")
def get_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = StatsService(db)
    return service.get_overview(current_user.id)


@router.get("/tasks")
def get_task_trends(
    period: Literal["week", "month", "year"] = "week",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = StatsService(db)
    return service.get_task_trends(current_user.id, period)


@router.get("/habits")
def get_habit_stats(
    period: Literal["week", "month"] = "week",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = StatsService(db)
    return service.get_habit_stats(current_user.id, period)


@router.get("/coins")
def get_coin_trends(
    period: Literal["week", "month", "year"] = "month",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = StatsService(db)
    return service.get_coin_trends(current_user.id, period)


@router.get("/level")
def get_level_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = StatsService(db)
    return service.get_level_progress(current_user.id)
