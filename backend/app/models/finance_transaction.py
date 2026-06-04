import uuid
from datetime import datetime, timezone, date
from enum import Enum

from sqlalchemy import Column, String, Float, DateTime, Date, ForeignKey, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class FinanceTransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class FinanceTransaction(Base):
    __tablename__ = "finance_transactions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Uuid, ForeignKey("accounts.id"), nullable=False)
    category_id = Column(Uuid, ForeignKey("finance_categories.id"), nullable=True)
    type = Column(String(10), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(200), default="")
    date = Column(Date, nullable=False, index=True)
    to_account_id = Column(Uuid, ForeignKey("accounts.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    account = relationship("Account", back_populates="transactions", foreign_keys=[account_id])
    to_account = relationship("Account", foreign_keys=[to_account_id])
    category = relationship("FinanceCategory")
