from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.achievement import AchievementResponse, UserAchievementResponse
from app.services.achievement import AchievementService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/achievements", tags=["achievements"])


@router.get("", response_model=List[AchievementResponse])
def get_achievements(db: Session = Depends(get_db)):
    service = AchievementService(db)
    return service.get_all_achievements()


@router.get("/me", response_model=List[UserAchievementResponse])
def get_user_achievements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AchievementService(db)
    return service.get_user_achievements(current_user.id)
