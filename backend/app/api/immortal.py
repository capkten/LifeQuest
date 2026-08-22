from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.immortal import AscensionRequest, AscensionResponse, ImmortalActivityRequest, ImmortalOverview
from app.services.ascension import AscensionService
from app.services.immortal import ImmortalService

router = APIRouter(prefix="/api/immortal", tags=["immortal"])


@router.post("/ascend", response_model=AscensionResponse)
def ascend(payload: AscensionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return AscensionService(db).ascend(current_user.id, payload.request_key)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/overview", response_model=ImmortalOverview)
def overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return ImmortalService(db).get_overview(current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/activities/run")
def run_activity(payload: ImmortalActivityRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        overview_data = ImmortalService(db).get_overview(current_user.id)
        return {"activity_id": payload.activity_id, "request_key": payload.request_key, "overview": overview_data}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
