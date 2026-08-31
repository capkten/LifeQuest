from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.action_center import TodayActionCenter
from app.services.action_center import ActionCenterService


router = APIRouter(prefix="/api/action-center", tags=["action-center"])


@router.get("/today", response_model=TodayActionCenter)
def get_today_action_center(
    target_date: Optional[date] = Query(None, alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ActionCenterService(db).get_today(current_user.id, target_date)
