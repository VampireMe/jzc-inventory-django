from django.db.models import Sum

from inventory.models import Stock
from transactions.models import PurchaseBill, SaleBill

from .models import Role, UserRole


def scope_queryset(queryset, membership, department_field="department", owner_field=None):
    if membership is None:
        return queryset.none()

    if membership.role_name == Role.ADMIN:
        return queryset

    filters = {}
    if department_field:
        filters[department_field] = membership.department

    scoped_queryset = queryset.filter(**filters)
    if membership.role_name == Role.STAFF and owner_field:
        scoped_queryset = scoped_queryset.filter(**{owner_field: membership.user})
    return scoped_queryset


def department_chart_payload(membership):
    visible_stock = scope_queryset(
        Stock.objects.filter(is_deleted=False).order_by("-quantity"),
        membership,
    )
    labels = []
    data = []
    for item in visible_stock:
        labels.append(item.name)
        data.append(item.quantity)

    visible_purchases = scope_queryset(
        PurchaseBill.objects.select_related("department"),
        membership,
    )
    visible_sales = scope_queryset(
        SaleBill.objects.select_related("department"),
        membership,
    )

    summary = {
        "department": "All departments" if membership and membership.role_name == Role.ADMIN else (membership.department.name if membership and membership.department else "Unknown"),
        "stock_types": visible_stock.count(),
        "stock_units": visible_stock.aggregate(total=Sum("quantity"))["total"] or 0,
        "purchase_count": visible_purchases.count(),
        "sale_count": visible_sales.count(),
        "membership_count": scope_queryset(
            UserRole.objects.select_related("department", "role"),
            membership,
            owner_field="user",
        ).count(),
    }
    return {
        "labels": labels,
        "data": data,
        "summary": summary,
    }
