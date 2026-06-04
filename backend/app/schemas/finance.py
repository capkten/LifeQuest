from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.account import AccountType
from app.models.finance_category import CategoryType
from app.models.finance_transaction import FinanceTransactionType
from app.models.budget import BudgetPeriod
from app.models.recurring_transaction import RecurFrequency
from app.models.debt import DebtType, DebtStatus


# Account schemas
class AccountCreate(BaseModel):
    name: str
    type: AccountType = AccountType.CASH
    icon: str = "💰"
    balance: float = 0.0
    credit_limit: Optional[float] = None
    billing_day: Optional[int] = None
    repayment_day: Optional[int] = None
    interest_rate: Optional[float] = None
    currency: str = "CNY"
    sort_order: int = 0


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[AccountType] = None
    icon: Optional[str] = None
    balance: Optional[float] = None
    credit_limit: Optional[float] = None
    billing_day: Optional[int] = None
    repayment_day: Optional[int] = None
    interest_rate: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    type: str
    icon: str
    balance: float
    credit_limit: Optional[float] = None
    billing_day: Optional[int] = None
    repayment_day: Optional[int] = None
    interest_rate: Optional[float] = None
    currency: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


# FinanceCategory schemas
class CategoryCreate(BaseModel):
    name: str
    type: CategoryType
    icon: str = "📦"
    parent_id: Optional[UUID] = None
    sort_order: int = 0


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID] = None
    name: str
    type: str
    icon: str
    parent_id: Optional[UUID] = None
    is_system: bool
    sort_order: int
    created_at: datetime


# FinanceTransaction schemas
class TransactionCreate(BaseModel):
    account_id: UUID
    category_id: Optional[UUID] = None
    type: FinanceTransactionType
    amount: float
    description: str = ""
    date: date
    to_account_id: Optional[UUID] = None


class TransactionUpdate(BaseModel):
    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    type: Optional[FinanceTransactionType] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    date: Optional[date] = None
    to_account_id: Optional[UUID] = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    account_id: UUID
    category_id: Optional[UUID] = None
    type: str
    amount: float
    description: str
    date: date
    to_account_id: Optional[UUID] = None
    created_at: datetime


# Budget schemas
class BudgetCreate(BaseModel):
    category_id: Optional[UUID] = None
    amount: float
    period: BudgetPeriod = BudgetPeriod.MONTHLY
    start_date: Optional[date] = None


class BudgetUpdate(BaseModel):
    category_id: Optional[UUID] = None
    amount: Optional[float] = None
    period: Optional[BudgetPeriod] = None
    start_date: Optional[date] = None


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    category_id: Optional[UUID] = None
    amount: float
    period: str
    start_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime


# RecurringTransaction schemas
class RecurringCreate(BaseModel):
    account_id: UUID
    category_id: Optional[UUID] = None
    type: FinanceTransactionType
    amount: float
    description: str = ""
    frequency: RecurFrequency
    next_date: date


class RecurringUpdate(BaseModel):
    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    type: Optional[FinanceTransactionType] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    frequency: Optional[RecurFrequency] = None
    next_date: Optional[date] = None
    is_active: Optional[bool] = None


class RecurringResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    account_id: UUID
    category_id: Optional[UUID] = None
    type: str
    amount: float
    description: str
    frequency: str
    next_date: date
    is_active: bool
    created_at: datetime


# Debt schemas
class DebtCreate(BaseModel):
    creditor: str
    type: DebtType
    amount: float
    remaining: float
    interest_rate: float = 0.0
    description: str = ""
    due_date: Optional[date] = None


class DebtUpdate(BaseModel):
    creditor: Optional[str] = None
    type: Optional[DebtType] = None
    amount: Optional[float] = None
    remaining: Optional[float] = None
    interest_rate: Optional[float] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[DebtStatus] = None


class DebtResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    creditor: str
    type: str
    amount: float
    remaining: float
    interest_rate: float
    description: str
    due_date: Optional[date] = None
    status: str
    created_at: datetime
    updated_at: datetime


class DebtPaymentCreate(BaseModel):
    amount: float
    description: str = ""
    date: date


class DebtPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    debt_id: UUID
    amount: float
    description: str
    date: date
    created_at: datetime


# Dashboard schema
class FinanceDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_balance: float
    month_income: float
    month_expense: float
    budgets: List[BudgetResponse]
    recent_transactions: List[TransactionResponse]
