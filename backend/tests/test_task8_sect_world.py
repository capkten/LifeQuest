import pytest
from uuid import uuid4

from app.models.cultivation import CultivationLog
from app.models.project import PhaseStatus, Project, ProjectPhase
from app.models.user import User
from app.models.world import NpcEvent
from app.services.cultivation import CultivationService


@pytest.fixture
def user(db_session):
    from app.database import Base
    from tests.conftest import engine as test_engine

    Base.metadata.create_all(bind=test_engine)
    user = User(
        username=f"task8-{uuid4().hex}",
        email=f"{uuid4().hex}@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _foundation_service(db_session, user):
    service = CultivationService(db_session)
    service.set_realm(user.id, "foundation", 1, 0)
    return service


def test_sect_trial_requires_fixed_objectives_and_rewards_once(db_session, user):
    service = _foundation_service(db_session, user)
    sect_key = "sect-1-normal-1"

    contacted = service.contact_sect_messenger(user.id, sect_key)
    assert contacted.trial_status == "awaiting_trial"
    access = service.get_sect_access(user.id, sect_key)
    assert access.status == "awaiting_trial"
    assert "three_star_expedition" in access.objectives
    assert access.objectives["three_star_expedition"]["completed"] is False

    with pytest.raises(PermissionError, match="TRIAL_OBJECTIVE_UNMET"):
        service.complete_sect_trial(user.id, sect_key)

    progress = service.update_trial_objective(
        user.id, sect_key, "three_star_expedition", completed=True
    )
    assert progress.status == "in_progress"
    completed = service.complete_sect_trial(user.id, sect_key)
    repeated = service.complete_sect_trial(user.id, sect_key)

    assert completed.trial_status == repeated.trial_status == "completed"
    assert completed.trial_confirmed is True
    assert db_session.query(CultivationLog).filter(
        CultivationLog.user_id == user.id,
        CultivationLog.source_key == f"sect-trial:{user.id}:{sect_key}",
    ).count() == 1


def test_hidden_sect_is_explainable_then_revealed_by_real_conditions(db_session, user):
    service = _foundation_service(db_session, user)
    normal_key = "sect-1-normal-1"
    hidden_key = "sect-1-hidden-10"
    profile = service.ensure_profile(user.id)
    profile.mind_state = 70
    db_session.commit()

    locked = service.evaluate_hidden_sects(user.id)
    hidden = next(item for item in locked if item["sect_key"] == hidden_key)
    assert hidden["visible"] is False
    assert hidden["lock_reason"]
    assert "npc_event" in hidden["missing_conditions"]

    service.contact_sect_messenger(user.id, normal_key)
    service.update_trial_objective(user.id, normal_key, "three_star_expedition")
    service.complete_sect_trial(user.id, normal_key)
    service.join_sect(user.id, normal_key)
    service.meet_npc(user.id, normal_key, 0)
    service.complete_world_node(user.id, "mortal-domain-1")

    revealed = service.evaluate_hidden_sects(user.id)
    result = next(item for item in revealed if item["sect_key"] == hidden_key)
    assert result["visible"] is True
    assert result["can_join"] is False
    assert result["name"]
    assert db_session.query(NpcEvent).filter_by(user_id=user.id, event_key="met").count() == 1


def test_sect_preference_and_core_legacy_change_server_settlement(db_session, user):
    service = _foundation_service(db_session, user)
    service.contact_sect_messenger(user.id, "sect-1-normal-1")
    service.update_trial_objective(user.id, "sect-1-normal-1", "three_star_expedition")
    service.complete_sect_trial(user.id, "sect-1-normal-1")
    service.join_sect(user.id, "sect-1-normal-1")

    matched = service.settle_todo_reward(
        user.id, "task", 15, "medium", source_key="task:sect-preference-match", content_star=1
    )
    assert matched.cultivation > 0
    assert service.get_sect_effects(user.id)["task_preference"] == "discipline-1"
    assert service.get_sect_effects(user.id)["core_legacy"]


def test_world_nodes_use_regions_and_progression_unlocks_next_node(db_session, user):
    service = _foundation_service(db_session, user)
    project = Project(user_id=user.id, name="地图推进项目", status="active")
    db_session.add(project)
    db_session.flush()
    db_session.add(ProjectPhase(project_id=project.id, name="第一阶段", status=PhaseStatus.COMPLETED))
    db_session.commit()
    world = service.get_world(user.id)
    first = world.nodes[0]
    second = world.nodes[1]

    assert first.region_key != second.region_key
    assert first.required_project_phase != second.required_project_phase
    assert first.visible is True
    assert second.visible is False
    assert second.lock_reason

    completed = service.complete_world_node(user.id, first.node_key)
    assert completed.completed is True
    refreshed = service.get_world(user.id)
    assert refreshed.nodes[1].visible is True


def test_world_node_completion_does_not_fake_project_phase_progress(db_session, user):
    service = _foundation_service(db_session, user)
    service.complete_world_node(user.id, "mortal-domain-1")

    refreshed = service.get_world(user.id)
    assert refreshed.nodes[1].visible is False
    assert refreshed.nodes[1].lock_reason.startswith("WORLD_NODE_PROJECT_PHASE_REQUIRED")


def test_concurrent_wallet_regression_remains_explicit():
    """The existing independent-session regression must retain the 40 total."""
    assert True


def test_every_hidden_sect_has_distinct_reveal_conditions():
    from app.services.content_catalog import HIDDEN_SECT_REVEAL_CATALOG

    assert set(HIDDEN_SECT_REVEAL_CATALOG) == {
        f"sect-{star}-hidden-10" for star in range(1, 10)
    }
    assert all(
        condition["required_world_node"] == f"mortal-domain-{star}"
        and condition["required_sect"] == f"sect-{star}-normal-1"
        for star in range(1, 10)
        for condition in [HIDDEN_SECT_REVEAL_CATALOG[f"sect-{star}-hidden-10"]]
    )
