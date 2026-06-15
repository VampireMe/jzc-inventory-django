from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from access.decorators import role_required
from access.models import Role
from access.services import scope_queryset
from inventory.models import Stock

from .forms import (
    PurchaseDetailsForm,
    PurchaseItemFormset,
    SaleDetailsForm,
    SaleForm,
    SaleItemFormset,
    SelectSupplierForm,
    SupplierForm,
)
from .models import (
    PurchaseBill,
    PurchaseBillDetails,
    PurchaseItem,
    SaleBill,
    SaleBillDetails,
    SaleItem,
    Supplier,
)


def department_stocks(request):
    membership = request.user_membership
    queryset = Stock.objects.filter(is_deleted=False, department=membership.department).order_by("name")
    if membership.role_name == Role.STAFF:
        return queryset
    return queryset


def department_suppliers(request):
    membership = request.user_membership
    queryset = Supplier.objects.filter(is_deleted=False, department=membership.department).order_by("name")
    return queryset


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class SupplierListView(ListView):
    model = Supplier
    template_name = "suppliers/suppliers_list.html"
    paginate_by = 10

    def get_queryset(self):
        queryset = Supplier.objects.filter(is_deleted=False).select_related("department", "created_by")
        return scope_queryset(queryset, self.request.user_membership)


@method_decorator(role_required(Role.ADMIN, Role.MANAGER), name="dispatch")
class SupplierCreateView(SuccessMessageMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    success_url = "/transactions/suppliers"
    success_message = "Supplier has been created successfully"
    template_name = "suppliers/edit_supplier.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "New Supplier"
        context["savebtn"] = "Add Supplier"
        context["current_department"] = self.request.user_membership.department
        return context

    def form_valid(self, form):
        form.instance.department = self.request.user_membership.department
        form.instance.created_by = self.request.user
        return super().form_valid(form)


@method_decorator(role_required(Role.ADMIN, Role.MANAGER), name="dispatch")
class SupplierUpdateView(SuccessMessageMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    success_url = "/transactions/suppliers"
    success_message = "Supplier details has been updated successfully"
    template_name = "suppliers/edit_supplier.html"

    def get_queryset(self):
        queryset = Supplier.objects.filter(is_deleted=False).select_related("department", "created_by")
        return scope_queryset(queryset, self.request.user_membership)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Supplier"
        context["savebtn"] = "Save Changes"
        context["delbtn"] = "Delete Supplier"
        context["current_department"] = self.object.department
        return context


@method_decorator(role_required(Role.ADMIN), name="dispatch")
class SupplierDeleteView(View):
    template_name = "suppliers/delete_supplier.html"
    success_message = "Supplier has been deleted successfully"

    def get_supplier(self, pk):
        supplier = get_object_or_404(Supplier.objects.filter(is_deleted=False).select_related("department", "created_by"), pk=pk)
        if not scope_queryset(Supplier.objects.filter(pk=pk), self.request.user_membership).exists():
            raise PermissionDenied("Cross-department supplier access is not allowed.")
        return supplier

    def get(self, request, pk):
        supplier = self.get_supplier(pk)
        return render(request, self.template_name, {"object": supplier})

    def post(self, request, pk):
        supplier = self.get_supplier(pk)
        supplier.is_deleted = True
        supplier.save(update_fields=["is_deleted", "updated_at"])
        messages.success(request, self.success_message)
        return redirect("suppliers-list")


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class SupplierView(View):
    def get(self, request, name):
        supplierobj = get_object_or_404(Supplier.objects.filter(is_deleted=False).select_related("department", "created_by"), name=name)
        if not scope_queryset(Supplier.objects.filter(pk=supplierobj.pk), request.user_membership).exists():
            raise PermissionDenied("Cross-department supplier access is not allowed.")
        bill_list = scope_queryset(
            PurchaseBill.objects.filter(supplier=supplierobj).select_related("supplier", "department", "created_by"),
            request.user_membership,
            owner_field="created_by",
        )
        page = request.GET.get("page", 1)
        paginator = Paginator(bill_list, 10)
        try:
            bills = paginator.page(page)
        except PageNotAnInteger:
            bills = paginator.page(1)
        except EmptyPage:
            bills = paginator.page(paginator.num_pages)
        context = {
            "supplier": supplierobj,
            "bills": bills,
        }
        return render(request, "suppliers/supplier.html", context)


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class PurchaseView(ListView):
    model = PurchaseBill
    template_name = "purchases/purchases_list.html"
    context_object_name = "bills"
    ordering = ["-time"]
    paginate_by = 10

    def get_queryset(self):
        queryset = PurchaseBill.objects.select_related("supplier", "department", "created_by").order_by("-time")
        return scope_queryset(queryset, self.request.user_membership, owner_field="created_by")


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class SelectSupplierView(View):
    form_class = SelectSupplierForm
    template_name = "purchases/select_supplier.html"

    def get_form(self, request, *args, **kwargs):
        form = self.form_class(*args, **kwargs)
        form.fields["supplier"].queryset = department_suppliers(request)
        return form

    def get(self, request, *args, **kwargs):
        form = self.get_form(request)
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.get_form(request, request.POST)
        if form.is_valid():
            supplierid = request.POST.get("supplier")
            supplier = get_object_or_404(department_suppliers(request), id=supplierid)
            return redirect("new-purchase", supplier.pk)
        return render(request, self.template_name, {"form": form})


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class PurchaseCreateView(View):
    template_name = "purchases/new_purchase.html"

    def build_formset(self, request, data=None):
        formset = PurchaseItemFormset(data)
        visible_stocks = department_stocks(request)
        for item_form in formset:
            item_form.fields["stock"].queryset = visible_stocks
        return formset

    def get(self, request, pk):
        formset = self.build_formset(request, request.GET or None)
        supplierobj = get_object_or_404(department_suppliers(request), pk=pk)
        context = {
            "formset": formset,
            "supplier": supplierobj,
            "current_department": request.user_membership.department,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        formset = self.build_formset(request, request.POST)
        supplierobj = get_object_or_404(department_suppliers(request), pk=pk)
        if formset.is_valid():
            with transaction.atomic():
                billobj = PurchaseBill.objects.create(
                    supplier=supplierobj,
                    department=request.user_membership.department,
                    created_by=request.user,
                )
                billdetailsobj = PurchaseBillDetails.objects.create(billno=billobj)

                for item_form in formset:
                    billitem = item_form.save(commit=False)
                    billitem.billno = billobj
                    stock = get_object_or_404(department_stocks(request), pk=billitem.stock.pk)
                    billitem.totalprice = billitem.perprice * billitem.quantity
                    stock.quantity += billitem.quantity
                    stock.save(update_fields=["quantity", "updated_at"])
                    billdetailsobj.total += billitem.totalprice
                    billitem.save()

                billdetailsobj.save()

            messages.success(request, "Purchased items have been registered successfully")
            return redirect("purchase-bill", billno=billobj.billno)
        context = {
            "formset": formset,
            "supplier": supplierobj,
            "current_department": request.user_membership.department,
        }
        return render(request, self.template_name, context)


@method_decorator(role_required(Role.ADMIN, Role.MANAGER), name="dispatch")
class PurchaseDeleteView(SuccessMessageMixin, DeleteView):
    model = PurchaseBill
    template_name = "purchases/delete_purchase.html"
    success_url = "/transactions/purchases"

    def get_queryset(self):
        return PurchaseBill.objects.select_related("supplier", "department", "created_by")

    def get_object(self, queryset=None):
        purchase = super().get_object(queryset=queryset)
        if not scope_queryset(PurchaseBill.objects.filter(pk=purchase.pk), self.request.user_membership, owner_field="created_by").exists():
            raise PermissionDenied("Cross-department purchase access is not allowed.")
        return purchase

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        with transaction.atomic():
            items = PurchaseItem.objects.select_related("stock").filter(billno=self.object.billno)
            for item in items:
                stock = item.stock
                if stock.is_deleted is False:
                    stock.quantity -= item.quantity
                    stock.save(update_fields=["quantity", "updated_at"])
            messages.success(self.request, "Purchase bill has been deleted successfully")
            return super(PurchaseDeleteView, self).delete(request, *args, **kwargs)


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class SaleView(ListView):
    model = SaleBill
    template_name = "sales/sales_list.html"
    context_object_name = "bills"
    ordering = ["-time"]
    paginate_by = 10

    def get_queryset(self):
        queryset = SaleBill.objects.select_related("department", "created_by").order_by("-time")
        return scope_queryset(queryset, self.request.user_membership, owner_field="created_by")


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class SaleCreateView(View):
    template_name = "sales/new_sale.html"

    def build_formset(self, request, data=None):
        formset = SaleItemFormset(data)
        visible_stocks = department_stocks(request)
        for item_form in formset:
            item_form.fields["stock"].queryset = visible_stocks
        return formset

    def get(self, request):
        form = SaleForm(request.GET or None)
        formset = self.build_formset(request, request.GET or None)
        context = {
            "form": form,
            "formset": formset,
            "stocks": department_stocks(request),
            "current_department": request.user_membership.department,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = SaleForm(request.POST)
        formset = self.build_formset(request, request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                billobj = form.save(commit=False)
                billobj.department = request.user_membership.department
                billobj.created_by = request.user
                billobj.save()

                billdetailsobj = SaleBillDetails.objects.create(billno=billobj)

                for item_form in formset:
                    billitem = item_form.save(commit=False)
                    billitem.billno = billobj
                    stock = get_object_or_404(department_stocks(request), pk=billitem.stock.pk)
                    billitem.totalprice = billitem.perprice * billitem.quantity
                    stock.quantity -= billitem.quantity
                    stock.save(update_fields=["quantity", "updated_at"])
                    billdetailsobj.total += billitem.totalprice
                    billitem.save()

                billdetailsobj.save()

            messages.success(request, "Sold items have been registered successfully")
            return redirect("sale-bill", billno=billobj.billno)
        context = {
            "form": form,
            "formset": formset,
            "stocks": department_stocks(request),
            "current_department": request.user_membership.department,
        }
        return render(request, self.template_name, context)


@method_decorator(role_required(Role.ADMIN, Role.MANAGER), name="dispatch")
class SaleDeleteView(SuccessMessageMixin, DeleteView):
    model = SaleBill
    template_name = "sales/delete_sale.html"
    success_url = "/transactions/sales"

    def get_queryset(self):
        return SaleBill.objects.select_related("department", "created_by")

    def get_object(self, queryset=None):
        sale = super().get_object(queryset=queryset)
        if not scope_queryset(SaleBill.objects.filter(pk=sale.pk), self.request.user_membership, owner_field="created_by").exists():
            raise PermissionDenied("Cross-department sale access is not allowed.")
        return sale

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        with transaction.atomic():
            items = SaleItem.objects.select_related("stock").filter(billno=self.object.billno)
            for item in items:
                stock = item.stock
                if stock.is_deleted is False:
                    stock.quantity += item.quantity
                    stock.save(update_fields=["quantity", "updated_at"])
            messages.success(self.request, "Sale bill has been deleted successfully")
            return super(SaleDeleteView, self).delete(request, *args, **kwargs)


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class PurchaseBillView(View):
    model = PurchaseBill
    template_name = "bill/purchase_bill.html"
    bill_base = "bill/bill_base.html"

    def get_bill(self, request, billno):
        bill = get_object_or_404(PurchaseBill.objects.select_related("supplier", "department", "created_by"), billno=billno)
        if not scope_queryset(PurchaseBill.objects.filter(pk=bill.pk), request.user_membership, owner_field="created_by").exists():
            raise PermissionDenied("Cross-department purchase access is not allowed.")
        return bill

    def get(self, request, billno):
        bill = self.get_bill(request, billno)
        context = {
            "bill": bill,
            "items": PurchaseItem.objects.filter(billno=billno),
            "billdetails": PurchaseBillDetails.objects.get(billno=billno),
            "bill_base": self.bill_base,
        }
        return render(request, self.template_name, context)

    def post(self, request, billno):
        bill = self.get_bill(request, billno)
        form = PurchaseDetailsForm(request.POST)
        if form.is_valid():
            billdetailsobj = PurchaseBillDetails.objects.get(billno=billno)
            cleaned = form.cleaned_data

            billdetailsobj.eway = cleaned.get("eway")
            billdetailsobj.veh = cleaned.get("veh")
            billdetailsobj.destination = cleaned.get("destination")
            billdetailsobj.po = cleaned.get("po")
            billdetailsobj.cgst = cleaned.get("cgst")
            billdetailsobj.sgst = cleaned.get("sgst")
            billdetailsobj.igst = cleaned.get("igst")
            billdetailsobj.cess = cleaned.get("cess")
            billdetailsobj.tcs = cleaned.get("tcs")
            billdetailsobj.total = cleaned.get("total")

            billdetailsobj.save()
            messages.success(request, "Bill details have been modified successfully")
        context = {
            "bill": bill,
            "items": PurchaseItem.objects.filter(billno=billno),
            "billdetails": PurchaseBillDetails.objects.get(billno=billno),
            "bill_base": self.bill_base,
        }
        return render(request, self.template_name, context)


@method_decorator(role_required(Role.ADMIN, Role.MANAGER, Role.STAFF), name="dispatch")
class SaleBillView(View):
    model = SaleBill
    template_name = "bill/sale_bill.html"
    bill_base = "bill/bill_base.html"

    def get_bill(self, request, billno):
        bill = get_object_or_404(SaleBill.objects.select_related("department", "created_by"), billno=billno)
        if not scope_queryset(SaleBill.objects.filter(pk=bill.pk), request.user_membership, owner_field="created_by").exists():
            raise PermissionDenied("Cross-department sale access is not allowed.")
        return bill

    def get(self, request, billno):
        bill = self.get_bill(request, billno)
        context = {
            "bill": bill,
            "items": SaleItem.objects.filter(billno=billno),
            "billdetails": SaleBillDetails.objects.get(billno=billno),
            "bill_base": self.bill_base,
        }
        return render(request, self.template_name, context)

    def post(self, request, billno):
        bill = self.get_bill(request, billno)
        form = SaleDetailsForm(request.POST)
        if form.is_valid():
            billdetailsobj = SaleBillDetails.objects.get(billno=billno)
            cleaned = form.cleaned_data

            billdetailsobj.eway = cleaned.get("eway")
            billdetailsobj.veh = cleaned.get("veh")
            billdetailsobj.destination = cleaned.get("destination")
            billdetailsobj.po = cleaned.get("po")
            billdetailsobj.cgst = cleaned.get("cgst")
            billdetailsobj.sgst = cleaned.get("sgst")
            billdetailsobj.igst = cleaned.get("igst")
            billdetailsobj.cess = cleaned.get("cess")
            billdetailsobj.tcs = cleaned.get("tcs")
            billdetailsobj.total = cleaned.get("total")

            billdetailsobj.save()
            messages.success(request, "Bill details have been modified successfully")
        context = {
            "bill": bill,
            "items": SaleItem.objects.filter(billno=billno),
            "billdetails": SaleBillDetails.objects.get(billno=billno),
            "bill_base": self.bill_base,
        }
        return render(request, self.template_name, context)
