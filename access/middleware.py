from .models import UserRole


class RoleContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.user_membership = None
        request.user_role_name = None
        request.user_department = None

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            try:
                membership = UserRole.objects.select_related("role", "department").get(user=user)
            except UserRole.DoesNotExist:
                membership = None
            request.user_membership = membership
            if membership is not None:
                request.user_role_name = membership.role_name
                request.user_department = membership.department

        return self.get_response(request)

