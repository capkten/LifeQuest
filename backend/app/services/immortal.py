from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from sqlalchemy.exc import IntegrityError

from app.models.immortal import ImmortalActivityRecord, ImmortalOfficialCommission, ImmortalProfile, ImmortalStageAdvance

ACTIVITIES = {
    "daily-cultivation": {"label": "每日修行", "essence": 5, "stones": 2, "min_stage": 1, "cooldown_seconds": 0},
    "celestial-meditation": {"label": "天界冥想", "essence": 12, "stones": 5, "min_stage": 2, "cooldown_seconds": 86400},
}

OFFICIALS = {"gatekeeper": {"name": "天门执事", "essence": 3, "stones": 1, "min_stage": 1}}


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
            "regions": [{"key": "celestial-gate", "name": "天门境", "unlocked": True}],
            "officials": [
                {"key": key, "name": value["name"], "unlocked": profile.stage >= value["min_stage"]}
                for key, value in OFFICIALS.items()
            ],
            "activities": [
                {"id": key, "label": value["label"], "unlocked": profile.stage >= value["min_stage"], "cooldown_seconds": value["cooldown_seconds"]}
                for key, value in ACTIVITIES.items()
            ],
            "stage_goals": [{"key": "essence", "required": profile.stage * 50, "current": profile.essence}],
        }

    def run_activity(self, user_id: UUID, activity_id: str, request_key: str):
        activity = ACTIVITIES.get(activity_id)
        if activity is None:
            raise LookupError("IMMORTAL_ACTIVITY_NOT_FOUND")
        profile = self.db.query(ImmortalProfile).filter_by(user_id=user_id).one_or_none()
        if profile is None:
            raise PermissionError("IMMORTAL_PROFILE_REQUIRED")
        if profile.stage < activity["min_stage"]:
            raise PermissionError("IMMORTAL_ACTIVITY_LOCKED")
        request_key = (request_key or "").strip()
        if not request_key:
            raise ValueError("request_key must be non-empty")
        existing = self.db.query(ImmortalActivityRecord).filter_by(user_id=user_id, request_key=request_key).one_or_none()
        if existing:
            return self._activity_result(existing, profile)
        if activity["cooldown_seconds"]:
            latest = self.db.query(ImmortalActivityRecord).filter_by(user_id=user_id, activity_id=activity_id).order_by(ImmortalActivityRecord.created_at.desc()).first()
            if latest and self._seconds_since(latest.created_at) < activity["cooldown_seconds"]:
                raise PermissionError("IMMORTAL_ACTIVITY_COOLDOWN")
        record = ImmortalActivityRecord(
            user_id=user_id, activity_id=activity_id, request_key=request_key,
            essence_delta=activity["essence"], immortal_stones_delta=activity["stones"],
        )
        profile.essence += record.essence_delta
        profile.immortal_stones += record.immortal_stones_delta
        self.db.add(record)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            record = self.db.query(ImmortalActivityRecord).filter_by(user_id=user_id, request_key=request_key).one()
            profile = self.db.query(ImmortalProfile).filter_by(user_id=user_id).one()
        return self._activity_result(record, profile)

    def advance_stage(self, user_id: UUID, request_key: str):
        request_key = (request_key or "").strip()
        if not request_key:
            raise ValueError("request_key must be non-empty")
        profile = self.db.query(ImmortalProfile).filter_by(user_id=user_id).one_or_none()
        if profile is None:
            raise PermissionError("IMMORTAL_PROFILE_REQUIRED")
        existing = self.db.query(ImmortalStageAdvance).filter_by(user_id=user_id, request_key=request_key).one_or_none()
        if existing:
            return {"stage": existing.stage, "advanced": True, "required_essence": existing.stage * 50}
        required = profile.stage * 50
        if profile.essence < required:
            raise PermissionError(f"IMMORTAL_STAGE_GOAL_REQUIRED:{required}:{profile.essence}")
        profile.stage += 1
        self.db.add(ImmortalStageAdvance(user_id=user_id, request_key=request_key, stage=profile.stage))
        self.db.commit()
        return {"stage": profile.stage, "advanced": True, "required_essence": profile.stage * 50}

    def commission(self, user_id: UUID, official_key: str, request_key: str):
        official = OFFICIALS.get(official_key)
        if official is None:
            raise LookupError("IMMORTAL_OFFICIAL_NOT_FOUND")
        profile = self.db.query(ImmortalProfile).filter_by(user_id=user_id).one_or_none()
        if profile is None:
            raise PermissionError("IMMORTAL_PROFILE_REQUIRED")
        if profile.stage < official["min_stage"]:
            raise PermissionError("IMMORTAL_OFFICIAL_LOCKED")
        request_key = (request_key or "").strip()
        if not request_key:
            raise ValueError("request_key must be non-empty")
        existing = self.db.query(ImmortalOfficialCommission).filter_by(user_id=user_id, official_key=official_key, request_key=request_key).one_or_none()
        if existing:
            return self._commission_result(existing, profile)
        record = ImmortalOfficialCommission(user_id=user_id, official_key=official_key, request_key=request_key, essence_delta=official["essence"], immortal_stones_delta=official["stones"])
        profile.essence += record.essence_delta
        profile.immortal_stones += record.immortal_stones_delta
        self.db.add(record)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            record = self.db.query(ImmortalOfficialCommission).filter_by(user_id=user_id, official_key=official_key, request_key=request_key).one()
            profile = self.db.query(ImmortalProfile).filter_by(user_id=user_id).one()
        return self._commission_result(record, profile)

    @staticmethod
    def _seconds_since(created_at):
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - created_at).total_seconds())

    @staticmethod
    def _activity_result(record, profile):
        return {
            "activity_id": record.activity_id, "request_key": record.request_key,
            "essence_delta": record.essence_delta, "immortal_stones_delta": record.immortal_stones_delta,
            "essence": profile.essence, "immortal_stones": profile.immortal_stones,
        }

    @staticmethod
    def _commission_result(record, profile):
        return {
            "official_key": record.official_key, "request_key": record.request_key,
            "essence_delta": record.essence_delta, "immortal_stones_delta": record.immortal_stones_delta,
            "essence": profile.essence, "immortal_stones": profile.immortal_stones,
        }
