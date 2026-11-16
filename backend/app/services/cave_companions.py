from fastapi import HTTPException

from app.models.cave import CaveCompanionState, CaveRequest
from app.models.cultivation_retreat import CultivationRetreat
from app.repositories.user import UserRepository
from app.services import cultivation_retreat as retreat_lifecycle
from app.services.cave_progression import COMPANIONS, get_companion_progress
from app.services.transaction import rollback_on_error
from app.timezone import local_date


PET_STORIES = {
    'white_deer': ('common', '门前的白鹿轻轻衔来一枝草药，陪你安静坐下。', '完成 3 次入定，白鹿会来到门前。'),
    'spirit_fox': ('rare', '灵狐守着一盏小灯，把山间的新鲜事讲给你听。', '遇见一次稀有奇遇，或完成 7 次入定。'),
    'cloud_crane': ('epic', '玄鹤停在檐角，带来远方古卷的一页回声。', '完成一次境界突破，或完成 14 次入定。'),
}
PET_NOTES = {
    'white_deer': '衔芝沿着旧路找到一眼山泉，把清凉的水声带回门前。',
    'spirit_fox': '照夜在山灯旁听见一个小故事：有人把未写完的一页，认真收进了明天。',
    'cloud_crane': '临风从远山衔回一页旧卷，卷边写着：行到这里，也是一段风景。',
}
DAO_CHILD_LINES = (
    '蒲团已铺好，先照看眼前这一件事。', '你来时，灯便亮了。', '这一段专注，我替你记着。',
    '山风正好，慢慢坐稳。', '我们已经一起走过几段路。', '不必多说，我知道你会回来。',
)


class CaveCompanionService:
    def __init__(self, db):
        self.db = db

    def active_snapshot(self, user_id):
        state = self.db.query(CaveCompanionState).filter_by(user_id=user_id).first()
        if state is None or state.active_pet_key is None:
            return None
        return next({'key': key, 'name': name} for key, name, _ in COMPANIONS if key == state.active_pet_key)

    @rollback_on_error
    def get_companions(self, user_id):
        UserRepository(self.db).lock(user_id)
        result = self.snapshot(user_id)
        self.db.commit()
        return result

    @rollback_on_error
    def activate(self, user_id, key, request_id):
        from app.services.cave import CaveService

        UserRepository(self.db).lock(user_id)
        payload = {'key': key}
        previous = CaveService(self.db).replay(user_id, request_id, 'companion', payload)
        if previous is not None:
            self.db.commit()
            return previous
        current = self.snapshot(user_id)
        pet = next((pet for pet in current['pets'] if pet['key'] == key), None)
        if pet is None:
            raise HTTPException(status_code=404, detail='山中暂未见到这位伙伴。')
        if not pet['unlocked']:
            raise HTTPException(status_code=409, detail=pet['hint'])
        state = self.db.query(CaveCompanionState).filter_by(user_id=user_id).one()
        state.active_pet_key = key
        result = self.snapshot(user_id)
        self.db.add(CaveRequest(user_id=user_id, request_id=request_id, operation='companion', payload=payload, result=result))
        self.db.commit()
        return result

    def daily_note(self, user_id, active_pet):
        if active_pet is None:
            return None
        from app.services.cave import CaveService

        date = local_date(retreat_lifecycle.utc_now())
        daily = CaveService(self.db).get_daily_state(user_id, date)
        if daily.offline_note_key is None:
            daily.offline_note_key = f"pet:{active_pet['key']}:{date.isoformat()}"
            daily.offline_note = {'key': daily.offline_note_key, 'date': date.isoformat(),
                                  'companion_key': active_pet['key'], 'companion_name': active_pet['name'],
                                  'story': PET_NOTES[active_pet['key']]}
            self.db.flush()
        return daily.offline_note

    def snapshot(self, user_id):
        state = self.db.query(CaveCompanionState).filter_by(user_id=user_id).first()
        if state is None:
            state = CaveCompanionState(user_id=user_id, pet_unlocks={})
            self.db.add(state)
        progress = get_companion_progress(self.db, user_id)
        unlocks = dict(state.pet_unlocks)
        for pet in progress['pets']:
            if pet['unlocked'] and pet['key'] not in unlocks:
                unlocks[pet['key']] = retreat_lifecycle.utc_now().isoformat()
        state.pet_unlocks = unlocks
        self.db.flush()
        familiarity = min(5, progress['successful_sessions'])
        accompanied = [row.companion_snapshot['key'] for row in self.db.query(CultivationRetreat.companion_snapshot).filter_by(
            user_id=user_id, status='completed') if row.companion_snapshot]
        pets = []
        for milestone in progress['pets']:
            rarity, story, hint = PET_STORIES[milestone['key']]
            unlocked = milestone['key'] in unlocks
            pets.append({**milestone, 'unlocked': unlocked, 'rarity': rarity, 'story': story, 'hint': hint,
                         'first_unlocked_at': unlocks.get(milestone['key']),
                         'unlock_count': 1 if unlocked else 0,
                         'familiarity': min(5, accompanied.count(milestone['key'])),
                         'active': state.active_pet_key == milestone['key']})
        from app.services.cave_letters import CaveLetterService

        return {
            'dao_child': {'key': 'xiaoman', 'name': '小满', 'familiarity': familiarity,
                          'lines': list(DAO_CHILD_LINES[:familiarity + 1])},
            'active_pet_key': state.active_pet_key, 'pets': pets,
            'daily_note': self.daily_note(user_id, next((pet for pet in pets if pet['active']), None)),
            'seniors': CaveLetterService(self.db).seniors_snapshot(user_id),
        }
