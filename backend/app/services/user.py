from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.auth import get_password_hash, verify_password


class UserService:
    def __init__(self, db: Session):
        self.repository = UserRepository(db)

    def create_user(self, user_in: UserCreate) -> User:
        # Check if username exists
        if self.repository.get_by_username(user_in.username):
            raise ValueError("Username already exists")
        # Check if email exists
        if self.repository.get_by_email(user_in.email):
            raise ValueError("Email already exists")

        user_data = user_in.model_dump()
        user_data["password_hash"] = get_password_hash(user_data.pop("password"))
        return self.repository.create(user_data)

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.repository.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        return self.repository.get_by_id(user_id)

    def update_user(self, user: User, user_in: UserUpdate) -> User:
        update_data = user_in.model_dump(exclude_unset=True)
        return self.repository.update(user, update_data)

    def add_experience(self, user: User, exp: int) -> User:
        return self.repository.update_experience(user, exp)

    def add_coins(self, user: User, amount: int) -> User:
        return self.repository.update_coins(user, amount)

    def deduct_coins(self, user: User, amount: int) -> User:
        if user.coins < amount:
            raise ValueError("Insufficient coins")
        return self.repository.update_coins(user, -amount)
