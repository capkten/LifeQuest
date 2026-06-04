from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.checkin import DailyCheckin
from app.repositories.base import BaseRepository


class CheckinRepository(BaseRepository[DailyCheckin]):
    def __init__(self, db: Session):
        super().__init__(DailyCheckin, db)

    def get_by_user_and_date(self, user_id: UUID, checkin_date: date) -> Optional[DailyCheckin]:
        return (
            self.db.query(DailyCheckin)
            .filter(DailyCheckin.user_id == user_id, DailyCheckin.checkin_date == checkin_date)
            .first()
        )

    def get_latest_by_user(self, user_id: UUID) -> Optional[DailyCheckin]:
        return (
            self.db.query(DailyCheckin)
            .filter(DailyCheckin.user_id == user_id)
            .order_by(DailyCheckin.checkin_date.desc())
            .first()
        )

    def get_checkin_count(self, user_id: UUID) -> int:
        return (
            self.db.query(DailyCheckin)
            .filter(DailyCheckin.user_id == user_id)
            .count()
        )
