from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

MANAGE_ROLES = ("ADMIN", "MANAGER")
SELL_ROLES = ("ADMIN", "MANAGER", "STAFF")


def has_role(user, *roles):
    return bool(
        user and user.is_authenticated and user.is_active and (user.is_superuser or user.role in roles)
    )


def require_role(user, *roles):
    if not has_role(user, *roles):
        raise PermissionDenied("Bạn không có quyền thực hiện thao tác này.")


def roles_required(*roles):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            require_role(request.user, *roles)
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
