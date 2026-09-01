from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.review import WeeklyReviewResponse
from app.services.review import ReviewService


router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/weekly", response_model=WeeklyReviewResponse)
def get_weekly_review(
    week_start: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ReviewService(db).get_weekly_review(current_user.id, week_start)
    except ValueError as exc:
        if str(exc) == "WEEK_START_MUST_BE_MONDAY":
            raise HTTPException(status_code=422, detail=str(exc))
        raise
