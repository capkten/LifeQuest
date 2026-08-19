from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text


@pytest.fixture
def task7_user(db_session):
    from app.database import Base
    from tests.conftest import engine
    from app.models.user import User

    Base.metadata.create_all(bind=engine)
    user = User(
        username=f"task7-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_old_cultivation_log_schema_migrates_without_shop_items_table(tmp_path, monkeypatch):
    from app import main as main_module
    from app.database import Base

    database_engine = create_engine(f"sqlite:///{tmp_path / 'task7-legacy.sqlite'}")
    Base.metadata.create_all(bind=database_engine)
    with database_engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE shop_items")
        connection.exec_driver_sql("DROP TABLE cultivation_logs")
        connection.execute(text(
            "CREATE TABLE cultivation_logs ("
            "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, "
            "source VARCHAR(64) NOT NULL, source_key VARCHAR(128), "
            "cultivation_delta INTEGER NOT NULL DEFAULT 0, "
            "spirit_stones_delta INTEGER NOT NULL DEFAULT 0, "
            "merit_delta INTEGER NOT NULL DEFAULT 0, "
            "contribution_delta INTEGER NOT NULL DEFAULT 0, "
            "created_at DATETIME NOT NULL)"
        ))
    monkeypatch.setattr(main_module, "engine", database_engine)

    main_module._migrate_columns()

    columns = {column["name"] for column in inspect(database_engine).get_columns("cultivation_logs")}
    assert {
        "source_key",
        "aptitude_points_delta",
        "mind_state_delta",
        "efficiency_delta",
        "efficiency",
        "ready_for_tribulation",
    } <= columns
    database_engine.dispose()


def test_system_tribulation_pill_is_restored_and_immutable(db_session, task7_user):
    from fastapi import HTTPException
    from app.services.shop import ShopService
    from app.models.shop import ShopItem

    service = ShopService(db_session)
    service.seed_system_items(db_session)
    item = db_session.query(ShopItem).filter_by(item_key="tribulation-pill").one()
    item.name = "tampered"
    item.icon = "tampered-icon"
    item.coin_price = 1
    item.stock = 3
    item.is_active = False
    item.created_by = task7_user.id
    db_session.commit()

    service.seed_system_items(db_session)
    db_session.refresh(item)
    assert item.name == "渡劫丹"
    assert item.icon is None
    assert item.coin_price == 100
    assert item.stock == -1
    assert item.is_active is True
    assert item.created_by is None

    with pytest.raises(HTTPException) as update_error:
        service.get_mutable_item_for_user(item.id, task7_user.id)
    assert update_error.value.status_code == 403
    assert "system" in str(update_error.value.detail).lower()


def test_high_realm_prerequisites_do_not_treat_active_membership_as_mainline(db_session, task7_user):
    from app.models.todo import Goal, TaskStatus
    from app.models.world import Sect, SectMembership
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.seed_world(db_session)
    profile = service.set_realm(task7_user.id, "golden_core", 4, 2000)
    profile.mind_state = 80
    sect = db_session.query(Sect).filter(Sect.kind == "normal", Sect.star == 5).first()
    db_session.add(SectMembership(user_id=task7_user.id, sect_id=sect.id, status="active"))
    db_session.add(Goal(
        user_id=task7_user.id,
        title="Long goal",
        difficulty="very_hard",
        status=TaskStatus.IN_PROGRESS,
        progress=75,
    ))
    db_session.commit()

    preview = service.get_tribulation_preview(task7_user.id)
    prerequisites = {item.key: item for item in preview.prerequisites}
    assert {"sect_mainline", "high_star_trial", "realm_objective"} <= prerequisites.keys()
    assert prerequisites["sect_mainline"].current == 0
    assert prerequisites["sect_mainline"].satisfied is False
    assert prerequisites["high_star_trial"].satisfied is False
    assert prerequisites["realm_objective"].satisfied is False


def test_high_realm_prerequisites_ignore_unrelated_trials_and_objectives(db_session, task7_user):
    from app.models.cultivation import CultivationLog
    from app.models.world import Sect, SectAccessProgress, SectMembership
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.seed_world(db_session)
    service.set_realm(task7_user.id, "golden_core", 4, 2000)

    target_sect = db_session.query(Sect).filter(
        Sect.kind == "normal", Sect.star == 5
    ).first()
    unrelated_sect = db_session.query(Sect).filter(
        Sect.kind == "normal", Sect.star == 7
    ).first()
    db_session.add(SectMembership(
        user_id=task7_user.id, sect_id=target_sect.id, status="active"
    ))
    db_session.add(SectAccessProgress(
        user_id=task7_user.id,
        sect_id=unrelated_sect.id,
        trial_confirmed=True,
    ))
    db_session.add(CultivationLog(
        user_id=task7_user.id,
        source="trial_objective",
        source_key="realm-objective:unrelated-realm",
    ))
    db_session.commit()

    preview = service.get_tribulation_preview(task7_user.id)
    prerequisites = {item.key: item for item in preview.prerequisites}

    assert prerequisites["sect_mainline"].current == 0
    assert prerequisites["sect_mainline"].satisfied is False
    assert prerequisites["high_star_trial"].satisfied is True
    assert prerequisites["realm_objective"].current == 0
    assert prerequisites["realm_objective"].satisfied is False


def test_attempt_uses_preview_lock_code_before_inventory_validation(db_session, task7_user):
    from app.services.cultivation import CultivationService

    service = CultivationService(db_session)
    service.set_realm(task7_user.id, "qi_refining", 1, 0)
    preview = service.get_tribulation_preview(task7_user.id, pill_count=16)

    with pytest.raises(PermissionError) as error:
        service.attempt_tribulation(task7_user.id, 16)
    assert str(error.value).startswith(preview.lock_reason)


def test_direct_service_attempt_bounds_pills_before_consumption(db_session, task7_user, monkeypatch):
    from app.models.backpack import BackpackItem
    from app.models.shop import ShopItem
    from app.services.backpack import BackpackService
    from app.services.cultivation import CultivationService
    from app.services.shop import ShopService
    from tests.test_cultivation import _satisfy_tribulation_prerequisites

    service = CultivationService(db_session)
    service.seed_world(db_session)
    _satisfy_tribulation_prerequisites(service, task7_user.id, "qi_refining")
    service.set_realm(task7_user.id, "qi_refining", 9, 235)
    ShopService.seed_system_items(db_session)
    pill = db_session.query(ShopItem).filter_by(item_key="tribulation-pill").one()
    BackpackService(db_session).add_item(task7_user.id, pill.id, quantity=16)
    monkeypatch.setattr(service, "roll", lambda probability: False)

    service.attempt_tribulation(task7_user.id, 16)

    backpack = db_session.query(BackpackItem).filter_by(
        user_id=task7_user.id, shop_item_id=pill.id
    ).one()
    assert backpack.quantity == 1
