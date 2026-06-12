from .models import Role


def access_context(request):
    membership = getattr(request, "user_membership", None)
    role_name = getattr(request, "user_role_name", None)

    return {
        "user_membership": membership,
        "user_role_name": role_name,
        "user_department": getattr(request, "user_department", None),
        "user_can_manage_catalog": membership.can_manage_catalog() if membership else False,
        "user_can_delete_records": membership.can_delete_records() if membership else False,
        "user_can_manage_bills": membership.can_manage_bills() if membership else False,
        "user_can_manage_roles": membership.can_manage_roles() if membership else False,
        "user_can_view_stats": membership.can_view_stats() if membership else False,
        "role_admin": Role.ADMIN,
        "role_manager": Role.MANAGER,
        "role_staff": Role.STAFF,
    }

