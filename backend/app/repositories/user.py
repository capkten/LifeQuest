from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def update_experience(self, user: User, exp: int) -> User:
        user.experience += exp
        # Check for level up
        while user.experience >= self._get_required_exp(user.level):
            user.experience -= self._get_required_exp(user.level)
            user.level += 1
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_coins(self, user: User, amount: int) -> User:
        user.coins += amount
        self.db.commit()
        self.db.refresh(user)
        return user

    def _get_required_exp(self, level: int) -> int:
        return int(100 * (1.5 ** (level - 1)))
