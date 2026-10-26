from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

HR_PERMISSION = "onboarding.view_employee_progress"

def is_hr(user):
    return (
        user.is_authenticated
        and user.is_active
        and not user.is_superuser
        and user.groups.filter(name="HR").exists()
        and user.has_perm(HR_PERMISSION)
    )


def hr_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not (request.user.is_superuser or is_hr(request.user)):
            raise PermissionDenied("Нет доступа к прогрессу сотрудников.")
        return view(request, *args, **kwargs)
    return wrapped


def employee_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser and request.user.groups.filter(name="HR").exists():
            raise PermissionDenied("Обучение доступно через аккаунт сотрудника.")
        return view(request, *args, **kwargs)
    return wrapped
