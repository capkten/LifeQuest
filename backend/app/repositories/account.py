from typing import List
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    def __init__(self, db: Session):
        super().__init__(Account, db)

    def get_by_user(self, user_id: UUID, active_only: bool = True) -> List[Account]:
        query = self.db.query(Account).filter(Account.user_id == user_id)
        if active_only:
            query = query.filter(Account.is_active == True)
        return query.order_by(Account.sort_order).all()

    def get_total_balance(self, user_id: UUID) -> float:
        result = self.db.query(func.coalesce(func.sum(Account.balance), 0.0)).filter(
            Account.user_id == user_id,
            Account.is_active == True,
        ).scalar()
        return float(result)
