from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cultivation import CultivationProfile
from app.models.immortal import AscensionRecord, CrossRealmSettlement, ImmortalProfile

ASCENDED_REALM_KEYS = {"ascended", "n"}  # "n" is retained for legacy persisted fixtures.
MORTAL_EXP_TO_IMMORTAL_ESSENCE = 1
MORTAL_COIN_TO_IMMORTAL_STONE = 1


class AscensionService:
    def __init__(self, db: Session):
        self.db = db

    def ascend(self, user_id: UUID, request_key: str):
        request_key = (request_key or "").strip()
        if not request_key:
            raise ValueError("request_key must be non-empty")
        existing = self.db.query(AscensionRecord).filter_by(request_key=request_key).one_or_none()
        if existing:
            return existing
        profile = self.db.query(CultivationProfile).filter_by(user_id=user_id).one_or_none()
        if profile is None or profile.realm_key not in ASCENDED_REALM_KEYS:
            raise PermissionError("ASCENSION_NOT_READY")
        if self.db.query(ImmortalProfile).filter_by(user_id=user_id).one_or_none():
            raise ValueError("ASCENSION_ALREADY_RECORDED")
        immortal = ImmortalProfile(user_id=user_id)
        record = AscensionRecord(
            user_id=user_id,
            request_key=request_key,
            source_key=f"ascension:{user_id}",
        )
        self.db.add_all([immortal, record])
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.db.query(AscensionRecord).filter_by(request_key=request_key).one_or_none()
            if existing:
                return existing
            raise
        return record

    def settle_mortal_todo_after_ascension(self, user_id: UUID, source_key: str, mortal_exp: int, mortal_coins: int):
        if not self.db.query(ImmortalProfile).filter_by(user_id=user_id).one_or_none():
            raise PermissionError("IMMORTAL_PROFILE_REQUIRED")
        existing = self.db.query(CrossRealmSettlement).filter_by(user_id=user_id, source_key=source_key).one_or_none()
        if existing:
            return existing
        profile = self.db.query(ImmortalProfile).filter_by(user_id=user_id).one()
        settlement = CrossRealmSettlement(
            user_id=user_id,
            source_key=source_key,
            request_key=f"cross-realm:{user_id}:{source_key}",
            essence_delta=max(0, mortal_exp) * MORTAL_EXP_TO_IMMORTAL_ESSENCE,
            immortal_stones_delta=max(0, mortal_coins) * MORTAL_COIN_TO_IMMORTAL_STONE,
        )
        profile.essence += settlement.essence_delta
        profile.immortal_stones += settlement.immortal_stones_delta
        self.db.add(settlement)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return self.db.query(CrossRealmSettlement).filter_by(user_id=user_id, source_key=source_key).one()
        return settlement
