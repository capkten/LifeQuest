from datetime import datetime, date as Date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.account import AccountType
from app.models.finance_category import CategoryType
from app.models.finance_transaction import FinanceTransactionType
from app.models.budget import BudgetPeriod
from app.models.recurring_transaction import RecurFrequency
from app.models.debt import DebtType, DebtStatus


def _round_money(v: float | Decimal | None) -> float | None:
    """Round monetary value to 2 decimal places."""
    if v is None:
        return None
    return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _validate_account_values(
    account_type: AccountType,
    balance: float,
    credit_limit: Optional[float],
) -> None:
    balance_value = Decimal(str(balance))
    limit_value = Decimal(str(credit_limit)) if credit_limit is not None else Decimal("0")
    if limit_value < 0:
        raise ValueError("credit_limit must be non-negative")
    if account_type == AccountType.CREDIT:
        if balance_value < -limit_value:
            raise ValueError("Credit account balance cannot be below its credit limit")
    elif balance_value < 0:
        raise ValueError("Account balance cannot be negative")


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

    _round_balance = field_validator("balance", "credit_limit", mode="before")(_round_money)

    @model_validator(mode="after")
    def _validate_account_balance(self):
        _validate_account_values(self.type, self.balance, self.credit_limit)
        return self


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

    _round_balance = field_validator("balance", "credit_limit", mode="before")(_round_money)

    @model_validator(mode="after")
    def _validate_explicit_account_values(self):
        if self.type is None and "type" in self.model_fields_set:
            raise ValueError("type must not be null")
        if self.balance is None and "balance" in self.model_fields_set:
            raise ValueError("balance must not be null")
        if self.credit_limit is not None and self.credit_limit < 0:
            raise ValueError("credit_limit must be non-negative")
        return self


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
    amount: float = Field(gt=0)
    description: str = ""
    date: Date
    to_account_id: Optional[UUID] = None

    _round_amount = field_validator("amount", mode="before")(_round_money)


class TransactionUpdate(BaseModel):
    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    type: Optional[FinanceTransactionType] = None
    amount: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = None
    date: Optional[Date] = None
    to_account_id: Optional[UUID] = None

    _round_amount = field_validator("amount", mode="before")(_round_money)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    account_id: UUID
    category_id: Optional[UUID] = None
    type: str
    amount: float
    description: str
    date: Date
    to_account_id: Optional[UUID] = None
    created_at: datetime
    account_name: Optional[str] = None
    category_name: Optional[str] = None


class TransactionPageResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# Budget schemas
class BudgetCreate(BaseModel):
    category_id: Optional[UUID] = None
    amount: float = Field(gt=0)
    period: BudgetPeriod = BudgetPeriod.MONTHLY
    start_date: Optional[Date] = None

    _round_amount = field_validator("amount", mode="before")(_round_money)


class BudgetUpdate(BaseModel):
    category_id: Optional[UUID] = None
    amount: Optional[float] = Field(default=None, gt=0)
    period: Optional[BudgetPeriod] = None
    start_date: Optional[Date] = None

    _round_amount = field_validator("amount", mode="before")(_round_money)


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    category_id: Optional[UUID] = None
    amount: float
    period: str
    start_date: Optional[Date] = None
    created_at: datetime
    updated_at: datetime
    spent_amount: float
    remaining_amount: float
    progress: float
    category_name: Optional[str] = None


# RecurringTransaction schemas
class RecurringCreate(BaseModel):
    account_id: UUID
    category_id: Optional[UUID] = None
    type: FinanceTransactionType
    amount: float = Field(gt=0)
    description: str = ""
    frequency: RecurFrequency
    next_date: Date

    _round_amount = field_validator("amount", mode="before")(_round_money)


class RecurringUpdate(BaseModel):
    account_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    type: Optional[FinanceTransactionType] = None
    amount: Optional[float] = Field(default=None, gt=0)
    description: Optional[str] = None
    frequency: Optional[RecurFrequency] = None
    next_date: Optional[Date] = None
    is_active: Optional[bool] = None

    _round_amount = field_validator("amount", mode="before")(_round_money)

    @model_validator(mode="after")
    def _validate_explicit_recurring_values(self):
        non_nullable_fields = ("account_id", "type", "amount", "frequency", "next_date", "is_active")
        for field in non_nullable_fields:
            if getattr(self, field) is None and field in self.model_fields_set:
                raise ValueError(f"{field} must not be null")
        return self


class RecurringResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    account_id: UUID
    category_id: Optional[UUID] = None
    type: str
    amount: float
    description: Optional[str] = None
    frequency: str
    next_date: Date
    is_active: bool
    created_at: datetime


# Debt schemas
def _normalize_debt_payload(value):
    if not isinstance(value, dict):
        return value
    payload = dict(value)
    legacy_creditor = payload.pop("creditor_name", None)
    if "creditor" not in payload:
        if legacy_creditor is not None:
            payload["creditor"] = legacy_creditor
    elif legacy_creditor is not None and payload["creditor"] != legacy_creditor:
        raise ValueError("creditor and creditor_name must match")

    legacy_types = {"borrowed": "borrow", "lent": "lend"}
    if payload.get("type") in legacy_types:
        payload["type"] = legacy_types[payload["type"]]
    return payload


class DebtCreate(BaseModel):
    creditor: str
    type: DebtType
    amount: float = Field(gt=0)
    remaining: float = Field(ge=0)
    interest_rate: float = 0.0
    description: str = ""
    due_date: Optional[Date] = None

    _round_amounts = field_validator("amount", "remaining", mode="before")(_round_money)

    _normalize_legacy_fields = model_validator(mode="before")(_normalize_debt_payload)

    @model_validator(mode="after")
    def validate_remaining(self):
        if self.remaining > self.amount:
            raise ValueError("remaining must not exceed amount")
        return self


class DebtUpdate(BaseModel):
    creditor: Optional[str] = None
    type: Optional[DebtType] = None
    amount: Optional[float] = Field(default=None, gt=0)
    remaining: Optional[float] = Field(default=None, ge=0)
    interest_rate: Optional[float] = None
    description: Optional[str] = None
    due_date: Optional[Date] = None
    status: Optional[DebtStatus] = None

    _round_amounts = field_validator("amount", "remaining", mode="before")(_round_money)

    _normalize_legacy_fields = model_validator(mode="before")(_normalize_debt_payload)


class DebtPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    debt_id: UUID
    amount: float
    description: str
    date: Date
    created_at: datetime


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
    due_date: Optional[Date] = None
    status: str
    created_at: datetime
    updated_at: datetime
    payments: List[DebtPaymentResponse] = Field(default_factory=list)


class DebtPaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    description: str = ""
    date: Date

    _round_amount = field_validator("amount", mode="before")(_round_money)


# Dashboard schema
class FinanceDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_balance: float
    month_income: float
    month_expense: float
    budgets: List[BudgetResponse]
    recent_transactions: List[TransactionResponse]
