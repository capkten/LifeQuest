from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.coin_transaction import CoinTransaction
from app.repositories.base import BaseRepository


class CoinTransactionRepository(BaseRepository[CoinTransaction]):
    def __init__(self, db: Session):
        super().__init__(CoinTransaction, db)

    def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        coin_type: Optional[str] = None,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[CoinTransaction]:
        query = self.db.query(CoinTransaction).filter(CoinTransaction.user_id == user_id)
        if coin_type:
            query = query.filter(CoinTransaction.type == coin_type)
        if source:
            query = query.filter(CoinTransaction.source == source)
        if start_date:
            query = query.filter(CoinTransaction.created_at >= start_date)
        if end_date:
            query = query.filter(CoinTransaction.created_at <= end_date)
        return (
            query.order_by(CoinTransaction.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_totals(self, user_id: UUID) -> dict:
        result = (
            self.db.query(
                CoinTransaction.type,
                func.sum(CoinTransaction.amount).label("total"),
            )
            .filter(CoinTransaction.user_id == user_id)
            .group_by(CoinTransaction.type)
            .all()
        )
        totals = {"total_earned": 0, "total_spent": 0}
        for row in result:
            if row.type == "earn":
                totals["total_earned"] = row.total or 0
            elif row.type == "spend":
                totals["total_spent"] = row.total or 0
        return totals

    def count_by_user(self, user_id: UUID) -> int:
        return (
            self.db.query(CoinTransaction)
            .filter(CoinTransaction.user_id == user_id)
            .count()
        )

    def create_transaction(
        self,
        user_id: UUID,
        amount: int,
        coin_type: str,
        source: str,
        source_id: Optional[str] = None,
        description: str = "",
    ) -> CoinTransaction:
        data = {
            "user_id": user_id,
            "amount": amount,
            "type": coin_type,
            "source": source,
            "source_id": source_id,
            "description": description,
        }
        return self.create(data)
