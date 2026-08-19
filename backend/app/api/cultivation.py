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
    NpcMeetRequest,
    NpcRelationshipResponse,
    NpcSummary,
    SectMembershipResponse,
    SectSummary,
    TechniqueLibraryResponse,
    TechniqueSlotPurchaseRequest,
    LearnedTechniqueResponse,
    TribulationAttemptRequest,
    TribulationPreview,
    TribulationResult,
    WorldResponse,
    WorldNodeResponse,
    SectAccessResponse,
    HiddenSectSummary,
    TrialObjectiveRequest,
)
from app.services.cultivation import CultivationService

router = APIRouter(prefix="/api/cultivation", tags=["cultivation"])


def _service(db: Session) -> CultivationService:
    return CultivationService(db)


@router.get("/overview", response_model=CultivationOverview)
def overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CultivationOverview:
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
) -> List[SectSummary]:
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


@router.post("/sects/{sect_id}/messenger/contact", response_model=SectSummary)
def contact_sect_messenger(sect_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _service(db).contact_sect_messenger(current_user.id, sect_id)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sects/{sect_id}/trial/complete", response_model=SectSummary)
def complete_sect_trial(sect_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _service(db).complete_sect_trial(current_user.id, sect_id)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sects/{sect_id}/access", response_model=SectAccessResponse)
def sect_access(sect_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _service(db).get_sect_access(current_user.id, sect_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sects/{sect_id}/trial/objectives/{objective_key}", response_model=SectAccessResponse)
def update_trial_objective(
    sect_id: str,
    objective_key: str,
    payload: TrialObjectiveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return _service(db).update_trial_objective(
            current_user.id, sect_id, objective_key, payload.completed
        )
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sects/hidden/evaluate", response_model=List[HiddenSectSummary])
def evaluate_hidden_sects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _service(db).evaluate_hidden_sects(current_user.id)


@router.post("/sects/leave")
def leave_sect(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _service(db).leave_sect(current_user.id)


@router.post("/world/{node_key}/complete", response_model=WorldNodeResponse)
def complete_world_node(node_key: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _service(db).complete_world_node(current_user.id, node_key)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/techniques", response_model=TechniqueLibraryResponse)
def techniques(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TechniqueLibraryResponse:
    return _service(db).get_techniques(current_user.id)


@router.post("/techniques/{technique_key}/learn", response_model=LearnedTechniqueResponse)
def learn_technique(technique_key: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _service(db).learn_technique(current_user.id, technique_key)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
def npcs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> NpcRelationshipResponse:
    try:
        return _service(db).get_npcs(current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/npcs/meet", response_model=NpcSummary)
def meet_npc(payload: NpcMeetRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _service(db).meet_npc(current_user.id, payload.sect_key, payload.population_index)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/tribulation/preview", response_model=TribulationPreview)
def tribulation_preview(
    pill_count: int = Query(default=0, ge=0, le=15),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _service(db).get_tribulation_preview(current_user.id, pill_count)


@router.post("/tribulation/attempt", response_model=TribulationResult)
def attempt_tribulation(payload: TribulationAttemptRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return _service(db).attempt_tribulation(current_user.id, payload.pill_count)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
