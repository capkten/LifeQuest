from uuid import uuid4

import pytest
from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP

from app.models.user import User


@pytest.fixture
def daily_tools(database):
    from app.mcp.daily import register
    import mcp_server
    owner = User(username=uuid4().hex, email=f'{uuid4().hex}@test.invalid', password_hash='x', coins=100)
    other = User(username=uuid4().hex, email=f'{uuid4().hex}@test.invalid', password_hash='x')
    database.add_all([owner, other])
    database.commit()
    identity = [owner.id]
    class SessionContext:
        def __enter__(self): return database
        def __exit__(self, *args): database.rollback()
    server = FastMCP('daily-test')
    tools = register(server, lambda db: identity[0], mcp_server._serialize, SessionContext)
    return tools, database, owner, other, identity, server


def test_shop_purchase_retry_refund_and_ownership(daily_tools):
    tools, db, owner, other, identity, server = daily_tools
    item = tools['create_shop_item'](name='Tea', coin_price=10, stock=5, category='consumable')
    exchange = tools['purchase_shop_item'](item['id'], 'stable-request', quantity=2)
    assert tools['purchase_shop_item'](item['id'], 'stable-request', quantity=2)['id'] == exchange['id']
    db.refresh(owner)
    assert owner.coins == 80
    backpack = tools['list_backpack_items']()
    assert len(backpack) == 1 and backpack[0]['quantity'] == 2
    identity[0] = other.id
    for name, argument in [('get_shop_exchange', exchange['id']), ('refund_shop_exchange', exchange['id']), ('get_backpack_item', backpack[0]['id']), ('get_shop_item', item['id'])]:
        with pytest.raises(HTTPException): tools[name](argument)
    identity[0] = owner.id
    tools['refund_shop_exchange'](exchange['id'])
    db.refresh(owner)
    assert owner.coins == 100
    assert tools['get_coin_totals']()['total_spent'] == 20
    assert tools['get_coin_history']()['count'] == 2


def test_daily_reads_validation_and_registry(daily_tools):
    tools, db, owner, other, identity, server = daily_tools
    assert len(server._tool_manager._tools) == len(tools)
    assert tools['get_checkin_status']()['checked_in'] is False
    assert isinstance(tools['get_calendar_events']('2026-01-01', '2026-01-02'), list)
    for name in ['get_task_trends', 'get_coin_trends', 'get_habit_stats']:
        with pytest.raises(ValueError): tools[name]('bad')
    with pytest.raises(ValueError): tools['use_backpack_item'](str(uuid4()), 0)
    with pytest.raises(ValueError): tools['get_calendar_events']('2026-02-01', '2026-01-01')


def test_backpack_operations_and_shop_crud(daily_tools):
    tools, db, owner, other, identity, server = daily_tools
    item = tools['create_shop_item']('Equipment', category='gear', stock=5)
    assert tools['update_shop_item'](item['id'], {'description': 'test'})['description'] == 'test'
    purchase = tools['purchase_shop_item'](item['id'], 'gear-purchase', quantity=2)
    owned = tools['list_backpack_items']()[0]
    assert tools['equip_backpack_item'](owned['id'])['status'] == 'equipped'
    with pytest.raises(HTTPException): tools['refund_shop_exchange'](purchase['id'])
    assert tools['unequip_backpack_item'](owned['id'])['status'] == 'active'
    tools['discard_backpack_item'](owned['id'])
    assert any(entry['action'] == 'discard' for entry in tools['get_backpack_history']())
    consumable = tools['create_shop_item']('Consumable', category='consumable')
    tools['purchase_shop_item'](consumable['id'], 'consumable-purchase')
    consumable_owned = next(row for row in tools['list_backpack_items']() if row['shop_item_id'] == consumable['id'])
    tools['use_backpack_item'](consumable_owned['id'])
    temporary = tools['create_shop_item']('Temporary')
    assert tools['delete_shop_item'](temporary['id'])['deleted']
    with pytest.raises(HTTPException): tools['get_shop_item'](temporary['id'])


def test_detail_reads_and_completion_rewards_share_services(daily_tools):
    from app.schemas.todo import TaskCreate, HabitCreate, GoalCreate, SubtaskCreate
    from app.services.todo import TodoService
    from app.services.checkin import CheckinService
    tools, db, owner, other, identity, server = daily_tools
    svc = TodoService(db)
    task = svc.create_task(owner.id, TaskCreate(title='Task'))
    habit = svc.create_habit(owner.id, HabitCreate(title='Habit'))
    goal = svc.create_goal(owner.id, GoalCreate(title='Goal'))
    subtask = svc.create_subtask(SubtaskCreate(task_id=task.id, title='Part'))
    for kind, entity in [('task', task), ('habit', habit), ('goal', goal), ('subtask', subtask)]:
        assert tools[f'get_{kind}'](str(entity.id))['title']
        identity[0] = other.id
        with pytest.raises(HTTPException): tools[f'get_{kind}'](str(entity.id))
        identity[0] = owner.id
    svc.complete_task(task, owner.id)
    svc.complete_habit(habit, owner.id)
    db.refresh(owner)
    balance = owner.coins
    svc.complete_task(task, owner.id)
    svc.complete_habit(habit, owner.id)
    db.refresh(owner)
    assert owner.coins == balance
    CheckinService(db).checkin(owner.id)
    assert tools['get_checkin_status']()['checked_in'] is True
    db.refresh(owner)
    balance = owner.coins
    tools['get_checkin_status']()
    db.refresh(owner)
    assert owner.coins == balance


def test_achievement_title_metadata_and_activation_permissions(daily_tools):
    from app.services.achievement import AchievementService
    from app.services.title import TitleService
    tools, db, owner, other, identity, server = daily_tools
    achievements = AchievementService(db)
    achievements.seed_achievements()
    achievements.check_and_unlock(owner.id, 'task_count', 1)
    titles = TitleService(db)
    titles.seed_titles()
    titles.check_and_unlock(owner.id, 'level', 1)
    assert tools['list_achievements']()
    assert tools['list_titles']()
    earned = tools['get_user_achievements']()
    assert earned[0]['achievement']['name']
    unlocked = tools['get_user_titles']()
    title = unlocked[0]['title']
    tools['activate_title'](title['id'])
    db.refresh(owner)
    assert owner.title == title['name']
    identity[0] = other.id
    assert tools['get_user_titles']() == []
    assert tools['get_user_achievements']() == []
    with pytest.raises(HTTPException): tools['activate_title'](title['id'])


def test_habit_and_backpack_response_fields(daily_tools):
    from app.schemas.todo import HabitCreate
    from app.services.todo import TodoService
    tools, db, owner, other, identity, server = daily_tools
    svc = TodoService(db)
    habit = svc.create_habit(owner.id, HabitCreate(title='Read status'))
    assert tools['get_habit'](str(habit.id))['completed_today'] is False
    svc.complete_habit(habit, owner.id)
    assert tools['get_habit'](str(habit.id))['completed_today'] is True
    shop = tools['create_shop_item']('Gear', category='gear')
    tools['purchase_shop_item'](shop['id'], 'schema-purchase')
    item = tools['list_backpack_items']()[0]
    assert item['is_equipped'] is False
    assert tools['equip_backpack_item'](item['id'])['is_equipped'] is True
    assert tools['get_backpack_history']()[0]['action_type']
