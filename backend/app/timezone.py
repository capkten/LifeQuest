from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


APP_TIMEZONE = ZoneInfo("Asia/Shanghai")


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def local_date(value: datetime) -> date:
    return as_utc(value).astimezone(APP_TIMEZONE).date()


def today() -> date:
    return local_date(datetime.now(timezone.utc))


def day_start_utc(value: date) -> datetime:
    return datetime.combine(value, time.min, APP_TIMEZONE).astimezone(timezone.utc)


def day_bounds_utc(value: date) -> tuple[datetime, datetime]:
    return day_start_utc(value), day_start_utc(value + timedelta(days=1))
