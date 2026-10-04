from datetime import date, timedelta

from app.timezone import local_date


def week_start(target_date):
    return target_date - timedelta(days=target_date.weekday())


def is_paused_on(pause_intervals, target_date):
    return any(
        interval.paused_on <= target_date
        and (interval.resumed_on is None or target_date < interval.resumed_on)
        for interval in (pause_intervals or [])
    )


def is_excused_on(leave_intervals, target_date):
    return any(
        interval.leave_on <= target_date < interval.return_on
        for interval in (leave_intervals or [])
    )


def is_excluded_on(target_date, pause_intervals=None, leave_intervals=None):
    return is_paused_on(pause_intervals, target_date) or is_excused_on(leave_intervals, target_date)


def _habit_created_on(habit):
    created_at = getattr(habit, "created_at", None)
    return local_date(created_at) if created_at else None


def week_has_active_schedule(habit, start_date, pause_intervals=None, leave_intervals=None):
    created_on = _habit_created_on(habit)
    return any(
        (created_on is None or candidate >= created_on)
        and is_due(habit, candidate)
        and not is_excluded_on(candidate, pause_intervals, leave_intervals)
        for candidate in (start_date + timedelta(days=offset) for offset in range(7))
    )


def month_period(target_date):
    return target_date.year * 12 + target_date.month


def month_start_for_period(period):
    year, month = divmod(period - 1, 12)
    return date(year, month + 1, 1)


def month_has_active_schedule(habit, period, pause_intervals=None, leave_intervals=None):
    target_date = month_start_for_period(period)
    next_month = month_start_for_period(period + 1)
    created_on = _habit_created_on(habit)
    while target_date < next_month:
        if (
            (created_on is None or target_date >= created_on)
            and is_due(habit, target_date)
            and not is_excluded_on(target_date, pause_intervals, leave_intervals)
        ):
            return True
        target_date += timedelta(days=1)
    return False


def is_due(habit, target_date):
    if habit.frequency == "weekly_target":
        return True
    if habit.frequency == "weekdays":
        return target_date.weekday() in (habit.weekdays or [])
    if habit.frequency == "weekly":
        return target_date.weekday() == 0
    if habit.frequency == "monthly":
        return target_date.day == 1
    return habit.frequency == "daily"


def previous_scheduled_date(habit, target_date, pause_intervals=None, leave_intervals=None):
    if habit.frequency == "weekdays" and not habit.weekdays:
        return None

    created_on = _habit_created_on(habit)
    candidate = target_date - timedelta(days=1)
    while candidate >= date.min:
        if created_on is not None and candidate < created_on:
            break
        if is_due(habit, candidate) and not is_excluded_on(candidate, pause_intervals, leave_intervals):
            return candidate
        if candidate == date.min:
            break
        candidate -= timedelta(days=1)
    return None
