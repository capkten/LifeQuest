from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.title import Title, UserTitle
from app.repositories.title import TitleRepository, UserTitleRepository
from app.repositories.user import UserRepository

SEED_TITLES = [
    {"name": "初学者", "description": "刚刚踏上冒险之路", "unlock_condition_type": "level", "unlock_condition_value": 1},
    {"name": "冒险者", "description": "已经积累了一些经验", "unlock_condition_type": "level", "unlock_condition_value": 5},
    {"name": "探索者", "description": "不断探索未知的领域", "unlock_condition_type": "level", "unlock_condition_value": 10},
    {"name": "勇者", "description": "无畏的勇者", "unlock_condition_type": "level", "unlock_condition_value": 20},
    {"name": "传奇", "description": "传奇般的存在", "unlock_condition_type": "level", "unlock_condition_value": 50},
    {"name": "习惯大师", "description": "坚持就是胜利", "unlock_condition_type": "habit_streak", "unlock_condition_value": 30},
    {"name": "知识守护者", "description": "笔耕不辍", "unlock_condition_type": "note_count", "unlock_condition_value": 50},
    {"name": "精打细算", "description": "理财达人", "unlock_condition_type": "transaction_count", "unlock_condition_value": 100},
]


class TitleService:
    def __init__(self, db: Session):
        self.db = db
        self.title_repo = TitleRepository(db)
        self.user_title_repo = UserTitleRepository(db)
        self.user_repo = UserRepository(db)

    def seed_titles(self):
        for data in SEED_TITLES:
            existing = self.title_repo.get_by_name(data["name"])
            if not existing:
                self.title_repo.create(data)

    def check_and_unlock(self, user_id: UUID, condition_type: str, current_value: int) -> List[Title]:
        """Check all titles of the given condition_type and unlock any
        that the user qualifies for but hasn't earned yet.

        Returns a list of newly unlocked Title objects.
        """
        titles = self.title_repo.get_by_condition(condition_type, current_value)
        unlocked = []
        for title in titles:
            existing = self.user_title_repo.get_by_user_and_title(user_id, title.id)
            if not existing:
                self.user_title_repo.create({
                    "user_id": user_id,
                    "title_id": title.id,
                })
                unlocked.append(title)
        return unlocked

    def get_all_titles(self) -> List[Title]:
        return self.title_repo.get_all_titles()

    def get_user_titles(self, user_id: UUID) -> List[UserTitle]:
        return self.user_title_repo.get_by_user(user_id)

    def activate_title(self, user_id: UUID, title_id: int) -> None:
        user_title = self.user_title_repo.get_by_user_and_title(user_id, title_id)
        if not user_title:
            raise HTTPException(status_code=404, detail="Title not unlocked")
        title = self.title_repo.get_by_id(title_id)
        if not title:
            raise HTTPException(status_code=404, detail="Title not found")
        user = self.user_repo.get_by_id(user_id)
        if user:
            user.title = title.name
            self.db.commit()

    def get_active_title(self, user_id: UUID) -> str:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user.title or "初学者"
