import json

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View

from access.decorators import admin_required, role_required
from access.models import Department, Role, UserRole
from access.services import department_chart_payload, scope_queryset
from inventory.models import Stock
from transactions.models import PurchaseBill, SaleBill


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class HomeView(View):
    template_name = "home.html"

    def get_context_data(self, request):
        membership = request.user_membership
        payload = department_chart_payload(membership)
        sales = scope_queryset(
            SaleBill.objects.select_related("department", "created_by").order_by("-time"),
            membership,
        )[:3]
        purchases = scope_queryset(
            PurchaseBill.objects.select_related("supplier", "department", "created_by").order_by("-time"),
            membership,
        )[:3]
        memberships = UserRole.objects.select_related("user", "role", "department").order_by("department__name", "user__username")
        context = {
            "chart_payload": json.dumps(payload),
            "summary": payload["summary"],
            "sales": sales,
            "purchases": purchases,
            "memberships": memberships if request.user_membership.can_manage_roles() else UserRole.objects.none(),
            "departments": Department.objects.filter(is_active=True),
            "role_workflow_statuses": UserRole.STATUS_CHOICES,
            "labels": payload["labels"],
            "data": payload["data"],
        }
        return context

    def get(self, request):
        return render(request, self.template_name, self.get_context_data(request))


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class DepartmentChartView(View):
    def get(self, request):
        return JsonResponse({"code": 0, "data": department_chart_payload(request.user_membership), "message": "ok"})

    def post(self, request):
        return self.get(request)


@method_decorator(admin_required, name="dispatch")
class ChangeDepartmentView(View):
    def post(self, request, pk):
        membership = get_object_or_404(UserRole.objects.select_related("department", "role", "user"), pk=pk)
        department = get_object_or_404(Department, pk=request.POST.get("department"))
        membership.department = department
        membership.approved_by = request.user
        membership.save(update_fields=["department", "approved_by", "updated_at"])
        messages.success(request, "%s now reports to %s." % (membership.user.username, department.name))
        return redirect("home")


class RoleTransitionView(View):
    action = None

    @method_decorator(admin_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        membership = get_object_or_404(UserRole.objects.select_related("role", "department", "user"), pk=pk)
        try:
            membership.transition(actor=request.user, action=self.action)
        except ValidationError:
            return JsonResponse({"code": 1, "message": "illegal transition"}, status=409)
        except PermissionDenied:
            return JsonResponse({"code": 1, "message": "permission denied"}, status=403)
        messages.success(request, "Updated %s to %s." % (membership.user.username, membership.status))
        return redirect("home")


class GrantRoleView(RoleTransitionView):
    action = UserRole.ACTION_GRANT_ROLE


class RevokeRoleView(RoleTransitionView):
    action = UserRole.ACTION_REVOKE_ROLE


class AboutView(TemplateView):
    template_name = "about.html"
