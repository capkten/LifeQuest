import time
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models.cultivation import CultivationLog, CultivationProfile
from app.repositories.base import BaseRepository


_PROFILE_CREATE_RETRIES = 5
_PROFILE_CREATE_DELAY_SECONDS = 0.05


class CultivationRepository(BaseRepository[CultivationProfile]):
    def __init__(self, db: Session):
        super().__init__(CultivationProfile, db)

    def get_by_user(self, user_id: UUID) -> Optional[CultivationProfile]:
        return self.db.query(CultivationProfile).filter(
            CultivationProfile.user_id == user_id
        ).first()

    def create_default(self, user_id: UUID) -> CultivationProfile:
        dialect_name = (self.db.get_bind().dialect.name or "").lower()
        if dialect_name in {"sqlite", "postgresql"}:
            insert_factory = sqlite_insert if dialect_name == "sqlite" else postgresql_insert
            for attempt in range(_PROFILE_CREATE_RETRIES):
                try:
                    statement = insert_factory(CultivationProfile).values(user_id=user_id)
                    statement = statement.on_conflict_do_nothing(index_elements=["user_id"])
                    self.db.execute(statement)
                    profile = self.get_by_user(user_id)
                    if profile is not None:
                        return profile
                except OperationalError as exc:
                    if not self._is_sqlite_lock_error(exc):
                        raise
                    self.db.expire_all()
                if attempt < _PROFILE_CREATE_RETRIES - 1:
                    time.sleep(_PROFILE_CREATE_DELAY_SECONDS)
            profile = self.get_by_user(user_id)
            if profile is not None:
                return profile
            raise RuntimeError("profile upsert retry loop exhausted")
        if dialect_name in {"mysql", "mariadb"}:
            for attempt in range(_PROFILE_CREATE_RETRIES):
                try:
                    self.db.execute(mysql_insert(CultivationProfile).values(user_id=user_id).prefix_with("IGNORE"))
                    profile = self.get_by_user(user_id)
                    if profile is not None:
                        return profile
                except OperationalError as exc:
                    if not self._is_sqlite_lock_error(exc):
                        raise
                    self.db.expire_all()
                if attempt < _PROFILE_CREATE_RETRIES - 1:
                    time.sleep(_PROFILE_CREATE_DELAY_SECONDS)
            profile = self.get_by_user(user_id)
            if profile is not None:
                return profile
            raise RuntimeError("profile upsert retry loop exhausted")

        for attempt in range(_PROFILE_CREATE_RETRIES):
            profile = self.get_by_user(user_id)
            if profile is not None:
                return profile
            try:
                with self.db.begin_nested():
                    profile = CultivationProfile(user_id=user_id)
                    self.db.add(profile)
                    self.db.flush()
                return profile
            except IntegrityError:
                self.db.expire_all()
                profile = self.get_by_user(user_id)
                if profile is not None:
                    return profile
            except OperationalError as exc:
                if not self._is_sqlite_lock_error(exc):
                    raise
                self.db.expire_all()
            if attempt < _PROFILE_CREATE_RETRIES - 1:
                time.sleep(_PROFILE_CREATE_DELAY_SECONDS)
        profile = self.get_by_user(user_id)
        if profile is not None:
            return profile
        raise RuntimeError("profile creation retry loop exhausted")

    @staticmethod
    def _is_sqlite_lock_error(exc: OperationalError) -> bool:
        error_text = str(getattr(exc, "orig", exc)).lower()
        return "database" in error_text and "locked" in error_text


class CultivationLogRepository(BaseRepository[CultivationLog]):
    def __init__(self, db: Session):
        super().__init__(CultivationLog, db)

    def get_by_user(self, user_id: UUID):
        return self.db.query(CultivationLog).filter(
            CultivationLog.user_id == user_id
        ).order_by(CultivationLog.created_at.desc()).all()
