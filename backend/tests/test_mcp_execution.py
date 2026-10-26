from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP

from app.models.user import User
from app.schemas.todo import TaskCreate
from app.services.todo import TodoService
from app.services.task_schedule import TaskScheduleService


@pytest.fixture
def execution(database, monkeypatch):
    from app.mcp.execution import register
    import mcp_server
    owner = User(username=uuid4().hex, email=f'{uuid4().hex}@example.com', password_hash='unused')
    other = User(username=uuid4().hex, email=f'{uuid4().hex}@example.com', password_hash='unused')
    database.add_all([owner, other])
    database.commit()
    identity = [owner.id]
    class Context:
        def __enter__(self): return database
        def __exit__(self, *args): database.rollback()
    tools = register(FastMCP('execution'), lambda db: identity[0], mcp_server._serialize, Context)
    # UTC Sunday evening is Monday under the business China day boundary.
    now = datetime(2026, 8, 30, 16, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(TaskScheduleService, '_now_utc', classmethod(lambda cls: now))
    return tools, database, owner, other, identity


def test_schedule_snooze_move_and_occurrence_reward_replay(execution):
    tools, db, owner, other, identity = execution
    svc = TodoService(db)
    task = svc.create_task(owner.id, TaskCreate(title='Daily', deadline='2026-08-31T10:00:00+08:00', schedule={'rule_type': 'daily', 'starts_on': '2026-08-31'}))
    state = tools['snooze_task'](str(task.id), '2026-08-31T11:00:00+08:00')
    assert state['occurrence_date'] == '2026-08-31'
    assert state['snoozed_until']
    moved = tools['reschedule_task'](str(task.id), occurrence_date='2026-08-31', new_occurrence_date='2026-09-01')
    assert moved['occurrence_date'] == '2026-09-01'
    svc.complete_task(task, owner.id, date(2026, 9, 1))
    db.refresh(owner)
    balance = owner.coins
    svc.complete_task(task, owner.id, date(2026, 9, 1))
    db.refresh(owner)
    assert owner.coins == balance
    identity[0] = other.id
    with pytest.raises(HTTPException): tools['snooze_task'](str(task.id), '2026-09-02T10:00:00+08:00')
    with pytest.raises(HTTPException): tools['reschedule_task'](str(task.id), deadline='2026-09-02T10:00:00+08:00')


def test_review_action_center_privacy_and_validation(execution):
    tools, db, owner, other, identity = execution
    svc = TodoService(db)
    owned = svc.create_task(owner.id, TaskCreate(title='Owner task', deadline='2026-08-31T12:00:00+08:00', priority='high'))
    secret = svc.create_task(other.id, TaskCreate(title='Secret other task', deadline='2026-08-31T12:00:00+08:00', priority='high'))
    owned.created_at = secret.created_at = datetime(2026, 8, 30, 16, tzinfo=timezone.utc)
    db.commit()
    center = tools['get_action_center']('2026-08-31')
    assert center['timezone'] == 'Asia/Shanghai'
    assert 'Owner task' in str(center) and 'Secret other task' not in str(center)
    review = tools['get_weekly_review']('2026-08-31')
    assert review['timezone'] == 'Asia/Shanghai'
    assert 'Owner task' in str(review) and 'Secret other task' not in str(review)
    assert tools['get_weekly_review']('2026-08-31') == review
    with pytest.raises(ValueError): tools['get_weekly_review']('2026-09-01')
    with pytest.raises(ValueError): tools['reschedule_task'](str(owned.id))


@pytest.mark.parametrize("kind", ["task", "goal", "project"])
def test_note_links_both_sides_metadata_permissions_and_unlink(execution, kind):
    from app.schemas.note import NotebookCreate, NoteCreate
    from app.services.note import NoteService
    tools, db, owner, other, identity = execution
    notes = NoteService(db)
    notebook = notes.create_notebook(owner.id, NotebookCreate(name='Links'))
    note = notes.create_note(notebook.id, owner.id, NoteCreate(title='Linked plan', content='private'))
    from app.schemas.todo import GoalCreate
    from app.schemas.project import ProjectCreate
    from app.services.project import ProjectService
    from app.models.project import Project
    if kind == 'task':
        target = TodoService(db).create_task(owner.id, TaskCreate(title='Linked target'))
    elif kind == 'goal':
        target = TodoService(db).create_goal(owner.id, GoalCreate(title='Linked target'))
    else:
        ProjectService(db).create_project(owner.id, ProjectCreate(name='Linked target'))
        target = db.query(Project).filter_by(user_id=owner.id).one()
    linked = tools['create_note_link'](str(note.id), kind, str(target.id))
    assert linked['title'] == 'Linked target' and linked['kind'] == kind
    assert tools['list_note_links'](str(note.id)) == [linked]
    backlinks = tools['list_target_notes'](kind, str(target.id))
    assert backlinks[0]['title'] == 'Linked plan' and '/notes/' in backlinks[0]['url']
    with pytest.raises(ValueError): tools['create_note_link'](str(note.id), kind, str(target.id))
    identity[0] = other.id
    for callback in [lambda: tools['list_note_links'](str(note.id)), lambda: tools['list_target_notes'](kind, str(target.id)), lambda: tools['delete_note_link'](str(note.id), kind, str(target.id))]:
        with pytest.raises((ValueError, PermissionError)): callback()
    identity[0] = owner.id
    assert tools['delete_note_link'](str(note.id), kind, str(target.id))['deleted']
    assert tools['list_note_links'](str(note.id)) == []
    assert tools['list_target_notes'](kind, str(target.id)) == []
    with pytest.raises(ValueError): tools['list_target_notes']('unknown', str(target.id))


def test_shared_note_links_hide_other_users_targets_and_require_write_access(execution):
    from app.schemas.note import NotebookCreate, NoteCreate
    from app.services.note import NoteService
    tools, db, owner, other, identity = execution
    notes = NoteService(db)
    notebook = notes.create_notebook(owner.id, NotebookCreate(name='Shared'))
    note = notes.create_note(notebook.id, owner.id, NoteCreate(title='Shared note'))
    task = TodoService(db).create_task(owner.id, TaskCreate(title='Private target'))
    tools['create_note_link'](str(note.id), 'task', str(task.id))
    notes.add_notebook_member(notebook.id, owner.id, other.username, 'viewer')
    identity[0] = other.id
    assert tools['list_note_links'](str(note.id)) == []
    other_task = TodoService(db).create_task(other.id, TaskCreate(title='Viewer task'))
    with pytest.raises(PermissionError): tools['create_note_link'](str(note.id), 'task', str(other_task.id))
    notes.update_notebook_member(notebook.id, owner.id, other.id, 'editor')
    tools['create_note_link'](str(note.id), 'task', str(other_task.id))
    assert [row['title'] for row in tools['list_note_links'](str(note.id))] == ['Viewer task']
    identity[0] = owner.id
    assert [row['title'] for row in tools['list_note_links'](str(note.id))] == ['Private target']
