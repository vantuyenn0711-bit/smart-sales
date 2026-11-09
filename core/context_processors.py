from django.conf import settings


def application(request):
    user = request.user
    role = getattr(user, "role", "") if user.is_authenticated else ""
    admin = user.is_authenticated and (user.is_superuser or role == "ADMIN")
    return {
        "can_manage": bool(admin or role == "MANAGER"),
        "can_sell": bool(admin or role in {"MANAGER", "STAFF"}),
        "is_admin": bool(admin),
        "demo_mode": settings.DEMO_MODE,
    }
