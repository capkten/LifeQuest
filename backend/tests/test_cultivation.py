def test_cultivation_tables_are_registered(db_session):
    from app.models.cultivation import CultivationProfile, CultivationLog
    from app.models.technique import TechniqueSlot

    assert CultivationProfile.__tablename__ == "cultivation_profiles"
    assert CultivationLog.__tablename__ == "cultivation_logs"
    assert TechniqueSlot.__tablename__ == "technique_slots"
