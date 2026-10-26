"""Daily business tools: authenticated thin adapters around existing services."""
from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from app.schemas.todo import HabitResponse
from app.schemas.backpack import BackpackItemResponse, UsageHistoryResponse
from app.schemas.achievement import AchievementResponse, UserAchievementResponse
from app.schemas.title import TitleResponse, UserTitleResponse
from app.services.achievement import AchievementService
from app.services.title import TitleService
from app.models.backpack import ItemStatus
from app.models.coin_transaction import CoinType
from app.schemas.shop import ShopItemCreate, ShopItemUpdate, ExchangeHistoryCreate
from app.services.shop import ShopService
from app.services.backpack import BackpackService
from app.services.coin import CoinService
from app.services.stats import StatsService
from app.services.calendar import CalendarService
from app.services.checkin import CheckinService
from app.services.todo import TodoService


def register(mcp, resolve_user_id, serialize, session_factory):
    """Register tools with injected authentication and database lifecycle."""
    tools = {}

    def tool(function):
        tools[function.__name__] = function
        mcp.tool()(function)
        return function

    def run(service, operation, response=None):
        with session_factory() as db:
            uid = resolve_user_id(db)
            result = operation(service(db), uid)
            if response is not None:
                result = [response.model_validate(item) for item in result] if isinstance(result, list) else response.model_validate(result)
            return serialize(result)

    def positive(value):
        if value < 1:
            raise ValueError('quantity must be at least 1')
        return value

    def period(value, allowed):
        if value not in allowed:
            raise ValueError('Unsupported period')
        return value

    @tool
    def list_shop_items(skip: int = 0, limit: int = 100) -> Any:
        """List active catalog items visible in the application shop."""
        if skip < 0 or not 1 <= limit <= 1000:
            raise ValueError('Invalid pagination')
        return run(ShopService, lambda svc, uid: svc.get_items(skip=skip, limit=limit))

    @tool
    def get_shop_item(item_id: str) -> Any:
        """Read an owned or system shop item."""
        return run(ShopService, lambda svc, uid: svc.get_item_for_user(UUID(item_id), uid))

    @tool
    def create_shop_item(name: str, description: Optional[str] = None, icon: Optional[str] = None, category: Optional[str] = None, coin_price: int = 0, stock: int = -1) -> Any:
        """Create a personal shop reward using the normal shop validation."""
        data = ShopItemCreate(name=name, description=description, icon=icon, category=category, coin_price=coin_price, stock=stock)
        return run(ShopService, lambda svc, uid: svc.create_item(data, uid))

    @tool
    def update_shop_item(item_id: str, changes: dict[str, Any]) -> Any:
        """Update explicitly supplied shop fields; null clears nullable fields."""
        unknown = set(changes) - set(ShopItemUpdate.model_fields)
        if unknown:
            raise ValueError(f'Unknown shop fields: {sorted(unknown)}')
        data = ShopItemUpdate.model_validate(changes)
        return run(ShopService, lambda svc, uid: svc.update_item(svc.get_mutable_item_for_user(UUID(item_id), uid), data))

    @tool
    def delete_shop_item(item_id: str) -> Any:
        """Delete an owned reward; service rules protect system and referenced items."""
        return run(ShopService, lambda svc, uid: {'deleted': svc.delete_item(UUID(item_id), uid)})

    @tool
    def purchase_shop_item(item_id: str, idempotency_key: str, quantity: int = 1) -> Any:
        """Purchase a reward. Reuse the same idempotency key when retrying a purchase."""
        data = ExchangeHistoryCreate(item_id=UUID(item_id), quantity=quantity)
        return run(ShopService, lambda svc, uid: svc.purchase_item(uid, data, idempotency_key))

    @tool
    def list_shop_exchanges() -> Any:
        """Read the authenticated user's purchase history."""
        return run(ShopService, lambda svc, uid: svc.get_user_exchanges(uid))

    @tool
    def get_shop_exchange(exchange_id: str) -> Any:
        """Read an owned purchase."""
        return run(ShopService, lambda svc, uid: svc.get_exchange_for_user(UUID(exchange_id), uid))

    @tool
    def refund_shop_exchange(exchange_id: str) -> Any:
        """Refund an owned purchase subject to normal stock and inventory rules."""
        return run(ShopService, lambda svc, uid: svc.refund_exchange(svc.get_exchange_for_user(UUID(exchange_id), uid)))

    @tool
    def get_coin_totals() -> Any:
        """Read lifetime coin earnings and spending."""
        return run(CoinService, lambda svc, uid: svc.get_totals(uid))

    @tool
    def get_coin_history(skip: int = 0, limit: int = 50, coin_type: Optional[str] = None, source: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Any:
        """Read filtered coin transactions; dates are ISO timestamps."""
        if skip < 0 or not 1 <= limit <= 1000:
            raise ValueError('Invalid pagination')
        if coin_type is not None:
            CoinType(coin_type)
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        if start and end and start > end:
            raise ValueError('start_date must precede end_date')
        return run(CoinService, lambda svc, uid: svc.get_history(uid, skip, limit, coin_type, source, start, end))

    @tool
    def list_backpack_items(status: Optional[str] = None) -> Any:
        """Read owned backpack inventory, optionally filtered by status."""
        parsed = ItemStatus(status) if status else None
        return run(BackpackService, lambda svc, uid: svc.get_user_items(uid, status=parsed), BackpackItemResponse)

    @tool
    def get_backpack_item(item_id: str) -> Any:
        """Read an owned inventory item."""
        return run(BackpackService, lambda svc, uid: svc.get_item_for_user(UUID(item_id), uid), BackpackItemResponse)

    @tool
    def use_backpack_item(item_id: str, quantity: int = 1) -> Any:
        """Consume owned inventory through normal item effects."""
        positive(quantity)
        return run(BackpackService, lambda svc, uid: svc.use_item(svc.get_item_for_user(UUID(item_id), uid), quantity), BackpackItemResponse)

    @tool
    def equip_backpack_item(item_id: str) -> Any:
        """Equip an owned equipment item."""
        return run(BackpackService, lambda svc, uid: svc.equip_item(svc.get_item_for_user(UUID(item_id), uid)), BackpackItemResponse)

    @tool
    def unequip_backpack_item(item_id: str) -> Any:
        """Unequip an owned equipment item."""
        return run(BackpackService, lambda svc, uid: svc.unequip_item(svc.get_item_for_user(UUID(item_id), uid)), BackpackItemResponse)

    @tool
    def discard_backpack_item(item_id: str, quantity: int = 1) -> Any:
        """Discard owned inventory; this operation cannot be undone."""
        positive(quantity)
        return run(BackpackService, lambda svc, uid: svc.discard_item(svc.get_item_for_user(UUID(item_id), uid), quantity), BackpackItemResponse)

    @tool
    def get_backpack_history() -> Any:
        """Read inventory actions including current or snapshotted item names."""
        return run(BackpackService, lambda svc, uid: [UsageHistoryResponse.model_validate(dict(serialize(entry), item_name=name, action_type=entry.action)) for entry, name in svc.get_usage_history_with_names(uid)])

    @tool
    def get_task_trends(period_name: str = 'week') -> Any:
        """Review task completion trends over week, month or year."""
        period(period_name, {'week', 'month', 'year'})
        return run(StatsService, lambda svc, uid: svc.get_task_trends(uid, period_name))

    @tool
    def get_habit_stats(period_name: str = 'week') -> Any:
        """Review habit completion over week or month."""
        period(period_name, {'week', 'month'})
        return run(StatsService, lambda svc, uid: svc.get_habit_stats(uid, period_name))

    @tool
    def get_coin_trends(period_name: str = 'month') -> Any:
        """Review coin trends over week, month or year."""
        period(period_name, {'week', 'month', 'year'})
        return run(StatsService, lambda svc, uid: svc.get_coin_trends(uid, period_name))

    @tool
    def get_level_progress() -> Any:
        """Read experience and level progress."""
        return run(StatsService, lambda svc, uid: svc.get_level_progress(uid))

    @tool
    def get_calendar_events(start: str, end: str) -> Any:
        """Read calendar events within inclusive ISO calendar dates."""
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        if first > last:
            raise ValueError('start must precede end')
        return run(CalendarService, lambda svc, uid: svc.get_events(uid, first, last))

    @tool
    def get_calendar_day(day: str) -> Any:
        """Read calendar details for an ISO calendar date."""
        parsed = date.fromisoformat(day)
        return run(CalendarService, lambda svc, uid: svc.get_day_detail(uid, parsed))

    @tool
    def get_checkin_status() -> Any:
        """Read daily checkin status and streak without issuing rewards."""
        return run(CheckinService, lambda svc, uid: svc.get_status(uid))

    @tool
    def get_task(task_id: str) -> Any:
        """Read an owned task."""
        return run(TodoService, lambda svc, uid: svc.get_task_for_user(UUID(task_id), uid))

    @tool
    def get_habit(habit_id: str) -> Any:
        """Read an owned habit with today's completion state."""
        return run(TodoService, lambda svc, uid: svc._set_completed_today(svc.get_habit_for_user(UUID(habit_id), uid)), HabitResponse)

    @tool
    def get_goal(goal_id: str) -> Any:
        """Read an owned goal."""
        return run(TodoService, lambda svc, uid: svc.get_goal_for_user(UUID(goal_id), uid))

    @tool
    def get_subtask(subtask_id: str) -> Any:
        """Read a subtask after verifying the parent task ownership."""
        return run(TodoService, lambda svc, uid: svc.get_subtask_for_user(UUID(subtask_id), uid))

    @tool
    def list_achievements() -> Any:
        """Read achievement definitions and their reward conditions."""
        return run(AchievementService, lambda svc, uid: svc.get_all_achievements(), AchievementResponse)

    @tool
    def get_user_achievements() -> Any:
        """Read the authenticated user's unlocked achievements and metadata."""
        return run(AchievementService, lambda svc, uid: svc.get_user_achievements(uid), UserAchievementResponse)

    @tool
    def list_titles() -> Any:
        """Read title definitions and unlock conditions."""
        return run(TitleService, lambda svc, uid: svc.get_all_titles(), TitleResponse)

    @tool
    def get_user_titles() -> Any:
        """Read the authenticated user's unlocked titles and metadata."""
        return run(TitleService, lambda svc, uid: svc.get_user_titles(uid), UserTitleResponse)

    @tool
    def activate_title(title_id: int) -> Any:
        """Activate an already unlocked title for the authenticated user."""
        def activate(svc, uid):
            svc.activate_title(uid, title_id)
            return {'message': 'Title activated'}
        return run(TitleService, activate)

    return tools
