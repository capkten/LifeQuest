from datetime import date, timezone
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.budget import Budget
from app.models.debt import Debt, DebtPayment, DebtStatus
from app.models.finance_category import FinanceCategory, CategoryType
from app.models.finance_transaction import FinanceTransaction, FinanceTransactionType
from app.models.recurring_transaction import RecurringTransaction
from app.models.coin_transaction import CoinSource, CoinType
from app.repositories.account import AccountRepository
from app.repositories.budget import BudgetRepository
from app.repositories.finance_transaction import FinanceTransactionRepository
from app.repositories.base import BaseRepository
from app.repositories.user import UserRepository
from app.repositories.coin_transaction import CoinTransactionRepository
from app.schemas.finance import (
    AccountCreate, AccountUpdate,
    BudgetCreate, BudgetUpdate,
    CategoryCreate,
    TransactionCreate, TransactionUpdate,
    RecurringCreate,
    DebtCreate, DebtUpdate, DebtPaymentCreate,
)
from app.services.achievement import AchievementService


class FinanceService:
    logger = logging.getLogger(__name__)
    SEED_EXPENSE_CATEGORIES = [
        ("餐饮", "🍜"), ("交通", "🚌"), ("购物", "🛒"), ("住房", "🏠"),
        ("娱乐", "🎮"), ("医疗", "💊"), ("教育", "📚"), ("通讯", "📱"), ("其他", "📦"),
    ]
    SEED_INCOME_CATEGORIES = [
        ("工资", "💰"), ("奖金", "🎁"), ("投资收益", "📈"),
        ("兼职", "💼"), ("红包", "🧧"), ("其他", "📦"),
    ]

    def __init__(self, db: Session):
        self.db = db
        self.account_repo = AccountRepository(db)
        self.category_repo = BaseRepository(FinanceCategory, db)
        self.transaction_repo = FinanceTransactionRepository(db)
        self.budget_repo = BudgetRepository(db)
        self.recurring_repo = BaseRepository(RecurringTransaction, db)
        self.debt_repo = BaseRepository(Debt, db)
        self.debt_payment_repo = BaseRepository(DebtPayment, db)
        self.user_repo = UserRepository(db)
        self.coin_repo = CoinTransactionRepository(db)
        self.achievement_service = AchievementService(db)

    def _get_account_for_user(self, account_id: UUID, user_id: UUID) -> Account:
        account = self.account_repo.get_by_id(account_id)
        if not account or account.user_id != user_id:
            raise HTTPException(status_code=404, detail="Account not found")
        return account

    def _validate_category_for_user(self, category_id: UUID | None, user_id: UUID) -> None:
        if category_id is None:
            return
        category = self.category_repo.get_by_id(category_id)
        if not category or (not category.is_system and category.user_id != user_id):
            raise HTTPException(status_code=404, detail="Category not found")

    # --- Seed categories ---

    @staticmethod
    def seed_categories(db: Session):
        existing = db.query(FinanceCategory).filter(
            FinanceCategory.is_system == True
        ).first()
        if existing:
            return
        categories = []
        for i, (name, icon) in enumerate(FinanceService.SEED_EXPENSE_CATEGORIES):
            categories.append(FinanceCategory(
                name=name, type=CategoryType.EXPENSE, icon=icon,
                is_system=True, sort_order=i,
            ))
        for i, (name, icon) in enumerate(FinanceService.SEED_INCOME_CATEGORIES):
            categories.append(FinanceCategory(
                name=name, type=CategoryType.INCOME, icon=icon,
                is_system=True, sort_order=i,
            ))
        db.add_all(categories)
        db.commit()

    # --- Account CRUD ---

    def create_account(self, user_id: UUID, data: AccountCreate) -> Account:
        d = data.model_dump()
        d["user_id"] = user_id
        return self.account_repo.create(d)

    def get_accounts(self, user_id: UUID) -> List[Account]:
        return self.account_repo.get_by_user(user_id)

    def update_account(self, account: Account, data: AccountUpdate) -> Account:
        update_data = data.model_dump(exclude_unset=True)
        return self.account_repo.update(account, update_data)

    def delete_account(self, account: Account) -> bool:
        account.is_active = False
        self.db.commit()
        self.db.refresh(account)
        return True

    def transfer(
        self, user_id: UUID, from_id: UUID, to_id: UUID,
        amount: float, description: str = "", transfer_date: date | None = None,
    ) -> dict:
        if amount <= 0:
            raise HTTPException(status_code=422, detail="Amount must be greater than zero")
        from_acc = self.account_repo.get_by_id(from_id)
        to_acc = self.account_repo.get_by_id(to_id)
        if not from_acc or from_acc.user_id != user_id:
            raise HTTPException(status_code=404, detail="Source account not found")
        if not to_acc or to_acc.user_id != user_id:
            raise HTTPException(status_code=404, detail="Target account not found")
        if float(from_acc.balance) < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        # Create transfer transaction + update both balances atomically
        txn = FinanceTransaction(
            user_id=user_id,
            account_id=from_id,
            type=FinanceTransactionType.TRANSFER,
            amount=amount,
            description=description or f"转账：{from_acc.name} -> {to_acc.name}",
            date=transfer_date or date.today(),
            to_account_id=to_id,
        )
        self.db.add(txn)
        from_acc.balance = float(from_acc.balance) - amount
        to_acc.balance = float(to_acc.balance) + amount
        self.db.commit()
        self.db.refresh(txn)
        return {"transaction": txn, "from_balance": from_acc.balance, "to_balance": to_acc.balance}

    def _apply_transaction_balance_effect(self, transaction: FinanceTransaction, reverse: bool = False) -> None:
        multiplier = -1 if reverse else 1
        amount = float(transaction.amount) * multiplier

        if transaction.type == FinanceTransactionType.INCOME:
            account = self.account_repo.get_by_id(transaction.account_id)
            if account:
                account.balance = float(account.balance) + amount
        elif transaction.type == FinanceTransactionType.EXPENSE:
            account = self.account_repo.get_by_id(transaction.account_id)
            if account:
                account.balance = float(account.balance) - amount
        elif transaction.type == FinanceTransactionType.TRANSFER:
            from_acc = self.account_repo.get_by_id(transaction.account_id)
            to_acc = self.account_repo.get_by_id(transaction.to_account_id) if transaction.to_account_id else None
            if from_acc:
                from_acc.balance = float(from_acc.balance) - amount
            if to_acc:
                to_acc.balance = float(to_acc.balance) + amount

    # --- Category CRUD ---

    def get_categories(self, user_id: UUID) -> List[FinanceCategory]:
        return (
            self.db.query(FinanceCategory)
            .filter(
                (FinanceCategory.is_system == True) | (FinanceCategory.user_id == user_id)
            )
            .order_by(FinanceCategory.sort_order)
            .all()
        )

    def create_category(self, user_id: UUID, data: CategoryCreate) -> FinanceCategory:
        d = data.model_dump()
        d["user_id"] = user_id
        return self.category_repo.create(d)

    def delete_category(self, cat: FinanceCategory, user_id: UUID) -> bool:
        if cat.is_system:
            raise HTTPException(status_code=400, detail="Cannot delete system category")
        if cat.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        self.db.delete(cat)
        self.db.commit()
        return True

    # --- Transaction CRUD ---

    def create_transaction(self, user_id: UUID, data: TransactionCreate) -> FinanceTransaction:
        if data.type == FinanceTransactionType.TRANSFER:
            raise HTTPException(
                status_code=400, detail="Use /accounts/transfer for transfers"
            )

        account = self._get_account_for_user(data.account_id, user_id)
        self._validate_category_for_user(data.category_id, user_id)

        d = data.model_dump()
        d["user_id"] = user_id
        if not d.get("date"):
            d["date"] = date.today()

        # Create transaction and update account balance atomically
        txn = FinanceTransaction(**d)
        self.db.add(txn)
        if data.type == FinanceTransactionType.INCOME:
            account.balance = float(account.balance) + data.amount
        elif data.type == FinanceTransactionType.EXPENSE:
            account.balance = float(account.balance) - data.amount
        try:
            self._award_transaction_exp(user_id)
            self.db.flush()
            count = self.transaction_repo.count_by_user(user_id)
            self.achievement_service.check_and_unlock(
                user_id, "transaction_count", count, commit=False
            )
            self.db.commit()
            self.db.refresh(txn)
        except Exception:
            self.db.rollback()
            self.logger.exception("Finance transaction commit failed for user %s", user_id)
            raise

        return txn

    def get_transactions(self, user_id: UUID, **filters) -> dict:
        page = filters.pop("page", 1)
        page_size = filters.pop("page_size", 50)
        legacy_skip = filters.pop("skip", None)
        legacy_limit = filters.pop("limit", None)
        if legacy_limit is not None:
            page_size = legacy_limit

        if legacy_skip is None:
            offset = (page - 1) * page_size
        else:
            offset = legacy_skip
            page = (offset // page_size) + 1

        txns = self.transaction_repo.get_by_user(
            user_id,
            skip=offset,
            limit=page_size,
            **filters,
        )
        total = self.transaction_repo.count_by_user(user_id, **filters)
        return {
            "items": txns,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": offset + len(txns) < total,
        }

    def update_transaction(
        self, transaction: FinanceTransaction, data: TransactionUpdate, user_id: UUID
    ) -> FinanceTransaction:
        update_data = data.model_dump(exclude_unset=True)
        new_account_id = update_data.get("account_id", transaction.account_id)
        new_category_id = update_data.get("category_id", transaction.category_id)
        new_type = update_data.get("type", transaction.type)
        new_to_account_id = update_data.get("to_account_id", transaction.to_account_id)
        self._get_account_for_user(new_account_id, user_id)
        self._validate_category_for_user(new_category_id, user_id)
        if new_type == FinanceTransactionType.TRANSFER and not new_to_account_id:
            raise HTTPException(status_code=400, detail="Transfer requires target account")
        if new_to_account_id:
            self._get_account_for_user(new_to_account_id, user_id)

        self._apply_transaction_balance_effect(transaction, reverse=True)
        for key, value in update_data.items():
            setattr(transaction, key, value)
        self._apply_transaction_balance_effect(transaction, reverse=False)

        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def delete_transaction(self, transaction: FinanceTransaction) -> bool:
        # Reverse the balance change
        self._apply_transaction_balance_effect(transaction, reverse=True)
        self.db.delete(transaction)
        self.db.commit()
        return True

    # --- Budget CRUD ---

    def create_budget(self, user_id: UUID, data: BudgetCreate) -> Budget:
        self._validate_category_for_user(data.category_id, user_id)
        d = data.model_dump()
        d["user_id"] = user_id
        return self.budget_repo.create(d)

    def get_budgets(self, user_id: UUID) -> List[dict]:
        budgets = self.budget_repo.get_by_user(user_id)
        today = date.today()
        result = []
        for b in budgets:
            spent = self.budget_repo.get_spent_amount(b, today.year, today.month)
            budget_amount = float(b.amount)
            remaining = budget_amount - spent
            result.append({
                "id": b.id,
                "user_id": b.user_id,
                "category_id": b.category_id,
                "amount": budget_amount,
                "period": b.period,
                "start_date": b.start_date,
                "created_at": b.created_at,
                "updated_at": b.updated_at,
                "spent_amount": spent,
                "remaining": remaining,
            })
        return result

    def update_budget(self, budget: Budget, data: BudgetUpdate) -> Budget:
        update_data = data.model_dump(exclude_unset=True)
        return self.budget_repo.update(budget, update_data)

    def delete_budget(self, budget: Budget) -> bool:
        return self.budget_repo.delete(budget.id)

    # --- Recurring ---

    def create_recurring(self, user_id: UUID, data: RecurringCreate) -> RecurringTransaction:
        self._get_account_for_user(data.account_id, user_id)
        self._validate_category_for_user(data.category_id, user_id)
        d = data.model_dump()
        d["user_id"] = user_id
        return self.recurring_repo.create(d)

    def get_recurring(self, user_id: UUID) -> List[RecurringTransaction]:
        return (
            self.db.query(RecurringTransaction)
            .filter(RecurringTransaction.user_id == user_id)
            .order_by(RecurringTransaction.created_at.desc())
            .all()
        )

    def delete_recurring(self, rec: RecurringTransaction) -> bool:
        return self.recurring_repo.delete(rec.id)

    def trigger_recurring(self, recurring: RecurringTransaction) -> FinanceTransaction:
        # Idempotency: check if already triggered for this date
        existing = (
            self.db.query(FinanceTransaction)
            .filter(
                FinanceTransaction.recurring_id == recurring.id,
                FinanceTransaction.date == recurring.next_date,
            )
            .first()
        )
        if existing:
            return existing

        # Create the actual transaction
        txn = FinanceTransaction(
            user_id=recurring.user_id,
            account_id=recurring.account_id,
            category_id=recurring.category_id,
            type=recurring.type,
            amount=recurring.amount,
            description=recurring.description,
            date=recurring.next_date,
            recurring_id=recurring.id,
        )
        self.db.add(txn)

        # Update account balance
        account = self.account_repo.get_by_id(recurring.account_id)
        if account:
            if recurring.type == FinanceTransactionType.INCOME:
                account.balance = float(account.balance) + float(recurring.amount)
            elif recurring.type == FinanceTransactionType.EXPENSE:
                account.balance = float(account.balance) - float(recurring.amount)

        # Advance next_date based on frequency
        from datetime import timedelta
        import calendar

        def _add_months(d: date, months: int) -> date:
            month = d.month - 1 + months
            year = d.year + month // 12
            month = month % 12 + 1
            day = min(d.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)

        freq = recurring.frequency
        if freq == "daily":
            recurring.next_date = recurring.next_date + timedelta(days=1)
        elif freq == "weekly":
            recurring.next_date = recurring.next_date + timedelta(weeks=1)
        elif freq == "monthly":
            recurring.next_date = _add_months(recurring.next_date, 1)
        elif freq == "yearly":
            recurring.next_date = _add_months(recurring.next_date, 12)

        self.db.commit()
        self.db.refresh(txn)
        return txn

    # --- Debt CRUD ---

    def create_debt(self, user_id: UUID, data: DebtCreate) -> Debt:
        d = data.model_dump()
        d["user_id"] = user_id
        return self.debt_repo.create(d)

    def get_debts(self, user_id: UUID, status: Optional[str] = None) -> List[Debt]:
        query = self.db.query(Debt).filter(Debt.user_id == user_id)
        if status:
            query = query.filter(Debt.status == status)
        return query.order_by(Debt.created_at.desc()).all()

    def update_debt(self, debt: Debt, data: DebtUpdate) -> Debt:
        update_data = data.model_dump(exclude_unset=True)
        new_amount = update_data.get("amount", debt.amount)
        new_remaining = update_data.get("remaining", debt.remaining)
        if new_remaining < 0 or new_remaining > new_amount:
            raise HTTPException(status_code=422, detail="remaining must be between zero and amount")
        for key, value in update_data.items():
            setattr(debt, key, value)
        self.db.commit()
        self.db.refresh(debt)
        return debt

    def delete_debt(self, debt: Debt) -> bool:
        return self.debt_repo.delete(debt.id)

    def add_payment(
        self, debt_id: UUID, user_id: UUID, data: DebtPaymentCreate
    ) -> DebtPayment:
        debt = self.debt_repo.get_by_id(debt_id)
        if not debt or debt.user_id != user_id:
            raise HTTPException(status_code=404, detail="Debt not found")
        if debt.status == DebtStatus.SETTLED:
            raise HTTPException(status_code=400, detail="Debt already settled")
        if data.amount > debt.remaining:
            raise HTTPException(status_code=400, detail="Payment exceeds remaining debt")

        payment = DebtPayment(
            debt_id=debt_id,
            amount=data.amount,
            description=data.description,
            date=data.date,
        )
        self.db.add(payment)

        debt.remaining = float(debt.remaining) - data.amount
        if debt.remaining <= 0:
            debt.remaining = 0
            debt.status = DebtStatus.SETTLED

        self.db.commit()
        self.db.refresh(payment)
        return payment

    # --- Dashboard ---

    def get_dashboard(self, user_id: UUID) -> dict:
        today = date.today()
        total_balance = self.account_repo.get_total_balance(user_id)
        month_summary = self.transaction_repo.get_month_summary(
            user_id, today.year, today.month
        )
        budgets = self.get_budgets(user_id)
        recent_txns = self.transaction_repo.get_by_user(user_id, limit=5)

        return {
            "total_balance": total_balance,
            "month_income": month_summary["income"],
            "month_expense": month_summary["expense"],
            "month_net": month_summary["income"] - month_summary["expense"],
            "account_balances": [
                {"id": a.id, "name": a.name, "type": a.type, "icon": a.icon, "balance": float(a.balance)}
                for a in self.account_repo.get_by_user(user_id)
            ],
            "budgets": budgets,
            "recent_transactions": recent_txns,
        }

    # --- Internal helpers ---

    def _award_transaction_exp(self, user_id: UUID):
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return
        exp = 2
        # +5 bonus for first finance transaction of the day
        today_start = date.today()
        existing_today = (
            self.db.query(FinanceTransaction)
            .filter(
                FinanceTransaction.user_id == user_id,
                FinanceTransaction.date == today_start,
            )
            .count()
        )
        if existing_today <= 1:  # the one we just created
            exp += 5
        self.user_repo._update_experience_no_commit(user, exp)
