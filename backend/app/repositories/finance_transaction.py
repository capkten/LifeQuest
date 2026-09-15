from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.finance_category import FinanceCategory
from app.models.finance_transaction import FinanceTransaction
from app.repositories.base import BaseRepository


class FinanceTransactionRepository(BaseRepository[FinanceTransaction]):
    def __init__(self, db: Session):
        super().__init__(FinanceTransaction, db)

    def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        account_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[FinanceTransaction]:
        query = self.db.query(FinanceTransaction).filter(
            FinanceTransaction.user_id == user_id
        )
        if account_id:
            query = query.filter(FinanceTransaction.account_id == account_id)
        if category_id:
            query = query.filter(FinanceTransaction.category_id == category_id)
        if type:
            query = query.filter(FinanceTransaction.type == type)
        if start_date:
            query = query.filter(FinanceTransaction.date >= start_date)
        if end_date:
            query = query.filter(FinanceTransaction.date <= end_date)
        return (
            query.order_by(FinanceTransaction.date.desc(), FinanceTransaction.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_month_summary(self, user_id: UUID, year: int, month: int) -> dict:
        from datetime import date as date_type

        start = date_type(year, month, 1)
        if month == 12:
            end = date_type(year + 1, 1, 1)
        else:
            end = date_type(year, month + 1, 1)

        results = (
            self.db.query(
                FinanceTransaction.type,
                func.sum(FinanceTransaction.amount).label("total"),
            )
            .filter(
                FinanceTransaction.user_id == user_id,
                FinanceTransaction.date >= start,
                FinanceTransaction.date < end,
            )
            .group_by(FinanceTransaction.type)
            .all()
        )
        summary = {"income": 0.0, "expense": 0.0}
        for row in results:
            if row.type == "income":
                summary["income"] = float(row.total or 0)
            elif row.type == "expense":
                summary["expense"] = float(row.total or 0)
        return summary

    def count_by_user(
        self,
        user_id: UUID,
        account_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> int:
        query = self.db.query(FinanceTransaction).filter(
            FinanceTransaction.user_id == user_id
        )
        if account_id:
            query = query.filter(FinanceTransaction.account_id == account_id)
        if category_id:
            query = query.filter(FinanceTransaction.category_id == category_id)
        if type:
            query = query.filter(FinanceTransaction.type == type)
        if start_date:
            query = query.filter(FinanceTransaction.date >= start_date)
        if end_date:
            query = query.filter(FinanceTransaction.date <= end_date)
        return query.count()

    def get_with_names(self, transaction_id: UUID, user_id: UUID):
        return (
            self.db.query(
                FinanceTransaction,
                Account.name.label("account_name"),
                FinanceCategory.name.label("category_name"),
            )
            .outerjoin(
                Account,
                and_(
                    Account.id == FinanceTransaction.account_id,
                    Account.user_id == user_id,
                ),
            )
            .outerjoin(
                FinanceCategory,
                and_(
                    FinanceCategory.id == FinanceTransaction.category_id,
                    or_(
                        FinanceCategory.is_system == True,
                        FinanceCategory.user_id == user_id,
                    ),
                ),
            )
            .filter(
                FinanceTransaction.id == transaction_id,
                FinanceTransaction.user_id == user_id,
            )
            .one_or_none()
        )
