from datetime import datetime
from copy import copy
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
        transactions = [self._localized_transaction(transaction) for transaction in transactions]
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
        if not description:
            description = self._default_description(source)
        return self.coin_repo.create_transaction(
            user_id=user_id,
            amount=amount,
            coin_type=coin_type,
            source=source,
            source_id=source_id,
            description=description,
        )

    @staticmethod
    def _default_description(source: str) -> str:
        source_value = getattr(source, "value", source)
        source_labels = {
            "task": "任务",
            "habit": "习惯",
            "goal": "目标",
            "checkin": "签到",
            "shop": "商店",
            "achievement": "成就",
            "other": "其他",
        }
        return f"{source_labels.get(source_value, source_value)}奖励"

    @classmethod
    def _localized_transaction(cls, transaction):
        source_value = getattr(transaction.source, "value", transaction.source)
        if transaction.description == f"Reward from {source_value}":
            localized = copy(transaction)
            localized.description = cls._default_description(source_value)
            return localized
        return transaction
