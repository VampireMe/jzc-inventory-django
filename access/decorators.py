from functools import wraps

from django.core.exceptions import PermissionDenied

from .models import Role, UserRole


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            membership = getattr(request, "user_membership", None)
            if membership is None:
                raise PermissionDenied("No role membership configured.")
            if membership.status != UserRole.STATUS_ACTIVE:
                raise PermissionDenied("Inactive role membership.")
            if allowed_roles and membership.role_name not in allowed_roles:
                raise PermissionDenied("Permission denied.")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def admin_required(view_func):
    return role_required(Role.ADMIN)(view_func)

