"""Read-only companion milestones shared by return receipts and growth."""

from app.models.cultivation import TribulationAttempt
from app.models.cultivation_retreat import CultivationRetreat, EncounterEvent, UserEncounterRecord


COMPANIONS = (
    ('white_deer', '白鹿·衔芝', 3),
    ('spirit_fox', '灵狐·照夜', 7),
    ('cloud_crane', '玄鹤·临风', 14),
)


def get_companion_progress(db, user_id):
    count = db.query(CultivationRetreat.id).filter_by(user_id=user_id, status='completed').count()
    rare = db.query(UserEncounterRecord.id).join(
        EncounterEvent, EncounterEvent.id == UserEncounterRecord.encounter_id,
    ).filter(UserEncounterRecord.user_id == user_id,
             EncounterEvent.rarity.in_(('rare', 'epic', 'legendary'))).first() is not None
    breakthrough = db.query(TribulationAttempt.id).filter_by(user_id=user_id, success=True).first() is not None
    pets = [
        {'key': key, 'name': name, 'current': count, 'target': target,
         'unlocked': count >= target or (key == 'spirit_fox' and rare) or (key == 'cloud_crane' and breakthrough)}
        for key, name, target in COMPANIONS
    ]
    return {'successful_sessions': count, 'pets': pets,
            'next_unlock': next((pet for pet in pets if not pet['unlocked']), None)}
