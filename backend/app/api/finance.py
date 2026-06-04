from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.finance import (
    AccountCreate, AccountUpdate, AccountResponse,
    BudgetCreate, BudgetUpdate, BudgetResponse,
    CategoryCreate, CategoryResponse,
    TransactionCreate, TransactionUpdate, TransactionResponse,
    RecurringCreate, RecurringResponse,
    DebtCreate, DebtUpdate, DebtResponse, DebtPaymentCreate, DebtPaymentResponse,
    FinanceDashboardResponse,
)
from app.services.finance import FinanceService

router = APIRouter(prefix="/api/finance", tags=["finance"])


class TransferRequest(BaseModel):
    from_id: UUID
    to_id: UUID
    amount: float
    description: str = ""


# --- Dashboard ---

@router.get("/dashboard")
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.get_dashboard(current_user.id)


# --- Accounts ---

@router.get("/accounts", response_model=List[AccountResponse])
def get_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.get_accounts(current_user.id)


@router.post("/accounts", response_model=AccountResponse)
def create_account(
    data: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.create_account(current_user.id, data)


@router.put("/accounts/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: UUID,
    data: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    account = service.account_repo.get_by_id(account_id)
    if not account or account.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Account not found")
    return service.update_account(account, data)


@router.delete("/accounts/{account_id}")
def delete_account(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    account = service.account_repo.get_by_id(account_id)
    if not account or account.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Account not found")
    service.delete_account(account)
    return {"message": "Account deleted"}


@router.post("/accounts/transfer")
def transfer(
    body: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.transfer(current_user.id, body.from_id, body.to_id, body.amount, body.description)


# --- Categories ---

@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.get_categories(current_user.id)


@router.post("/categories", response_model=CategoryResponse)
def create_category(
    data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.create_category(current_user.id, data)


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    cat = service.category_repo.get_by_id(category_id)
    if not cat:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Category not found")
    service.delete_category(cat)
    return {"message": "Category deleted"}


# --- Transactions ---

@router.get("/transactions")
def get_transactions(
    account_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.get_transactions(
        current_user.id,
        skip=skip, limit=limit,
        account_id=account_id, category_id=category_id,
        type=type, start_date=start_date, end_date=end_date,
    )


@router.post("/transactions", response_model=TransactionResponse)
def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.create_transaction(current_user.id, data)


@router.put("/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: UUID,
    data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    txn = service.transaction_repo.get_by_id(transaction_id)
    if not txn or txn.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transaction not found")
    return service.update_transaction(txn, data)


@router.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    txn = service.transaction_repo.get_by_id(transaction_id)
    if not txn or txn.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Transaction not found")
    service.delete_transaction(txn)
    return {"message": "Transaction deleted"}


# --- Budgets ---

@router.get("/budgets")
def get_budgets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.get_budgets(current_user.id)


@router.post("/budgets", response_model=BudgetResponse)
def create_budget(
    data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.create_budget(current_user.id, data)


@router.put("/budgets/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: UUID,
    data: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    budget = service.budget_repo.get_by_id(budget_id)
    if not budget or budget.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Budget not found")
    return service.update_budget(budget, data)


@router.delete("/budgets/{budget_id}")
def delete_budget(
    budget_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    budget = service.budget_repo.get_by_id(budget_id)
    if not budget or budget.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Budget not found")
    service.delete_budget(budget)
    return {"message": "Budget deleted"}


# --- Recurring ---

@router.get("/recurring", response_model=List[RecurringResponse])
def get_recurring(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.get_recurring(current_user.id)


@router.post("/recurring", response_model=RecurringResponse)
def create_recurring(
    data: RecurringCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.create_recurring(current_user.id, data)


@router.post("/recurring/{recurring_id}/trigger", response_model=TransactionResponse)
def trigger_recurring(
    recurring_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    rec = service.recurring_repo.get_by_id(recurring_id)
    if not rec or rec.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    return service.trigger_recurring(rec)


@router.delete("/recurring/{recurring_id}")
def delete_recurring(
    recurring_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    rec = service.recurring_repo.get_by_id(recurring_id)
    if not rec or rec.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    service.delete_recurring(rec)
    return {"message": "Recurring transaction deleted"}


# --- Debts ---

@router.get("/debts", response_model=List[DebtResponse])
def get_debts(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.get_debts(current_user.id, status=status)


@router.post("/debts", response_model=DebtResponse)
def create_debt(
    data: DebtCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.create_debt(current_user.id, data)


@router.put("/debts/{debt_id}", response_model=DebtResponse)
def update_debt(
    debt_id: UUID,
    data: DebtUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    debt = service.debt_repo.get_by_id(debt_id)
    if not debt or debt.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Debt not found")
    return service.update_debt(debt, data)


@router.delete("/debts/{debt_id}")
def delete_debt(
    debt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    debt = service.debt_repo.get_by_id(debt_id)
    if not debt or debt.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Debt not found")
    service.delete_debt(debt)
    return {"message": "Debt deleted"}


@router.post("/debts/{debt_id}/payments", response_model=DebtPaymentResponse)
def add_payment(
    debt_id: UUID,
    data: DebtPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = FinanceService(db)
    return service.add_payment(debt_id, current_user.id, data)
