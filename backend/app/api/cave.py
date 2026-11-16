from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.cave import CaveService
from app.schemas.cave import CaveStartRequest, CaveOpenEvent, CaveSignRequest, CaveSelectRequest, CaveSettleRequest, CaveAcknowledgeRequest, CaveOnboardingCompleteRequest

router = APIRouter(prefix='/api/cave', tags=['cave'])


@router.get('', include_in_schema=False)
@router.get('/today')
def get_cave(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CaveService(db).get_cave(current_user.id)


@router.post('/onboarding/skip')
def skip_onboarding(data: CaveAcknowledgeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.cave_onboarding import CaveOnboardingService
    return CaveOnboardingService(db).skip(current_user.id, data.request_id)


@router.post('/onboarding/complete')
def complete_onboarding(data: CaveOnboardingCompleteRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.cave_onboarding import CaveOnboardingService
    return CaveOnboardingService(db).complete(current_user.id, data.request_id, data.session_id)


@router.post('/sessions')
def start_session(data: CaveStartRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CaveService(db).start_session(current_user.id, data)


@router.get('/sessions/{session_id}')
def read_session(session_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CaveService(db).read_session(current_user.id, session_id)


@router.post('/sessions/{session_id}/settle')
def settle_session(session_id: UUID, data: CaveSettleRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CaveService(db).settle_session(current_user.id, session_id, data)


@router.post('/sessions/{session_id}/acknowledge')
def acknowledge_return(session_id: UUID, data: CaveAcknowledgeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CaveService(db).acknowledge_return(current_user.id, session_id, data)


@router.post('/signs/reroll')
def reroll(data: CaveSignRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CaveService(db).reroll(current_user.id, data)


@router.post('/signs/select')
def select_sign(data: CaveSelectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CaveService(db).select_sign(current_user.id, data)


@router.get('/events')
def list_events(session_id: UUID | None = None, limit: int = Query(default=50, ge=1, le=100),
                current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CaveService(db).list_events(current_user.id, session_id, limit)


@router.get('/letters')
def get_letters(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.cave_letters import CaveLetterService
    return CaveLetterService(db).get_letters(current_user.id)


@router.get('/letters/{letter_id}')
def get_letter(letter_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.cave_letters import CaveLetterService
    return CaveLetterService(db).get_letter(current_user.id, letter_id)


@router.post('/letters/{letter_id}/read')
def read_letter(letter_id: UUID, data: CaveAcknowledgeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.cave_letters import CaveLetterService
    return CaveLetterService(db).act(current_user.id, letter_id, 'read', data.request_id)


@router.post('/letters/{letter_id}/accept')
def accept_letter(letter_id: UUID, data: CaveAcknowledgeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.cave_letters import CaveLetterService
    return CaveLetterService(db).act(current_user.id, letter_id, 'accept', data.request_id)


@router.post('/letters/{letter_id}/decline')
def decline_letter(letter_id: UUID, data: CaveAcknowledgeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.cave_letters import CaveLetterService
    return CaveLetterService(db).act(current_user.id, letter_id, 'decline', data.request_id)


@router.post('/letters/{letter_id}/claim')
def claim_letter(letter_id: UUID, data: CaveAcknowledgeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.cave_letters import CaveLetterService
    return CaveLetterService(db).act(current_user.id, letter_id, 'claim', data.request_id)


@router.get('/growth')
def get_growth(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.cave_growth import CaveGrowthService
    return CaveGrowthService(db).get_growth(current_user.id)


@router.get('/codex')
def get_codex(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.cave_growth import CaveGrowthService
    return CaveGrowthService(db).get_codex(current_user.id)


@router.get('/companions')
def get_companions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.cave_companions import CaveCompanionService
    return CaveCompanionService(db).get_companions(current_user.id)


@router.post('/companions/{key}/activate')
def activate_companion(key: str, data: CaveAcknowledgeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.cave_companions import CaveCompanionService
    return CaveCompanionService(db).activate(current_user.id, key, data.request_id)


@router.post('/events')
def record_open(data: CaveOpenEvent, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CaveService(db).record_open(current_user.id, data)
