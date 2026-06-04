from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.coin_transaction import CoinTransactionRepository


class CoinService:
    def __init__(self, db: Session):
        self.db = db
        self.coin_repo = CoinTransactionRepository(db)

    def get_history(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        coin_type: Optional[str] = None,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        transactions = self.coin_repo.get_by_user(
            user_id,
            skip=skip,
            limit=limit,
            coin_type=coin_type,
            source=source,
            start_date=start_date,
            end_date=end_date,
        )
        totals = self.coin_repo.get_totals(user_id)
        count = self.coin_repo.count_by_user(user_id)
        return {
            "transactions": transactions,
            "total_earned": totals["total_earned"],
            "total_spent": totals["total_spent"],
            "count": count,
        }

    def get_totals(self, user_id: UUID) -> dict:
        return self.coin_repo.get_totals(user_id)

    def record_transaction(
        self,
        user_id: UUID,
        amount: int,
        coin_type: str,
        source: str,
        source_id: Optional[str] = None,
        description: str = "",
    ):
        return self.coin_repo.create_transaction(
            user_id=user_id,
            amount=amount,
            coin_type=coin_type,
            source=source,
            source_id=source_id,
            description=description,
        )
