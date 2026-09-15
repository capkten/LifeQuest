from datetime import date
from decimal import Decimal
from typing import List
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.finance_transaction import FinanceTransaction, FinanceTransactionType
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

    def get_spent_amount(
        self, budget: Budget, period_start: date, period_end: date,
    ) -> Decimal:
        effective_start = max(
            period_start,
            budget.start_date if budget.start_date is not None else period_start,
        )
        if effective_start >= period_end:
            return Decimal("0")

        query = self.db.query(
            func.coalesce(func.sum(FinanceTransaction.amount), Decimal("0"))
        ).filter(
            FinanceTransaction.user_id == budget.user_id,
            FinanceTransaction.type == FinanceTransactionType.EXPENSE.value,
            FinanceTransaction.date >= effective_start,
            FinanceTransaction.date < period_end,
        )
        if budget.category_id:
            query = query.filter(FinanceTransaction.category_id == budget.category_id)

        spent_amount = query.scalar()
        return spent_amount if isinstance(spent_amount, Decimal) else Decimal(str(spent_amount or 0))
