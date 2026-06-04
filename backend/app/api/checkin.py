from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.checkin import CheckinResponse, CheckinStatusResponse
from app.services.checkin import CheckinService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/checkin", tags=["checkin"])


@router.post("", response_model=CheckinResponse)
def checkin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CheckinService(db)
    return service.checkin(current_user.id)


@router.get("/status", response_model=CheckinStatusResponse)
def get_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CheckinService(db)
    return service.get_status(current_user.id)
