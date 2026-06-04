from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.title import Title, UserTitle
from app.repositories.base import BaseRepository


class TitleRepository(BaseRepository[Title]):
    def __init__(self, db: Session):
        super().__init__(Title, db)

    def get_all_titles(self) -> List[Title]:
        return self.db.query(Title).all()

    def get_by_name(self, name: str) -> Optional[Title]:
        return self.db.query(Title).filter(Title.name == name).first()

    def get_by_condition(self, condition_type: str, condition_value: int) -> List[Title]:
        return (
            self.db.query(Title)
            .filter(
                Title.unlock_condition_type == condition_type,
                Title.unlock_condition_value <= condition_value,
            )
            .all()
        )


class UserTitleRepository(BaseRepository[UserTitle]):
    def __init__(self, db: Session):
        super().__init__(UserTitle, db)

    def get_by_user(self, user_id: UUID) -> List[UserTitle]:
        return (
            self.db.query(UserTitle)
            .filter(UserTitle.user_id == user_id)
            .all()
        )

    def get_by_user_and_title(self, user_id: UUID, title_id: int) -> Optional[UserTitle]:
        return (
            self.db.query(UserTitle)
            .filter(UserTitle.user_id == user_id, UserTitle.title_id == title_id)
            .first()
        )
