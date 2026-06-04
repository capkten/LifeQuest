from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.calendar import CalendarService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/events")
def get_events(
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CalendarService(db)
    return service.get_events(current_user.id, start, end)


@router.get("/day/{date}")
def get_day_detail(
    date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CalendarService(db)
    return service.get_day_detail(current_user.id, date)
