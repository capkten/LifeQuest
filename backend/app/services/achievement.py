from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.achievement import Achievement, UserAchievement
from app.repositories.achievement import AchievementRepository, UserAchievementRepository
from app.repositories.user import UserRepository

SEED_ACHIEVEMENTS = [
    {
        "name": "初出茅庐",
        "description": "完成你的第一个任务",
        "icon": "check",
        "condition_type": "task_count",
        "condition_value": 1,
        "coin_reward": 50,
        "exp_reward": 100,
    },
    {
        "name": "坚持不懈",
        "description": "连续7天完成习惯",
        "icon": "fire",
        "condition_type": "habit_streak",
        "condition_value": 7,
        "coin_reward": 100,
        "exp_reward": 200,
    },
    {
        "name": "冒险家",
        "description": "达到5级",
        "icon": "star",
        "condition_type": "level",
        "condition_value": 5,
        "coin_reward": 200,
        "exp_reward": 500,
    },
    {
        "name": "寻宝猎人",
        "description": "累计获得1000金币",
        "icon": "coins",
        "condition_type": "coins_earned",
        "condition_value": 1000,
        "coin_reward": 150,
        "exp_reward": 300,
    },
]


class AchievementService:
    def __init__(self, db: Session):
        self.db = db
        self.achievement_repo = AchievementRepository(db)
        self.user_achievement_repo = UserAchievementRepository(db)
        self.user_repo = UserRepository(db)

    def seed_achievements(self):
        for data in SEED_ACHIEVEMENTS:
            existing = self.achievement_repo.get_by_name(data["name"])
            if not existing:
                self.achievement_repo.create(data)

    def get_all_achievements(self) -> List[Achievement]:
        return self.achievement_repo.get_all_achievements()

    def get_user_achievements(self, user_id: UUID) -> List[UserAchievement]:
        return self.user_achievement_repo.get_by_user(user_id)

    def check_and_unlock(
        self, user_id: UUID, condition_type: str, current_value: int
    ) -> List[Achievement]:
        """Check all achievements of the given condition_type and unlock any
        that the user qualifies for but hasn't earned yet.

        Returns a list of newly unlocked Achievement objects.
        """
        achievements = self.achievement_repo.get_all_achievements()
        unlocked = []
        for achievement in achievements:
            if (
                achievement.condition_type == condition_type
                and achievement.condition_value <= current_value
            ):
                existing = self.user_achievement_repo.get_by_user_and_achievement(
                    user_id, achievement.id
                )
                if not existing:
                    self.user_achievement_repo.create(
                        {
                            "user_id": user_id,
                            "achievement_id": achievement.id,
                        }
                    )
                    # Award rewards in the same transaction
                    user = self.user_repo.get_by_id(user_id)
                    if user:
                        self.user_repo._update_coins_no_commit(user, achievement.coin_reward)
                        self.user_repo._update_experience_no_commit(user, achievement.exp_reward)
                    unlocked.append(achievement)
        if unlocked:
            self.db.commit()
        return unlocked
