from datetime import date, timedelta


def get_week_start(value: date) -> date:
    """Определяет, к какой неделе относится дата (понедельник этой недели)"""
    return value - timedelta(days=value.weekday())


def get_retention_cutoff(value: date) -> date:
    """Возвращает дату на 12 календарных месяцев раньше"""
    return _shift_calendar_year(value, years=-1)


def get_expiration_date(value: date) -> date:
    """Возвращает дату окончания хранения через 12 календарных месяцев"""
    return _shift_calendar_year(value, years=1)


def _shift_calendar_year(value: date, years: int) -> date:
    """Сдвигает дату на календарные годы; 29 февраля → 28 февраля"""
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(year=value.year + years, day=28)