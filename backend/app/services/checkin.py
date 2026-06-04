from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.coin_transaction import CoinSource, CoinType
from app.repositories.checkin import CheckinRepository
from app.repositories.coin_transaction import CoinTransactionRepository
from app.repositories.user import UserRepository
from app.services.achievement import AchievementService

BASE_COINS = 10
BASE_EXP = 5
STREAK_BONUS_COINS = 50
STREAK_BONUS_EXP = 20
STREAK_INTERVAL = 7


class CheckinService:
    def __init__(self, db: Session):
        self.db = db
        self.checkin_repo = CheckinRepository(db)
        self.user_repo = UserRepository(db)
        self.coin_repo = CoinTransactionRepository(db)
        self.achievement_service = AchievementService(db)

    def get_status(self, user_id: UUID) -> dict:
        today = date.today()
        today_checkin = self.checkin_repo.get_by_user_and_date(user_id, today)

        latest = self.checkin_repo.get_latest_by_user(user_id)
        current_streak = latest.streak if latest else 0

        if today_checkin:
            # Already checked in today - return actual streak
            streak = today_checkin.streak
        else:
            # Not checked in yet - streak would be what it becomes on checkin
            if latest and latest.checkin_date == today - timedelta(days=1):
                streak = current_streak + 1
            else:
                streak = 1

        # Calculate what rewards would be
        reward_coins = BASE_COINS
        reward_exp = BASE_EXP
        if streak % STREAK_INTERVAL == 0:
            reward_coins += STREAK_BONUS_COINS
            reward_exp += STREAK_BONUS_EXP

        return {
            "checked_in": today_checkin is not None,
            "streak": current_streak if today_checkin else current_streak,
            "reward_coins": reward_coins,
            "reward_exp": reward_exp,
        }

    def checkin(self, user_id: UUID):
        today = date.today()
        existing = self.checkin_repo.get_by_user_and_date(user_id, today)
        if existing:
            raise HTTPException(status_code=400, detail="Already checked in today")

        # Calculate streak
        latest = self.checkin_repo.get_latest_by_user(user_id)
        if latest and latest.checkin_date == today - timedelta(days=1):
            streak = latest.streak + 1
        else:
            streak = 1

        # Create checkin record (handle race condition)
        try:
            checkin = self.checkin_repo.create({
                "user_id": user_id,
                "checkin_date": today,
                "streak": streak,
            })
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Already checked in today")

        # Calculate rewards
        reward_coins = BASE_COINS
        reward_exp = BASE_EXP
        if streak % STREAK_INTERVAL == 0:
            reward_coins += STREAK_BONUS_COINS
            reward_exp += STREAK_BONUS_EXP

        # Award rewards
        user = self.user_repo.get_by_id(user_id)
        if user:
            self.user_repo._update_coins_no_commit(user, reward_coins)
            self.user_repo._update_experience_no_commit(user, reward_exp)
            self.db.commit()

        # Record coin transaction
        self.coin_repo.create_transaction(
            user_id=user_id,
            amount=reward_coins,
            coin_type=CoinType.EARN,
            source=CoinSource.CHECKIN,
            description=f"Daily check-in (streak: {streak})",
        )

        # Check achievements: login_streak, checkin_count
        checkin_count = self.checkin_repo.get_checkin_count(user_id)
        self.achievement_service.check_and_unlock(user_id, "login_streak", streak)
        self.achievement_service.check_and_unlock(user_id, "checkin_count", checkin_count)

        return checkin
