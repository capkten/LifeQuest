import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class AccountType(str, Enum):
    CASH = "cash"          # 现金
    BANK = "bank"          # 银行卡
    CREDIT = "credit"      # 信用卡
    ALIPAY = "alipay"      # 支付宝
    WECHAT = "wechat"      # 微信
    DEBT = "debt"          # 借贷
    OTHER = "other"        # 其他


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    type = Column(String(20), default=AccountType.CASH)
    icon = Column(String(50), default="💰")
    balance = Column(Float, default=0.0)
    credit_limit = Column(Float, nullable=True)
    billing_day = Column(Integer, nullable=True)
    repayment_day = Column(Integer, nullable=True)
    interest_rate = Column(Float, nullable=True)
    currency = Column(String(10), default="CNY")
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="accounts")
    transactions = relationship("FinanceTransaction", back_populates="account", foreign_keys="FinanceTransaction.account_id")
