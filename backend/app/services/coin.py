from datetime import datetime
from copy import copy
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.coin_transaction import CoinTransactionRepository
from app.services.content_catalog import TODO_SOURCE_PREFIXES, source_label


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
        return f"{source_label(source)}奖励"

    @staticmethod
    def _is_proven_todo_system_transaction(transaction) -> bool:
        source_value = getattr(transaction.source, "value", transaction.source)
        transaction_type = getattr(transaction.type, "value", transaction.type)
        source_id = transaction.source_id or ""
        legacy_prefix = f"todo:{source_value}:"
        compact_prefix = f"{TODO_SOURCE_PREFIXES.get(source_value, '')}:"
        return (
            transaction_type == "earn"
            and source_value in {"task", "habit", "goal"}
            and (
                (
                    source_id.startswith(legacy_prefix)
                    and bool(source_id[len(legacy_prefix):])
                )
                or (
                    source_id.startswith(compact_prefix)
                    and bool(source_id[len(compact_prefix):])
                )
            )
        )

    @classmethod
    def _localized_transaction(cls, transaction):
        source_value = getattr(transaction.source, "value", transaction.source)
        if (
            cls._is_proven_todo_system_transaction(transaction)
            and transaction.description == f"Reward from {source_value}"
        ):
            localized = copy(transaction)
            localized.description = cls._default_description(source_value)
            return localized
        return transaction
