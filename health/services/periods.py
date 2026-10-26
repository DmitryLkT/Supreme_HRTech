from datetime import date, timedelta

def get_week_start(value: date) -> date:
    """Определяет к какой неделе относится ответ на анкету"""
    return value - timedelta(days=value.weekday())

def get_retention_cutoff(value: date) -> date:
    """Возвращает дату на 12 календарныхъ месяцев раньше"""
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(year=value.year - 1, day=28)

def get_expiration_date(value: date) -> date:
    """Возвращает дату окончания хранения через 12 календарных месяцев"""
    try:
        return value.replace(year=value.year + 1)
    except ValueError:
        return value.replace(year=value.year + 1, day=28)