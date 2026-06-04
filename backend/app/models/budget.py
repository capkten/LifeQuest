import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, String, Float, Date, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class BudgetPeriod(str, Enum):
    MONTHLY = "monthly"
    WEEKLY = "weekly"


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Uuid, ForeignKey("finance_categories.id"), nullable=True)
    amount = Column(Float, nullable=False)
    period = Column(String(10), default=BudgetPeriod.MONTHLY)
    start_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    category = relationship("FinanceCategory")
