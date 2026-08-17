from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.cultivation import CultivationLog, CultivationProfile
from app.repositories.base import BaseRepository


class CultivationRepository(BaseRepository[CultivationProfile]):
    def __init__(self, db: Session):
        super().__init__(CultivationProfile, db)

    def get_by_user(self, user_id: UUID) -> Optional[CultivationProfile]:
        return self.db.query(CultivationProfile).filter(
            CultivationProfile.user_id == user_id
        ).first()

    def create_default(self, user_id: UUID) -> CultivationProfile:
        profile = CultivationProfile(user_id=user_id)
        self.db.add(profile)
        self.db.flush()
        return profile


class CultivationLogRepository(BaseRepository[CultivationLog]):
    def __init__(self, db: Session):
        super().__init__(CultivationLog, db)

    def get_by_user(self, user_id: UUID):
        return self.db.query(CultivationLog).filter(
            CultivationLog.user_id == user_id
        ).order_by(CultivationLog.created_at.desc()).all()
