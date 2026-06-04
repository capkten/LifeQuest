import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, String, Float, Date, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class DebtType(str, Enum):
    BORROW = "borrow"  # 借入
    LEND = "lend"      # 借出


class DebtStatus(str, Enum):
    ACTIVE = "active"
    SETTLED = "settled"


class Debt(Base):
    __tablename__ = "debts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    creditor = Column(String(100), nullable=False)
    type = Column(String(10), nullable=False)
    amount = Column(Float, nullable=False)
    remaining = Column(Float, nullable=False)
    interest_rate = Column(Float, default=0.0)
    description = Column(String(200), default="")
    due_date = Column(Date, nullable=True)
    status = Column(String(10), default=DebtStatus.ACTIVE)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    payments = relationship("DebtPayment", back_populates="debt", cascade="all, delete-orphan")


class DebtPayment(Base):
    __tablename__ = "debt_payments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    debt_id = Column(Uuid, ForeignKey("debts.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String(200), default="")
    date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    debt = relationship("Debt", back_populates="payments")
