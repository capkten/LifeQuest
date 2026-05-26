from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.achievement import Achievement, UserAchievement
from app.repositories.base import BaseRepository


class AchievementRepository(BaseRepository[Achievement]):
    def __init__(self, db: Session):
        super().__init__(Achievement, db)

    def get_all_achievements(self) -> List[Achievement]:
        return self.db.query(Achievement).all()

    def get_by_name(self, name: str) -> Optional[Achievement]:
        return self.db.query(Achievement).filter(Achievement.name == name).first()


class UserAchievementRepository(BaseRepository[UserAchievement]):
    def __init__(self, db: Session):
        super().__init__(UserAchievement, db)

    def get_by_user(self, user_id: UUID) -> List[UserAchievement]:
        return (
            self.db.query(UserAchievement)
            .filter(UserAchievement.user_id == user_id)
            .all()
        )

    def get_by_user_and_achievement(
        self, user_id: UUID, achievement_id: UUID
    ) -> Optional[UserAchievement]:
        return (
            self.db.query(UserAchievement)
            .filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id,
            )
            .first()
        )
