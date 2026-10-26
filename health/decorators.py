from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def hr_required(view_func):
    """Разрешает доступ HR"""

    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        user = request.user

        has_access = (
            user.is_superuser
            or user.groups.filter(name="HR").exists()
        )

        if not has_access:
            raise PermissionDenied("Доступ к отчётам разрешён только HR.")

        return view_func(request, *args, **kwargs)

    return login_required(wrapped_view)