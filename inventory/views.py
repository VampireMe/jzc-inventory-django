import csv

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, UpdateView, View
from django_filters.views import FilterView

from access.decorators import role_required
from access.models import Role
from access.services import scope_queryset

from .filters import StockFilter
from .forms import StockForm
from .models import Stock


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class StockListView(FilterView):
    filterset_class = StockFilter
    template_name = "inventory.html"
    paginate_by = 10

    def get_queryset(self):
        queryset = Stock.objects.select_related("department", "created_by").order_by("name")
        if self.request.GET.get("archived") == "1":
            queryset = queryset.filter(is_deleted=True)
        else:
            queryset = queryset.filter(is_deleted=False)
        return scope_queryset(queryset, self.request.user_membership)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_archived"] = self.request.GET.get("archived") == "1"
        return context


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class InventoryExportView(View):
    def get(self, request):
        queryset = Stock.objects.filter(is_deleted=False)
        queryset = scope_queryset(queryset, request.user_membership)
        summary = (
            queryset
            .values("department__name")
            .annotate(variety_count=Count("id"), total_quantity=Sum("quantity"))
            .order_by("department__name")
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="inventory_export.csv"'
        response.write("\ufeff")

        writer = csv.writer(response)
        writer.writerow(["部门", "品种数", "总库存"])
        for row in summary:
            writer.writerow([row["department__name"], row["variety_count"], row["total_quantity"]])

        return response


@method_decorator(role_required(Role.ADMIN, Role.MANAGER), name="dispatch")
class StockCreateView(SuccessMessageMixin, CreateView):
    model = Stock
    form_class = StockForm
    template_name = "edit_stock.html"
    success_url = "/inventory"
    success_message = "Stock has been created successfully"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "New Stock"
        context["savebtn"] = "Add to Inventory"
        context["current_department"] = self.request.user_membership.department
        return context

    def form_valid(self, form):
        form.instance.department = self.request.user_membership.department
        form.instance.created_by = self.request.user
        return super().form_valid(form)


@method_decorator(role_required(Role.ADMIN, Role.MANAGER), name="dispatch")
class StockUpdateView(SuccessMessageMixin, UpdateView):
    model = Stock
    form_class = StockForm
    template_name = "edit_stock.html"
    success_url = "/inventory"
    success_message = "Stock has been updated successfully"

    def get_queryset(self):
        queryset = Stock.objects.filter(is_deleted=False).select_related("department", "created_by")
        return scope_queryset(queryset, self.request.user_membership)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Stock"
        context["savebtn"] = "Update Stock"
        context["delbtn"] = "Delete Stock"
        context["current_department"] = self.object.department
        return context


@method_decorator(role_required(Role.ADMIN), name="dispatch")
class StockDeleteView(View):
    template_name = "delete_stock.html"
    success_message = "Stock has been deleted successfully"

    def get_stock(self, pk):
        stock = get_object_or_404(Stock.objects.filter(is_deleted=False).select_related("department", "created_by"), pk=pk)
        if not scope_queryset(Stock.objects.filter(pk=pk), self.request.user_membership).exists():
            raise PermissionDenied("Cross-department stock access is not allowed.")
        return stock

    def get(self, request, pk):
        stock = self.get_stock(pk)
        return render(request, self.template_name, {"object": stock})

    def post(self, request, pk):
        stock = self.get_stock(pk)
        stock.is_deleted = True
        stock.save(update_fields=["is_deleted", "updated_at"])
        messages.success(request, self.success_message)
        return redirect("inventory")


@method_decorator(role_required(Role.ADMIN), name="dispatch")
class RestoreStockView(View):
    def post(self, request, pk):
        stock = get_object_or_404(Stock.objects.filter(is_deleted=True).select_related("department", "created_by"), pk=pk)
        if not scope_queryset(Stock.objects.filter(pk=pk), request.user_membership).exists():
            raise PermissionDenied("Cross-department stock access is not allowed.")
        stock.is_deleted = False
        stock.save(update_fields=["is_deleted", "updated_at"])
        messages.success(request, "Stock has been restored successfully")
        return redirect("%s?archived=1" % redirect("inventory").url)
