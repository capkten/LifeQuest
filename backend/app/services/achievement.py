from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.achievement import Achievement, UserAchievement
from app.models.note import Notebook
from app.models.note_node import NoteNode
from app.models.coin_transaction import CoinSource, CoinType
from app.repositories.achievement import AchievementRepository, UserAchievementRepository
from app.repositories.coin_transaction import CoinTransactionRepository
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
    # Note count achievements
    {
        "name": "记录者",
        "description": "写下第一篇笔记",
        "icon": "📝",
        "condition_type": "note_count",
        "condition_value": 1,
        "coin_reward": 20,
        "exp_reward": 30,
    },
    {
        "name": "笔者",
        "description": "累计写下20篇笔记",
        "icon": "📖",
        "condition_type": "note_count",
        "condition_value": 20,
        "coin_reward": 80,
        "exp_reward": 150,
    },
    {
        "name": "知识库",
        "description": "累计写下50篇笔记",
        "icon": "📚",
        "condition_type": "note_count",
        "condition_value": 50,
        "coin_reward": 200,
        "exp_reward": 400,
    },
    # Login streak achievements
    {
        "name": "持之以恒",
        "description": "连续签到3天",
        "icon": "🔥",
        "condition_type": "login_streak",
        "condition_value": 3,
        "coin_reward": 30,
        "exp_reward": 50,
    },
    {
        "name": "习惯养成",
        "description": "连续签到7天",
        "icon": "⚡",
        "condition_type": "login_streak",
        "condition_value": 7,
        "coin_reward": 80,
        "exp_reward": 150,
    },
    {
        "name": "钢铁意志",
        "description": "连续签到30天",
        "icon": "💪",
        "condition_type": "login_streak",
        "condition_value": 30,
        "coin_reward": 300,
        "exp_reward": 600,
    },
    # Coins spent achievements
    {
        "name": "消费者",
        "description": "累计消费100金币",
        "icon": "💰",
        "condition_type": "coins_spent",
        "condition_value": 100,
        "coin_reward": 20,
        "exp_reward": 30,
    },
    {
        "name": "购物狂",
        "description": "累计消费500金币",
        "icon": "🛒",
        "condition_type": "coins_spent",
        "condition_value": 500,
        "coin_reward": 60,
        "exp_reward": 100,
    },
    {
        "name": "挥金如土",
        "description": "累计消费2000金币",
        "icon": "💎",
        "condition_type": "coins_spent",
        "condition_value": 2000,
        "coin_reward": 150,
        "exp_reward": 300,
    },
    # Goal completion achievements
    {
        "name": "目标达成",
        "description": "完成第一个目标",
        "icon": "🎯",
        "condition_type": "goal_count",
        "condition_value": 1,
        "coin_reward": 50,
        "exp_reward": 100,
    },
    {
        "name": "目标猎人",
        "description": "完成5个目标",
        "icon": "🏹",
        "condition_type": "goal_count",
        "condition_value": 5,
        "coin_reward": 150,
        "exp_reward": 300,
    },
    {
        "name": "目标大师",
        "description": "完成10个目标",
        "icon": "👑",
        "condition_type": "goal_count",
        "condition_value": 10,
        "coin_reward": 300,
        "exp_reward": 600,
    },
    # Transaction count achievements
    {
        "name": "记账新手",
        "description": "记录10笔交易",
        "icon": "📒",
        "condition_type": "transaction_count",
        "condition_value": 10,
        "coin_reward": 20,
        "exp_reward": 30,
    },
    {
        "name": "记账达人",
        "description": "记录100笔交易",
        "icon": "📊",
        "condition_type": "transaction_count",
        "condition_value": 100,
        "coin_reward": 100,
        "exp_reward": 200,
    },
    {
        "name": "记账大师",
        "description": "记录500笔交易",
        "icon": "🏆",
        "condition_type": "transaction_count",
        "condition_value": 500,
        "coin_reward": 300,
        "exp_reward": 500,
    },
    # Additional level milestones
    {
        "name": "精英",
        "description": "达到15级",
        "icon": "⭐",
        "condition_type": "level",
        "condition_value": 15,
        "coin_reward": 250,
        "exp_reward": 500,
    },
    {
        "name": "王者",
        "description": "达到30级",
        "icon": "🌟",
        "condition_type": "level",
        "condition_value": 30,
        "coin_reward": 500,
        "exp_reward": 1000,
    },
    {
        "name": "传说",
        "description": "达到50级",
        "icon": "✨",
        "condition_type": "level",
        "condition_value": 50,
        "coin_reward": 1000,
        "exp_reward": 2000,
    },
    # Additional task_count milestones
    {
        "name": "老手",
        "description": "完成50个任务",
        "icon": "🎖️",
        "condition_type": "task_count",
        "condition_value": 50,
        "coin_reward": 100,
        "exp_reward": 200,
    },
    {
        "name": "传奇冒险者",
        "description": "完成100个任务",
        "icon": "🏅",
        "condition_type": "task_count",
        "condition_value": 100,
        "coin_reward": 250,
        "exp_reward": 500,
    },
    # Project achievements
    {
        "name": "项目经理",
        "description": "创建第一个项目",
        "icon": "📋",
        "condition_type": "project_count",
        "condition_value": 1,
        "coin_reward": 50,
        "exp_reward": 100,
    },
    {
        "name": "多线操作",
        "description": "同时进行3个项目",
        "icon": "🎯",
        "condition_type": "project_active",
        "condition_value": 3,
        "coin_reward": 100,
        "exp_reward": 200,
    },
    {
        "name": "项目收割者",
        "description": "完成5个项目",
        "icon": "🏆",
        "condition_type": "project_completed",
        "condition_value": 5,
        "coin_reward": 200,
        "exp_reward": 500,
    },
]


class AchievementService:
    def __init__(self, db: Session):
        self.db = db
        self.achievement_repo = AchievementRepository(db)
        self.user_achievement_repo = UserAchievementRepository(db)
        self.user_repo = UserRepository(db)
        self.coin_repo = CoinTransactionRepository(db)

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
            # Record coin transactions for each unlocked achievement
            for achievement in unlocked:
                if achievement.coin_reward and achievement.coin_reward > 0:
                    self.coin_repo.create_transaction(
                        user_id=user_id,
                        amount=achievement.coin_reward,
                        coin_type=CoinType.EARN,
                        source=CoinSource.ACHIEVEMENT,
                        description=f"Achievement unlocked: {achievement.name}",
                    )
        return unlocked

    def check_notes(self, user_id: UUID) -> List[Achievement]:
        """Count notes for user and check note_count achievements."""
        count = self.db.query(NoteNode).join(Notebook).filter(
            Notebook.user_id == user_id,
            NoteNode.type == "note",
        ).count()
        return self.check_and_unlock(user_id, "note_count", count)

    def check_coins_spent(self, user_id: UUID) -> List[Achievement]:
        """Sum total coins spent from exchange history and check coins_spent achievements."""
        from sqlalchemy import func
        from app.models.shop import ExchangeHistory, ExchangeStatus

        total = self.db.query(func.coalesce(func.sum(ExchangeHistory.total_cost), 0)).filter(
            ExchangeHistory.user_id == user_id,
            ExchangeHistory.status == ExchangeStatus.COMPLETED,
        ).scalar()
        return self.check_and_unlock(user_id, "coins_spent", int(total))

    def check_transactions(self, user_id: UUID) -> List[Achievement]:
        """Count completed transactions and check transaction_count achievements."""
        from app.models.shop import ExchangeHistory, ExchangeStatus

        count = self.db.query(ExchangeHistory).filter(
            ExchangeHistory.user_id == user_id,
            ExchangeHistory.status == ExchangeStatus.COMPLETED,
        ).count()
        return self.check_and_unlock(user_id, "transaction_count", count)

    def check_projects(self, user_id: UUID) -> List[Achievement]:
        """Check project-related achievements.

        Call this from ProjectService when a project is created or completed.
        - project_count: total projects created
        - project_active: projects with status == 'active'
        - project_completed: projects with status == 'completed'
        """
        from app.models.project import Project

        all_unlocked = []

        total = self.db.query(Project).filter(Project.user_id == user_id).count()
        all_unlocked.extend(self.check_and_unlock(user_id, "project_count", total))

        active = self.db.query(Project).filter(
            Project.user_id == user_id, Project.status == "active"
        ).count()
        all_unlocked.extend(self.check_and_unlock(user_id, "project_active", active))

        completed = self.db.query(Project).filter(
            Project.user_id == user_id, Project.status == "completed"
        ).count()
        all_unlocked.extend(self.check_and_unlock(user_id, "project_completed", completed))

        return all_unlocked
