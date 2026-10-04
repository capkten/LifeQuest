from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.cultivation_retreat import (
    EncounterCatalogItem,
    RetreatCompleteRequest,
    RetreatResponse,
    RetreatStartRequest,
)
from app.services.cultivation_retreat import CultivationRetreatService

router = APIRouter(prefix="/api/cultivation/retreat", tags=["cultivation_retreat"])


@router.post("/start", response_model=RetreatResponse)
def start_retreat(
    req: RetreatStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RetreatResponse:
    retreat = CultivationRetreatService.start_retreat(
        db=db,
        user_id=current_user.id,
        target_duration=req.target_duration,
        todo_id=req.todo_id,
    )
    return retreat


@router.get("/active", response_model=Optional[RetreatResponse])
def get_active_retreat(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Optional[RetreatResponse]:
    return CultivationRetreatService.get_active_retreat(db=db, user_id=current_user.id)


@router.post("/{retreat_id}/complete", response_model=RetreatResponse)
def complete_retreat(
    retreat_id: UUID,
    req: RetreatCompleteRequest = RetreatCompleteRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RetreatResponse:
    retreat = CultivationRetreatService.complete_retreat(
        db=db,
        user_id=current_user.id,
        retreat_id=retreat_id,
        mark_todo_complete=req.mark_todo_complete,
    )
    return retreat


@router.post("/{retreat_id}/abort", response_model=RetreatResponse)
def abort_retreat(
    retreat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RetreatResponse:
    return CultivationRetreatService.abort_retreat(
        db=db,
        user_id=current_user.id,
        retreat_id=retreat_id,
    )


@router.get("/history", response_model=List[RetreatResponse])
def get_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RetreatResponse]:
    return CultivationRetreatService.get_history(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )


@router.get("/encounters/catalog", response_model=List[EncounterCatalogItem])
def get_catalog(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[EncounterCatalogItem]:
    return CultivationRetreatService.get_catalog(
        db=db,
        user_id=current_user.id,
    )
