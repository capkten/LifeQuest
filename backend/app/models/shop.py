import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Uuid

from app.database import Base


class ExchangeStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class ShopItem(Base):
    __tablename__ = "shop_items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    created_by = Column(Uuid, ForeignKey("users.id"))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    icon = Column(String(100))
    category = Column(String(50))
    price = Column(Integer, default=0)
    coin_price = Column(Integer, default=0)
    stock = Column(Integer, default=-1)  # -1 means unlimited
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ExchangeHistory(Base):
    __tablename__ = "exchange_history"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    item_id = Column(Uuid, ForeignKey("shop_items.id"), nullable=False)
    quantity = Column(Integer, default=1)
    total_cost = Column(Integer, nullable=False)
    status = Column(String(20), default=ExchangeStatus.COMPLETED)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
