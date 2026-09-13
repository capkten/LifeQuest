from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def lock(self, user_id: UUID) -> None:
        dialect_name = getattr(getattr(self.db.bind, "dialect", None), "name", "")
        if str(dialect_name).lower() == "sqlite":
            # SQLite ignores FOR UPDATE. Keep the write statement to acquire
            # its database lock, but use a separate existence check instead
            # of relying on affected-row semantics for a no-op update.
            existing_id = self.db.execute(
                select(User.id).where(User.id == user_id)
            ).scalar_one_or_none()
            if existing_id is None:
                raise HTTPException(status_code=404, detail="User not found")
            self.db.execute(
                update(User).where(User.id == user_id).values(
                    id=User.id,
                    updated_at=User.updated_at,
                ).execution_options(synchronize_session=False)
            )
            return

        existing_id = self.db.execute(
            select(User.id).where(User.id == user_id).with_for_update()
        ).scalar_one_or_none()
        if existing_id is None:
            raise HTTPException(status_code=404, detail="User not found")

    def debit_coins(self, user_id: UUID, amount: int) -> None:
        if amount < 0:
            raise ValueError("amount must be non-negative")
        if amount == 0:
            return
        changed = self.db.execute(
            update(User).where(User.id == user_id, User.coins >= amount)
            .values(coins=User.coins - amount)
            .execution_options(synchronize_session=False)
        ).rowcount
        if not changed:
            raise HTTPException(status_code=400, detail="Insufficient coins")

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

    def _update_coins_no_commit(self, user: User, amount: int) -> None:
        self.db.flush()
        values = {"coins": User.coins + amount}
        if amount > 0:
            values["total_coins_earned"] = User.total_coins_earned + amount
        self.db.execute(
            update(User).where(User.id == user.id).values(**values)
        )
        self.db.refresh(user)

    def _refund_coins_no_commit(self, user: User, amount: int) -> None:
        """Restore coins without counting as earned (used for refunds)."""
        self.db.execute(update(User).where(User.id == user.id).values(coins=User.coins + amount))
        self.db.refresh(user)

    def _update_experience_no_commit(self, user: User, exp: int) -> None:
        self.db.flush()
        self.db.execute(
            update(User).where(User.id == user.id).values(
                experience=User.experience + exp
            )
        )
        self.db.refresh(user)
        while user.experience >= self._get_required_exp(user.level):
            user.experience -= self._get_required_exp(user.level)
            user.level += 1

    def _get_required_exp(self, level: int) -> int:
        return int(100 * (1.5 ** (level - 1)))
