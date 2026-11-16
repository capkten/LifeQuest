from app.models.cultivation_retreat import EncounterEvent, UserEncounterRecord
from app.models.technique import Technique, LearnedTechnique
from app.models.world import WorldNode, WorldNodeProgress
from app.repositories.user import UserRepository
from app.services.cave_companions import CaveCompanionService
from app.services.content_catalog import WORLD_NODE_CATALOG, TECHNIQUE_CATALOG
from app.services.encounter_engine import DEFAULT_ENCOUNTERS
from app.services.transaction import rollback_on_error


def codex_entry(key, name, story, hint, unlocked=False, first_unlocked_at=None, unlock_count=0, rarity='common'):
    return {'key': key, 'name': name, 'story': story, 'hint': hint, 'rarity': rarity,
            'unlocked': unlocked, 'first_unlocked_at': first_unlocked_at, 'unlock_count': unlock_count}


def category(key, name, entries):
    return {'key': key, 'name': name, 'entries': entries, 'total': len(entries),
            'unlocked': sum(entry['unlocked'] for entry in entries)}


class CaveGrowthService:
    def __init__(self, db):
        self.db = db

    @rollback_on_error
    def get_growth(self, user_id):
        from app.services.cave_progression import get_companion_progress
        from app.services.cultivation import CultivationService

        UserRepository(self.db).lock(user_id)
        companions = CaveCompanionService(self.db).snapshot(user_id)
        codex = self.codex_snapshot(user_id, companions)
        progress = get_companion_progress(self.db, user_id)
        result = {'realm': CultivationService(self.db).get_overview(user_id).model_dump(mode='json'),
                  'successful_sessions': progress['successful_sessions'], 'next_unlock': progress['next_unlock'],
                  'codex_counts': [{key: item[key] for key in ('key', 'name', 'unlocked', 'total')} for item in codex['categories']],
                  'companions': companions}
        self.db.commit()
        return result

    @rollback_on_error
    def get_codex(self, user_id):
        UserRepository(self.db).lock(user_id)
        result = self.codex_snapshot(user_id)
        self.db.commit()
        return result

    def codex_snapshot(self, user_id, companions=None):
        companions = companions or CaveCompanionService(self.db).snapshot(user_id)
        events = {event['id']: event for event in DEFAULT_ENCOUNTERS}
        for event in self.db.query(EncounterEvent).order_by(EncounterEvent.id):
            events[event.id] = {'id': event.id, 'title': event.title, 'story_text': event.story_text, 'rarity': event.rarity}
        records = {row.encounter_id: row for row in self.db.query(UserEncounterRecord).filter_by(user_id=user_id)}
        encounters = []
        for key, event in events.items():
            record = records.get(key)
            encounters.append(codex_entry(key, event['title'], event['story_text'], '入定收功时，或许会遇见。',
                record is not None, record.first_unlocked_at if record else None,
                record.unlock_count if record else 0, event['rarity']))

        locations = dict(WORLD_NODE_CATALOG)
        nodes = self.db.query(WorldNode).order_by(WorldNode.sort_order, WorldNode.node_key).all()
        progress = {row.node_id: row for row in self.db.query(WorldNodeProgress).filter_by(user_id=user_id, completed=True)}
        node_progress = {}
        for node in nodes:
            locations[node.node_key] = {'name': node.name, 'description': node.description}
            node_progress[node.node_key] = progress.get(node.id)
        location_entries = []
        for key, node in locations.items():
            record = node_progress.get(key)
            location_entries.append(codex_entry(key, node['name'], node.get('description') or '山川等你慢慢走过。',
                '在凡界探索这处地点。', record is not None, record.completed_at if record else None, 1 if record else 0))

        techniques = dict(TECHNIQUE_CATALOG)
        learned = {row.technique_id: row for row in self.db.query(LearnedTechnique).filter_by(user_id=user_id)}
        technique_progress = {}
        for technique in self.db.query(Technique).order_by(Technique.technique_key):
            techniques[technique.technique_key] = {'name': technique.name, 'description': technique.description}
            technique_progress[technique.technique_key] = learned.get(technique.id)
        technique_entries = []
        for key, technique in techniques.items():
            record = technique_progress.get(key)
            technique_entries.append(codex_entry(key, technique['name'], technique.get('description') or '一页功法，一段心得。',
                '学习这门功法，留下自己的心得。', record is not None, record.learned_at if record else None, 1 if record else 0))

        pets = [codex_entry(pet['key'], pet['name'], pet['story'], pet['hint'], pet['unlocked'],
                            pet['first_unlocked_at'], pet['unlock_count'], pet['rarity']) for pet in companions['pets']]
        from app.services.cave_letters import CaveLetterService

        seniors = [codex_entry(senior['key'], senior['name'], senior['story'], senior['hint'], senior['unlocked'],
                               senior['first_unlocked_at'], senior['unlock_count'], senior['rarity'])
                   for senior in companions['seniors']]
        seniors.extend(CaveLetterService(self.db).codex_stories(user_id))
        return {'categories': [category('encounters', '奇遇', encounters), category('pets', '灵宠', pets),
                               category('seniors', '同门', seniors), category('locations', '地点', location_entries),
                               category('techniques', '功法', technique_entries)]}
