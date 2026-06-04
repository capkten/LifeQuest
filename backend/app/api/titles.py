from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.title import TitleResponse, UserTitleResponse, TitleActivateRequest
from app.services.title import TitleService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/titles", tags=["titles"])


@router.get("", response_model=List[TitleResponse])
def get_titles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TitleService(db)
    return service.get_all_titles()


@router.get("/me", response_model=List[UserTitleResponse])
def get_user_titles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TitleService(db)
    return service.get_user_titles(current_user.id)


@router.put("/activate")
def activate_title(
    body: TitleActivateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TitleService(db)
    service.activate_title(current_user.id, body.title_id)
    return {"message": "Title activated"}
