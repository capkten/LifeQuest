from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.cultivation import (
    CultivationOverview,
    LoadoutRequest,
    NpcRelationshipResponse,
    SectMembershipResponse,
    SectSummary,
    TechniqueLibraryResponse,
    TechniqueSlotPurchaseRequest,
    TribulationAttemptRequest,
    TribulationPreview,
    TribulationResult,
    WorldResponse,
)
from app.services.cultivation import CultivationService

router = APIRouter(prefix="/api/cultivation", tags=["cultivation"])


def _service(db: Session) -> CultivationService:
    return CultivationService(db)


@router.get("/overview", response_model=CultivationOverview)
def overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _service(db).get_overview(current_user.id)


@router.get("/world", response_model=WorldResponse)
def world(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _service(db).get_world(current_user.id)


@router.get("/sects", response_model=List[SectSummary])
def sects(
    star: Optional[int] = Query(default=None, ge=1, le=9),
    kind: Optional[str] = Query(default=None),
    task_preference: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _service(db).get_sects(current_user.id, star=star, kind=kind, task_preference=task_preference)


@router.post("/sects/{sect_id}/join", response_model=SectMembershipResponse)
def join_sect(sect_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _service(db).join_sect(current_user.id, sect_id)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/sects/leave")
def leave_sect(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _service(db).leave_sect(current_user.id)


@router.get("/techniques", response_model=TechniqueLibraryResponse)
def techniques(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _service(db).get_techniques(current_user.id)


@router.post("/technique-slots/purchase")
def purchase_slot(payload: TechniqueSlotPurchaseRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _service(db).purchase_slot(current_user.id, payload.slot_type)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/loadout", response_model=TechniqueLibraryResponse)
def update_loadout(payload: LoadoutRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _service(db).update_loadout(current_user.id, payload.loadout)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/npcs", response_model=NpcRelationshipResponse)
def npcs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _service(db).get_npcs(current_user.id)


@router.get("/tribulation/preview", response_model=TribulationPreview)
def tribulation_preview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _service(db).get_tribulation_preview(current_user.id)


@router.post("/tribulation/attempt", response_model=TribulationResult)
def attempt_tribulation(payload: TribulationAttemptRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _service(db).attempt_tribulation(current_user.id, payload.pill_count)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
