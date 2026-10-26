import json
from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP

from app.models.project import Project
from app.models.user import User
from app.schemas.finance import AccountCreate, RecurringCreate
from app.schemas.project import ProjectCreate
from app.services.finance import FinanceService
from app.services.project import ProjectService


@pytest.fixture
def management(database):
    from app.mcp.management import register
    import mcp_server
    users = [User(username=uuid4().hex, email=f'{uuid4().hex}@example.com', password_hash='private') for _ in range(2)]
    database.add_all(users)
    database.commit()
    identity = [users[0].id]
    class Context:
        def __enter__(self): return database
        def __exit__(self, *args): database.rollback()
    server = FastMCP('management-test')
    tools = register(server, lambda db: identity[0], mcp_server._serialize, Context)
    assert set(server._tool_manager._tools) == set(tools)
    return tools, database, users, identity


def test_start_project_preserves_dates_and_guards_state_and_ownership(management):
    tools, db, users, identity = management
    svc = ProjectService(db)
    svc.create_project(users[0].id, ProjectCreate(name='Launch', start_date=date(2026, 10, 26), end_date=date(2026, 11, 1)))
    project = db.query(Project).filter_by(user_id=users[0].id).one()
    result = tools['start_project'](str(project.id))
    assert result['status'] == 'active'
    assert result['start_date'] == '2026-10-26' and result['end_date'] == '2026-11-01'
    assert result['total_tasks'] == 0 and result['progress'] == 0
    assert tools['start_project'](str(project.id))['status'] == 'active'
    assert 'password_hash' not in json.dumps(result)
    identity[0] = users[1].id
    with pytest.raises(HTTPException): tools['start_project'](str(project.id))
    identity[0] = users[0].id
    svc.complete_project(project)
    with pytest.raises(HTTPException): tools['start_project'](str(project.id))


def test_update_recurring_uses_validated_fields_and_account_ownership(management):
    tools, db, users, identity = management
    svc = FinanceService(db)
    accounts = [svc.create_account(user.id, AccountCreate(name='Cash')) for user in users]
    replacement = svc.create_account(users[0].id, AccountCreate(name='Replacement'))
    recurring = svc.create_recurring(users[0].id, RecurringCreate(account_id=accounts[0].id, type='expense', amount=10, frequency='monthly', next_date=date(2026, 11, 1)))
    result = tools['update_recurring_transaction'](str(recurring.id), {'amount': 12.345, 'account_id': str(replacement.id), 'next_date': '2026-12-01', 'is_active': False})
    assert result['amount'] == 12.35
    assert result['account_id'] == str(replacement.id)
    assert result['next_date'] == '2026-12-01' and result['is_active'] is False
    assert 'password_hash' not in json.dumps(result)
    with pytest.raises(HTTPException): tools['update_recurring_transaction'](str(recurring.id), {'account_id': str(accounts[1].id)})
    db.refresh(recurring)
    assert recurring.account_id == replacement.id
    identity[0] = users[1].id
    with pytest.raises(ValueError, match='Recurring transaction not found'):
        tools['update_recurring_transaction'](str(recurring.id), {'amount': 99})
    identity[0] = users[0].id
    for invalid in [{'amount': 0}, {'user_id': str(users[1].id)}, {'is_active': None}, {'next_date': 'invalid'}]:
        with pytest.raises(ValueError): tools['update_recurring_transaction'](str(recurring.id), invalid)
    db.refresh(recurring)
    assert float(recurring.amount) == 12.35
