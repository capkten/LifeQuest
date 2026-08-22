from uuid import UUID

from sqlalchemy.orm import Session

from app.models.immortal import ImmortalProfile


class ImmortalService:
    def __init__(self, db: Session):
        self.db = db

    def get_overview(self, user_id: UUID):
        profile = self.db.query(ImmortalProfile).filter_by(user_id=user_id).one_or_none()
        if profile is None:
            raise PermissionError("IMMORTAL_PROFILE_REQUIRED")
        return {
            "user_id": user_id,
            "realm_key": profile.realm_key,
            "stage": profile.stage,
            "essence": profile.essence,
            "immortal_stones": profile.immortal_stones,
            "regions": [],
            "officials": [],
            "activities": [],
            "stage_goals": [],
        }
