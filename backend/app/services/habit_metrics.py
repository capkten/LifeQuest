from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.models.todo import Habit
from app.services.habit_schedule import is_due, is_excluded_on, week_start
from app.timezone import local_date


@dataclass(frozen=True)
class HabitMetrics:
    total_completed: int
    scheduled_count: int
    completed_count: int
    completion_rate: float


def _created_on(habit: Habit, fallback: date) -> date:
    return local_date(habit.created_at) if habit.created_at else fallback


def _valid_completion_date(
    habit: Habit,
    completed_on: date,
    created_on: date,
    pause_intervals: Sequence,
    leave_intervals: Sequence,
) -> bool:
    return (
        completed_on >= created_on
        and is_due(habit, completed_on)
        and not is_excluded_on(completed_on, pause_intervals, leave_intervals)
    )


def valid_completion_dates(
    habit: Habit,
    completion_dates: Collection[date],
    pause_intervals: Sequence = (),
    leave_intervals: Sequence = (),
    as_of: date | None = None,
) -> set[date]:
    """Return completion facts that are valid as of an inclusive China date."""
    created_on = _created_on(habit, date.min)
    return {
        completed_on
        for completed_on in set(completion_dates)
        if isinstance(completed_on, date)
        and (as_of is None or completed_on <= as_of)
        and _valid_completion_date(
            habit,
            completed_on,
            created_on,
            pause_intervals,
            leave_intervals,
        )
    }


def count_valid_completions(
    habit: Habit,
    completion_dates: Collection[date],
    period_start: date,
    period_end: date,
    pause_intervals: Sequence = (),
    leave_intervals: Sequence = (),
    as_of: date | None = None,
) -> int:
    """Count recorded completions that were valid slots in an inclusive range."""
    if period_start > period_end:
        return 0
    valid_dates = valid_completion_dates(
        habit,
        completion_dates,
        pause_intervals,
        leave_intervals,
        as_of=as_of,
    )
    return sum(
        period_start <= completed_on <= period_end
        for completed_on in valid_dates
    )


def _week_has_target_slot(
    habit: Habit,
    current_week: date,
    created_on: date,
    pause_intervals: Sequence,
    leave_intervals: Sequence,
) -> bool:
    return any(
        candidate >= created_on
        and is_due(habit, candidate)
        and not is_excluded_on(candidate, pause_intervals, leave_intervals)
        for candidate in (current_week + timedelta(days=offset) for offset in range(7))
    )


def calculate_habit_metrics(
    habit: Habit,
    completion_dates: Collection[date],
    period_start: date,
    period_end: date,
    pause_intervals: Sequence = (),
    leave_intervals: Sequence = (),
    as_of: date | None = None,
) -> HabitMetrics:
    """Calculate inclusive China-local habit metrics from completion facts."""
    completion_date_set = set(completion_dates)
    effective_as_of = period_end if as_of is None else as_of
    valid_dates = valid_completion_dates(
        habit,
        completion_date_set,
        pause_intervals,
        leave_intervals,
        as_of=effective_as_of,
    )
    if period_start > period_end:
        return HabitMetrics(len(valid_dates), 0, 0, 0.0)

    created_on = _created_on(habit, period_start)
    scheduled_count = 0
    completed_count = 0

    if habit.frequency == "weekly_target" and habit.weekly_target:
        target = habit.weekly_target
        current_week = week_start(period_start)
        while current_week <= period_end:
            if _week_has_target_slot(
                habit, current_week, created_on, pause_intervals, leave_intervals,
            ):
                scheduled_count += target
                completed_count += min(
                    target,
                    count_valid_completions(
                        habit,
                        completion_date_set,
                        current_week,
                        current_week + timedelta(days=6),
                        pause_intervals,
                        leave_intervals,
                        as_of=effective_as_of,
                    ),
                )
            current_week += timedelta(days=7)
    else:
        current_date = max(period_start, created_on)
        while current_date <= period_end:
            if is_due(habit, current_date) and not is_excluded_on(
                current_date, pause_intervals, leave_intervals,
            ):
                scheduled_count += 1
                completed_count += current_date in valid_dates
            current_date += timedelta(days=1)

    completion_rate = round(completed_count / scheduled_count * 100, 1) if scheduled_count else 0.0
    return HabitMetrics(
        total_completed=len(valid_dates),
        scheduled_count=scheduled_count,
        completed_count=completed_count,
        completion_rate=completion_rate,
    )


def weekly_target_progress(
    habit: Habit,
    completion_dates: Collection[date],
    target_date: date,
    pause_intervals: Sequence = (),
    leave_intervals: Sequence = (),
) -> tuple[int, int]:
    """Return capped completed and remaining target slots for target_date's week."""
    current_week = week_start(target_date)
    completion_date_set = {
        completed_on for completed_on in completion_dates if completed_on <= target_date
    }
    metrics = calculate_habit_metrics(
        habit,
        completion_date_set,
        current_week,
        current_week + timedelta(days=6),
        pause_intervals,
        leave_intervals,
        as_of=target_date,
    )
    completed = min(metrics.completed_count, habit.weekly_target or 0)
    return completed, max(metrics.scheduled_count - completed, 0)
