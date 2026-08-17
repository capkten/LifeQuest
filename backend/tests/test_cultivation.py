def test_cultivation_tables_are_registered(db_session):
    from app.models.cultivation import CultivationProfile, CultivationLog
    from app.models.technique import TechniqueSlot

    assert CultivationProfile.__tablename__ == "cultivation_profiles"
    assert CultivationLog.__tablename__ == "cultivation_logs"
    assert TechniqueSlot.__tablename__ == "technique_slots"


def test_npc_user_id_is_non_nullable():
    from app.models.world import Npc

    assert Npc.__table__.c.user_id.nullable is False
