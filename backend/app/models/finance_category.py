import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class CategoryType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class FinanceCategory(Base):
    __tablename__ = "finance_categories"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(50), nullable=False)
    type = Column(String(10), nullable=False)
    icon = Column(String(50), default="📦")
    parent_id = Column(Uuid, ForeignKey("finance_categories.id"), nullable=True)
    is_system = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="finance_categories")
    children = relationship("FinanceCategory", backref="parent", remote_side=[id])
