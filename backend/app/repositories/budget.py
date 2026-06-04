from datetime import date
from typing import List
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.finance_transaction import FinanceTransaction
from app.repositories.base import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    def __init__(self, db: Session):
        super().__init__(Budget, db)

    def get_by_user(self, user_id: UUID) -> List[Budget]:
        return (
            self.db.query(Budget)
            .filter(Budget.user_id == user_id)
            .order_by(Budget.created_at.desc())
            .all()
        )

    def get_spent_amount(self, budget: Budget, year: int, month: int) -> float:
        from datetime import date as date_type

        start = date_type(year, month, 1)
        if month == 12:
            end = date_type(year + 1, 1, 1)
        else:
            end = date_type(year, month + 1, 1)

        query = self.db.query(
            func.coalesce(func.sum(FinanceTransaction.amount), 0.0)
        ).filter(
            FinanceTransaction.user_id == budget.user_id,
            FinanceTransaction.type == "expense",
            FinanceTransaction.date >= start,
            FinanceTransaction.date < end,
        )
        if budget.category_id:
            query = query.filter(FinanceTransaction.category_id == budget.category_id)

        return float(query.scalar() or 0.0)
