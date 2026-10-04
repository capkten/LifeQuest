import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Uuid, UniqueConstraint

from app.database import Base


class FinanceDailyRewardClaim(Base):
    """Persistent claim for the first-finance-action-of-day experience bonus."""

    __tablename__ = "finance_daily_reward_claims"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "reward_date",
            name="uq_finance_daily_reward_user_day",
        ),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    reward_date = Column(Date, nullable=False)
    claimed_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
