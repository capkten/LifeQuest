import math
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.cultivation import CultivationLog, CultivationProfile
from app.repositories.cultivation import CultivationRepository
from app.repositories.user import UserRepository
from app.schemas.cultivation import CultivationOverview, RewardSettlement, StageProgress


REALM_THRESHOLDS = {
    "qi_refining": [100, 110, 120, 130, 145, 160, 180, 205, 235],
    "foundation": [500, 600, 750, 950],
    "golden_core": [1000, 1300, 1700, 2000],
    "nascent_soul": [1500, 2200, 2800, 3500],
    "spirit_transformation": [2500, 3500, 4500, 5500],
    "void_refining": [4500, 6000, 8000, 9500],
    "body_combination": [7000, 9500, 13000, 18000],
    "great_vehicle": [12000, 16000, 22000, 30000],
    "tribulation": [20000, 26000, 35000, 49000],
}

DIFFICULTY_FACTORS = {"easy": 0.8, "medium": 1.0, "hard": 1.35}


class CultivationService:
    def __init__(self, db: Session):
        self.db = db
        self.cultivation_repo = CultivationRepository(db)
        self.user_repo = UserRepository(db)

    def ensure_profile(self, user_id: UUID) -> CultivationProfile:
        profile = self.cultivation_repo.get_by_user(user_id)
        if profile is None:
            profile = self.cultivation_repo.create_default(user_id)
        return profile

    def get_overview(self, user_id: UUID) -> CultivationOverview:
        profile = self.ensure_profile(user_id)
        return CultivationOverview(
            realm_key=profile.realm_key,
            minor_stage=profile.minor_stage,
            cultivation=profile.cultivation,
            spirit_stones=profile.spirit_stones,
            merit=profile.merit,
            contribution=profile.contribution,
            mind_state=profile.mind_state,
            aptitude_points=profile.aptitude_points,
            cultivation_efficiency=profile.cultivation_efficiency,
            next_stage=self.get_next_stage(
                profile.realm_key, profile.minor_stage, profile.cultivation
            ),
        )

    def settle_todo_reward(
        self,
        user_id: UUID,
        source: str,
        base_exp: int,
        difficulty: str,
        quality: float = 1.0,
        importance: float = 1.0,
    ) -> RewardSettlement:
        try:
            difficulty_factor = DIFFICULTY_FACTORS[difficulty]
        except KeyError as exc:
            raise ValueError(f"Unknown difficulty: {difficulty}") from exc

        profile = self.ensure_profile(user_id)
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")

        cultivation = max(0, math.floor(
            base_exp
            * difficulty_factor
            * importance
            * profile.cultivation_efficiency
            * quality
        ))
        stones = max(1, math.floor(cultivation * 0.6))
        profile.cultivation += cultivation
        profile.spirit_stones += stones
        log = CultivationLog(
            user_id=user_id,
            source=source,
            cultivation_delta=cultivation,
            spirit_stones_delta=stones,
        )
        self.db.add(log)
        self.user_repo._update_experience_no_commit(user, cultivation)
        self.user_repo._update_coins_no_commit(user, stones)
        self.db.flush()
        return RewardSettlement(
            cultivation=cultivation,
            spirit_stones=stones,
            merit=0,
            efficiency=profile.cultivation_efficiency,
            log_id=log.id,
            legacy_exp=cultivation,
        )

    def get_next_stage(
        self, realm_key: str, minor_stage: int, cultivation: int
    ) -> StageProgress:
        thresholds = REALM_THRESHOLDS[realm_key]
        if realm_key == "qi_refining" and minor_stage == 1:
            current_threshold = 0
            next_threshold = 180
        else:
            index = max(0, min(minor_stage - 1, len(thresholds) - 1))
            current_threshold = 0 if index == 0 else thresholds[index - 1]
            next_threshold = thresholds[index]
        return StageProgress(
            realm_key=realm_key,
            minor_stage=minor_stage,
            cultivation=cultivation,
            current_threshold=current_threshold,
            next_threshold=next_threshold,
            remaining=max(0, next_threshold - cultivation),
        )
