from functools import wraps

import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.repositories.user import UserRepository
from app.schemas.cultivation_retreat import RetreatStartRequest

from app.models.coin_transaction import CoinSource, CoinTransaction, CoinType
from app.models.cultivation import CultivationProfile
from app.models.cultivation_retreat import CultivationRetreat, EncounterEvent, UserEncounterRecord
from app.models.todo import Task, TaskStatus
from app.models.user import User
from app.schemas.cultivation_retreat import EncounterCatalogItem
from app.services.encounter_engine import EncounterEngine
from datetime import datetime, timezone
from app.timezone import as_utc, day_bounds_utc, local_date

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def rollback_retreat_on_error(method):
    @wraps(method)
    def guarded(*args, **kwargs):
        db = kwargs.get("db") if "db" in kwargs else args[0]
        try:
            return method(*args, **kwargs)
        except Exception:
            db.rollback()
            raise
    return guarded


class CultivationRetreatService:
    @staticmethod
    @rollback_retreat_on_error
    def start_retreat(
        db: Session,
        user_id: UUID,
        target_duration: int,
        todo_id: Optional[UUID] = None,
        *,
        commit: bool = True,
        mark_todo_complete: bool = False,
    ) -> CultivationRetreat:
        payload = RetreatStartRequest(target_duration=target_duration, todo_id=todo_id)
        target_duration, todo_id = payload.target_duration, payload.todo_id
        UserRepository(db).lock(user_id)
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

        from app.services.cave_companions import CaveCompanionService

        retreat = CultivationRetreat(
            user_id=user_id,
            companion_snapshot=CaveCompanionService(db).active_snapshot(user_id),
            todo_id=todo_id,
            todo_title=task.title if todo_id else None,
            mark_todo_complete=mark_todo_complete,
            target_duration=target_duration,
            started_at=utc_now(),
            status="active",
            rule_version="b_v1",
        )
        db.add(retreat)
        if commit:
            db.commit()
            db.refresh(retreat)
        else:
            db.flush()
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
    @rollback_retreat_on_error
    def abort_retreat(db: Session, user_id: UUID, retreat_id: UUID, *, commit: bool = True) -> CultivationRetreat:
        UserRepository(db).lock(user_id)
        claimed = db.query(CultivationRetreat).filter(
            CultivationRetreat.id == retreat_id,
            CultivationRetreat.user_id == user_id,
            CultivationRetreat.status == "active",
        ).update({CultivationRetreat.status: "settling"}, synchronize_session=False)
        if claimed != 1:
            settled = db.query(CultivationRetreat).populate_existing().filter(
                CultivationRetreat.id == retreat_id,
                CultivationRetreat.user_id == user_id,
                CultivationRetreat.status.in_(("completed", "aborted")),
            ).first()
            if settled is not None:
                if commit:
                    db.commit()
                    db.refresh(settled)
                return settled
            raise HTTPException(status_code=404, detail="Active retreat not found")
        retreat = (
            db.query(CultivationRetreat).populate_existing()
            .filter(
                CultivationRetreat.id == retreat_id,
                CultivationRetreat.user_id == user_id,
            )
            .first()
        )
        if not retreat or retreat.status != "settling":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active retreat not found",
            )

        if retreat.rule_version == "b_v1":
            return CultivationRetreatService._settle_b_retreat(db, user_id, retreat, abort=True, commit=commit)

        now = utc_now()
        retreat.status = "aborted"
        retreat.ended_at = now
        retreat.actual_duration = max(0, int((now - as_utc(retreat.started_at)).total_seconds() / 60))
        if commit:
            db.commit()
            db.refresh(retreat)
        else:
            db.flush()
        return retreat

    @staticmethod
    @rollback_retreat_on_error
    def complete_retreat(
        db: Session,
        user_id: UUID,
        retreat_id: UUID,
        mark_todo_complete: bool = False,
        force_encounter: bool = False,
        *,
        commit: bool = True,
    ) -> CultivationRetreat:
        UserRepository(db).lock(user_id)
        claimed = db.query(CultivationRetreat).filter(
            CultivationRetreat.id == retreat_id,
            CultivationRetreat.user_id == user_id,
            CultivationRetreat.status == "active",
        ).update({CultivationRetreat.status: "settling"}, synchronize_session=False)
        if claimed != 1:
            settled = db.query(CultivationRetreat).populate_existing().filter(
                CultivationRetreat.id == retreat_id,
                CultivationRetreat.user_id == user_id,
                CultivationRetreat.status.in_(("completed", "aborted")),
            ).first()
            if settled is not None:
                if commit:
                    db.commit()
                    db.refresh(settled)
                return settled
            raise HTTPException(status_code=404, detail="Active retreat not found")
        retreat = (
            db.query(CultivationRetreat).populate_existing()
            .filter(
                CultivationRetreat.id == retreat_id,
                CultivationRetreat.user_id == user_id,
            )
            .first()
        )
        if not retreat or retreat.status != "settling":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active retreat not found",
            )

        if retreat.rule_version == "b_v1":
            return CultivationRetreatService._settle_b_retreat(
                db, user_id, retreat, mark_todo_complete=mark_todo_complete, commit=commit,
            )

        now = utc_now()
        elapsed_seconds = max(0, (now - as_utc(retreat.started_at)).total_seconds())
        actual_minutes = int(elapsed_seconds / 60)
        retreat.actual_duration = actual_minutes
        retreat.ended_at = now

        # Anti-cheat: must reach at least 80% of target duration
        min_threshold_seconds = retreat.target_duration * 60 * 0.8
        if elapsed_seconds < min_threshold_seconds:
            retreat.status = "aborted"
            retreat.exp_gained = max(5, actual_minutes * 2) if actual_minutes > 0 else 0
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                UserRepository(db)._update_experience_no_commit(user, retreat.exp_gained)
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
            UserRepository(db)._update_experience_no_commit(user, retreat.exp_gained)
            UserRepository(db)._update_coins_no_commit(user, retreat.coins_gained)

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
            from app.services.todo import TodoService
            todo_service = TodoService(db)
            task = todo_service.get_task_for_user(retreat.todo_id, user_id)
            todo_service.complete_task(task, user_id, commit=False)

        if commit:
            db.commit()
            db.refresh(retreat)
        else:
            db.flush()
        return retreat

    @staticmethod
    def _settle_b_retreat(
        db: Session, user_id: UUID, retreat: CultivationRetreat,
        mark_todo_complete: bool = False, abort: bool = False, commit: bool = True,
    ) -> CultivationRetreat:
        from app.services.cultivation import CultivationService

        now = utc_now()
        elapsed_seconds = max(0, (now - as_utc(retreat.started_at)).total_seconds())
        elapsed = int(elapsed_seconds / 60)
        retreat.actual_duration = elapsed
        retreat.ended_at = now
        early = abort or elapsed_seconds < retreat.target_duration * 60 * 0.8
        retreat.status = "aborted" if early else "completed"
        start, end = day_bounds_utc(local_date(now))
        daily_qi = db.query(func.coalesce(func.sum(CultivationRetreat.qi_gained), 0)).filter(
            CultivationRetreat.user_id == user_id,
            CultivationRetreat.id != retreat.id,
            CultivationRetreat.ended_at >= start,
            CultivationRetreat.ended_at < end,
        ).scalar()
        retreat.qi_gained = min(elapsed, retreat.target_duration, max(0, 240 - daily_qi))
        daily_qi_total = daily_qi + retreat.qi_gained
        task_reward = None
        task_previously_completed = False
        if not early and mark_todo_complete and retreat.todo_id:
            from app.services.todo import TodoService
            todo_service = TodoService(db)
            task = todo_service.get_task_for_user(retreat.todo_id, user_id)
            task.cultivation_reward = None
            todo_service.complete_task(task, user_id, commit=False)
            task_reward = task.cultivation_reward
            if task_reward is not None and task_reward._already_settled:
                task_reward = None
            task_previously_completed = task_reward is None
        task_completed = task_reward is not None
        source_key = f"retreat:{retreat.id}"
        reward = CultivationService(db).settle_todo_reward(
            user_id, "retreat", retreat.qi_gained // (2 if task_completed else 4),
            "medium", source_key=source_key,
            # Zero credited qi produces a zero-delta settlement, including resources.
            content_star=1 if retreat.qi_gained > 0 else 0,
        )
        retreat.exp_gained = reward.cultivation
        retreat.coins_gained = reward.spirit_stones
        retreat.settlement_id = reward.log_id
        retreat.settlement_result = {
            "source": "retreat",
            "source_key": source_key,
            "conversion_rate": 0.5 if task_completed else 0.25,
            "daily_qi_total": daily_qi_total,
            "daily_qi_cap_reached": daily_qi_total >= 240,
            "task_completed": task_completed,
            "task_previously_completed": task_previously_completed,
            "retreat_reward": reward.model_dump(mode="json"),
            "task_reward": task_reward.model_dump(mode="json") if task_reward else None,
        }
        if retreat.coins_gained > 0:
            db.add(CoinTransaction(
                user_id=user_id, amount=retreat.coins_gained,
                type=CoinType.EARN.value, source="retreat", source_id=str(retreat.id),
                description=f"闭关入定收益 ({retreat.qi_gained}灵气)",
            ))
        from app.services.retreat_return import freeze_return
        retreat.return_summary = freeze_return(db, retreat)
        if commit:
            db.commit()
            db.refresh(retreat)
        else:
            db.flush()
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
