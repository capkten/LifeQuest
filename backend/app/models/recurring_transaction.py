import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, String, Float, Boolean, Date, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class RecurFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Uuid, ForeignKey("accounts.id"), nullable=False)
    category_id = Column(Uuid, ForeignKey("finance_categories.id"), nullable=True)
    type = Column(String(10), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(200), default="")
    frequency = Column(String(10), nullable=False)
    next_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    account = relationship("Account")
    category = relationship("FinanceCategory")
