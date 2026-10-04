import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.coin_transaction import CoinSource, CoinTransaction, CoinType
from app.models.cultivation import CultivationProfile
from app.models.cultivation_retreat import CultivationRetreat, EncounterEvent, UserEncounterRecord
from app.models.todo import Task, TaskStatus
from app.models.user import User
from app.schemas.cultivation_retreat import EncounterCatalogItem
from app.services.encounter_engine import EncounterEngine
from datetime import datetime, timezone
from app.timezone import as_utc

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CultivationRetreatService:
    @staticmethod
    def start_retreat(
        db: Session,
        user_id: UUID,
        target_duration: int,
        todo_id: Optional[UUID] = None,
    ) -> CultivationRetreat:
        # Check for existing active retreat
        active = (
            db.query(CultivationRetreat)
            .filter(
                CultivationRetreat.user_id == user_id,
                CultivationRetreat.status == "active",
            )
            .first()
        )
        if active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has an active cultivation retreat session",
            )

        # Check bound todo ownership
        if todo_id:
            task = db.query(Task).filter(Task.id == todo_id).first()
            if not task or task.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found or not owned by user",
                )

        retreat = CultivationRetreat(
            user_id=user_id,
            todo_id=todo_id,
            target_duration=target_duration,
            started_at=utc_now(),
            status="active",
        )
        db.add(retreat)
        db.commit()
        db.refresh(retreat)
        return retreat

    @staticmethod
    def get_active_retreat(db: Session, user_id: UUID) -> Optional[CultivationRetreat]:
        return (
            db.query(CultivationRetreat)
            .filter(
                CultivationRetreat.user_id == user_id,
                CultivationRetreat.status == "active",
            )
            .first()
        )

    @staticmethod
    def abort_retreat(db: Session, user_id: UUID, retreat_id: UUID) -> CultivationRetreat:
        retreat = (
            db.query(CultivationRetreat)
            .filter(
                CultivationRetreat.id == retreat_id,
                CultivationRetreat.user_id == user_id,
            )
            .first()
        )
        if not retreat or retreat.status != "active":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active retreat not found",
            )

        now = utc_now()
        retreat.status = "aborted"
        retreat.ended_at = now
        retreat.actual_duration = max(0, int((now - as_utc(retreat.started_at)).total_seconds() / 60))
        db.commit()
        db.refresh(retreat)
        return retreat

    @staticmethod
    def complete_retreat(
        db: Session,
        user_id: UUID,
        retreat_id: UUID,
        mark_todo_complete: bool = False,
        force_encounter: bool = False,
    ) -> CultivationRetreat:
        retreat = (
            db.query(CultivationRetreat)
            .filter(
                CultivationRetreat.id == retreat_id,
                CultivationRetreat.user_id == user_id,
            )
            .first()
        )
        if not retreat or retreat.status != "active":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active retreat not found",
            )

        now = utc_now()
        actual_minutes = max(0, int((now - as_utc(retreat.started_at)).total_seconds() / 60))
        retreat.actual_duration = actual_minutes
        retreat.ended_at = now

        # Anti-cheat: must reach at least 80% of target duration
        min_threshold = int(retreat.target_duration * 0.8)
        if actual_minutes < min_threshold:
            retreat.status = "aborted"
            retreat.exp_gained = max(5, actual_minutes * 2)
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.experience = (user.experience or 0) + retreat.exp_gained
            db.commit()
            db.refresh(retreat)
            return retreat

        # Valid completion
        retreat.status = "completed"
        base_exp = retreat.target_duration * 10
        base_coins = retreat.target_duration * 5
        retreat.exp_gained = base_exp
        retreat.coins_gained = base_coins

        # Retrieve user realm
        profile = db.query(CultivationProfile).filter(CultivationProfile.user_id == user_id).first()
        realm_level = 1
        if profile:
            try:
                from app.services.cultivation import REALM_ORDER
                realm_level = REALM_ORDER.index(profile.realm_key) + 1
            except Exception:
                realm_level = 1

        # Roll encounter
        encounter = EncounterEngine.roll_encounter(
            db=db,
            user_id=str(user_id),
            realm_level=realm_level,
            duration_minutes=retreat.target_duration,
            streak_days=0,
            force_hit=force_encounter,
        )

        if encounter:
            retreat.encounter_id = encounter.id
            retreat.encounter_result = {
                "id": encounter.id,
                "title": encounter.title,
                "story_text": encounter.story_text,
                "rarity": encounter.rarity,
                "reward_type": encounter.reward_type,
                "reward_payload": encounter.reward_payload,
            }
            payload = encounter.reward_payload or {}
            if "exp" in payload:
                retreat.exp_gained += payload["exp"]
            if "coins" in payload:
                retreat.coins_gained += payload["coins"]

            # Record encounter codex
            user_enc = (
                db.query(UserEncounterRecord)
                .filter(
                    UserEncounterRecord.user_id == user_id,
                    UserEncounterRecord.encounter_id == encounter.id,
                )
                .first()
            )
            if user_enc:
                user_enc.unlock_count += 1
                user_enc.last_retreat_id = retreat.id
            else:
                new_enc = UserEncounterRecord(
                    user_id=user_id,
                    encounter_id=encounter.id,
                    unlock_count=1,
                    last_retreat_id=retreat.id,
                )
                db.add(new_enc)

        # Grant user rewards
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.experience = (user.experience or 0) + retreat.exp_gained
            user.coins = (user.coins or 0) + retreat.coins_gained

        if profile:
            profile.cultivation = (profile.cultivation or 0) + retreat.exp_gained
            profile.spirit_stones = (profile.spirit_stones or 0) + retreat.coins_gained

        if retreat.coins_gained > 0:
            coin_tx = CoinTransaction(
                user_id=user_id,
                amount=retreat.coins_gained,
                type=CoinType.EARN.value,
                source=CoinSource.OTHER.value,
                source_id=str(retreat.id),
                description=f"闭关入定收益 ({retreat.target_duration}分钟)",
            )
            db.add(coin_tx)

        # Mark todo complete if requested
        if mark_todo_complete and retreat.todo_id:
            task = db.query(Task).filter(Task.id == retreat.todo_id, Task.user_id == user_id).first()
            if task and task.status != TaskStatus.COMPLETED:
                task.status = TaskStatus.COMPLETED
                task.completed_at = utc_now()

        db.commit()
        db.refresh(retreat)
        return retreat

    @staticmethod
    def get_history(
        db: Session,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[CultivationRetreat]:
        return (
            db.query(CultivationRetreat)
            .filter(CultivationRetreat.user_id == user_id)
            .order_by(CultivationRetreat.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_catalog(db: Session, user_id: UUID) -> List[EncounterCatalogItem]:
        EncounterEngine.seed_events(db)
        events = db.query(EncounterEvent).order_by(EncounterEvent.min_realm_level.asc()).all()
        records = {
            r.encounter_id: r
            for r in db.query(UserEncounterRecord).filter(UserEncounterRecord.user_id == user_id).all()
        }

        result = []
        for e in events:
            rec = records.get(e.id)
            result.append(
                EncounterCatalogItem(
                    id=e.id,
                    title=e.title,
                    story_text=e.story_text,
                    rarity=e.rarity,
                    min_realm_level=e.min_realm_level,
                    reward_type=e.reward_type,
                    unlocked=rec is not None,
                    unlock_count=rec.unlock_count if rec else 0,
                    first_unlocked_at=rec.first_unlocked_at if rec else None,
                )
            )
        return result
