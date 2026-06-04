from datetime import date, datetime, timezone

from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class DailyCheckin(Base):
    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    checkin_date = Column(Date, default=date.today)
    streak = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date"),
    )

    user = relationship("User", back_populates="checkins")
