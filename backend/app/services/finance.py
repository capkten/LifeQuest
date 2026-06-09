from datetime import date, timezone
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
        from_acc = self.account_repo.get_by_id(from_id)
        to_acc = self.account_repo.get_by_id(to_id)
        if not from_acc or from_acc.user_id != user_id:
            raise HTTPException(status_code=404, detail="Source account not found")
        if not to_acc or to_acc.user_id != user_id:
            raise HTTPException(status_code=404, detail="Target account not found")
        if from_acc.balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        # Create transfer transaction + update both balances atomically
        txn = FinanceTransaction(
            user_id=user_id,
            account_id=from_id,
            type=FinanceTransactionType.TRANSFER,
            amount=amount,
            description=description or f"Transfer: {from_acc.name} -> {to_acc.name}",
            date=transfer_date or date.today(),
            to_account_id=to_id,
        )
        self.db.add(txn)
        from_acc.balance -= amount
        to_acc.balance += amount
        self.db.commit()
        self.db.refresh(txn)
        return {"transaction": txn, "from_balance": from_acc.balance, "to_balance": to_acc.balance}

    def _apply_transaction_balance_effect(self, transaction: FinanceTransaction, reverse: bool = False) -> None:
        multiplier = -1 if reverse else 1
        amount = transaction.amount * multiplier

        if transaction.type == FinanceTransactionType.INCOME:
            account = self.account_repo.get_by_id(transaction.account_id)
            if account:
                account.balance += amount
        elif transaction.type == FinanceTransactionType.EXPENSE:
            account = self.account_repo.get_by_id(transaction.account_id)
            if account:
                account.balance -= amount
        elif transaction.type == FinanceTransactionType.TRANSFER:
            from_acc = self.account_repo.get_by_id(transaction.account_id)
            to_acc = self.account_repo.get_by_id(transaction.to_account_id) if transaction.to_account_id else None
            if from_acc:
                from_acc.balance -= amount
            if to_acc:
                to_acc.balance += amount

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

    def delete_category(self, cat: FinanceCategory) -> bool:
        if cat.is_system:
            raise HTTPException(status_code=400, detail="Cannot delete system category")
        self.db.delete(cat)
        self.db.commit()
        return True

    # --- Transaction CRUD ---

    def create_transaction(self, user_id: UUID, data: TransactionCreate) -> FinanceTransaction:
        if data.type == FinanceTransactionType.TRANSFER:
            raise HTTPException(
                status_code=400, detail="Use /accounts/transfer for transfers"
            )

        account = self.account_repo.get_by_id(data.account_id)
        if not account or account.user_id != user_id:
            raise HTTPException(status_code=404, detail="Account not found")

        d = data.model_dump()
        d["user_id"] = user_id
        if not d.get("date"):
            d["date"] = date.today()

        # Create transaction and update account balance atomically
        txn = FinanceTransaction(**d)
        self.db.add(txn)
        if data.type == FinanceTransactionType.INCOME:
            account.balance += data.amount
        elif data.type == FinanceTransactionType.EXPENSE:
            account.balance -= data.amount
        self.db.commit()
        self.db.refresh(txn)

        # Gamification: award exp, check achievements (best-effort)
        try:
            self._award_transaction_exp(user_id)
        except Exception:
            pass
        try:
            count = self.transaction_repo.count_by_user(user_id)
            self.achievement_service.check_and_unlock(user_id, "transaction_count", count)
        except Exception:
            pass

        return txn

    def get_transactions(self, user_id: UUID, **filters) -> dict:
        txns = self.transaction_repo.get_by_user(user_id, **filters)
        total = self.transaction_repo.count_by_user(user_id)
        return {"items": txns, "total": total}

    def update_transaction(
        self, transaction: FinanceTransaction, data: TransactionUpdate
    ) -> FinanceTransaction:
        update_data = data.model_dump(exclude_unset=True)
        new_type = update_data.get("type", transaction.type)
        new_to_account_id = update_data.get("to_account_id", transaction.to_account_id)
        if new_type == FinanceTransactionType.TRANSFER and not new_to_account_id:
            raise HTTPException(status_code=400, detail="Transfer requires target account")

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
        d = data.model_dump()
        d["user_id"] = user_id
        return self.budget_repo.create(d)

    def get_budgets(self, user_id: UUID) -> List[dict]:
        budgets = self.budget_repo.get_by_user(user_id)
        today = date.today()
        result = []
        for b in budgets:
            spent = self.budget_repo.get_spent_amount(b, today.year, today.month)
            remaining = b.amount - spent
            result.append({
                "id": b.id,
                "user_id": b.user_id,
                "category_id": b.category_id,
                "amount": b.amount,
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
        # Create the actual transaction
        txn = FinanceTransaction(
            user_id=recurring.user_id,
            account_id=recurring.account_id,
            category_id=recurring.category_id,
            type=recurring.type,
            amount=recurring.amount,
            description=recurring.description,
            date=recurring.next_date,
        )
        self.db.add(txn)

        # Update account balance
        account = self.account_repo.get_by_id(recurring.account_id)
        if account:
            if recurring.type == FinanceTransactionType.INCOME:
                account.balance += recurring.amount
            elif recurring.type == FinanceTransactionType.EXPENSE:
                account.balance -= recurring.amount

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

        payment = DebtPayment(
            debt_id=debt_id,
            amount=data.amount,
            description=data.description,
            date=data.date,
        )
        self.db.add(payment)

        debt.remaining -= data.amount
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
                {"id": a.id, "name": a.name, "type": a.type, "icon": a.icon, "balance": a.balance}
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
        self.db.commit()
