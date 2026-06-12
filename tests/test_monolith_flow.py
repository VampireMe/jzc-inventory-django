from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from access.models import Department, Role, UserRole
from inventory.models import Stock
from transactions.models import (
    PurchaseBill,
    PurchaseBillDetails,
    PurchaseItem,
    SaleBill,
    SaleBillDetails,
    SaleItem,
    Supplier,
)


class MonolithFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.password = "pass12345"

        self.admin_role = Role.objects.create(name=Role.ADMIN, description="Global access")
        self.manager_role = Role.objects.create(name=Role.MANAGER, description="Department access")
        self.staff_role = Role.objects.create(name=Role.STAFF, description="Operator access")

        self.north = Department.objects.create(name="North Hub", code="north")
        self.south = Department.objects.create(name="South Hub", code="south")

        self.admin_user = user_model.objects.create_user("admin_user", password=self.password, is_staff=True, is_superuser=True)
        self.manager_user = user_model.objects.create_user("manager_user", password=self.password)
        self.staff_user = user_model.objects.create_user("staff_user", password=self.password)
        self.south_user = user_model.objects.create_user("south_user", password=self.password)

        self.admin_membership = UserRole.objects.create(
            user=self.admin_user,
            role=self.admin_role,
            department=self.north,
            status=UserRole.STATUS_ACTIVE,
            created_by=self.admin_user,
            approved_by=self.admin_user,
        )
        self.manager_membership = UserRole.objects.create(
            user=self.manager_user,
            role=self.manager_role,
            department=self.north,
            status=UserRole.STATUS_ACTIVE,
            created_by=self.admin_user,
            approved_by=self.admin_user,
        )
        self.staff_membership = UserRole.objects.create(
            user=self.staff_user,
            role=self.staff_role,
            department=self.north,
            status=UserRole.STATUS_ACTIVE,
            created_by=self.admin_user,
            approved_by=self.admin_user,
        )
        self.south_membership = UserRole.objects.create(
            user=self.south_user,
            role=self.manager_role,
            department=self.south,
            status=UserRole.STATUS_ACTIVE,
            created_by=self.admin_user,
            approved_by=self.admin_user,
        )

        self.north_stock = Stock.objects.create(
            name="North Bolts",
            department=self.north,
            quantity=25,
            created_by=self.admin_user,
        )
        self.south_stock = Stock.objects.create(
            name="South Bearings",
            department=self.south,
            quantity=26,
            created_by=self.admin_user,
        )

        self.north_supplier = Supplier.objects.create(
            name="North Supply",
            department=self.north,
            phone="1111111111",
            address="North street",
            email="north@suppliers.test",
            gstin="11AAAAA1111A1Z1",
            created_by=self.admin_user,
        )
        self.south_supplier = Supplier.objects.create(
            name="South Supply",
            department=self.south,
            phone="2222222222",
            address="South street",
            email="south@suppliers.test",
            gstin="22BBBBB2222B2Z2",
            created_by=self.admin_user,
        )

        self.north_purchase = PurchaseBill.objects.create(
            supplier=self.north_supplier,
            department=self.north,
            created_by=self.manager_user,
        )
        PurchaseItem.objects.create(
            billno=self.north_purchase,
            stock=self.north_stock,
            quantity=5,
            perprice=12,
            totalprice=60,
        )
        PurchaseBillDetails.objects.create(billno=self.north_purchase, total=60)

        self.south_purchase = PurchaseBill.objects.create(
            supplier=self.south_supplier,
            department=self.south,
            created_by=self.south_user,
        )
        PurchaseItem.objects.create(
            billno=self.south_purchase,
            stock=self.south_stock,
            quantity=4,
            perprice=8,
            totalprice=32,
        )
        PurchaseBillDetails.objects.create(billno=self.south_purchase, total=32)

        self.south_sale = SaleBill.objects.create(
            department=self.south,
            created_by=self.south_user,
            name="South Customer",
            phone="3333333333",
            address="South market",
            email="customer@south.test",
            gstin="33CCCCC3333C3Z3",
        )
        SaleItem.objects.create(
            billno=self.south_sale,
            stock=self.south_stock,
            quantity=3,
            perprice=20,
            totalprice=60,
        )
        SaleBillDetails.objects.create(billno=self.south_sale, total=60)

    def test_role_transition_happy_path_and_illegal_jump(self):
        self.client.force_login(self.admin_user)

        suspend_response = self.client.post(reverse("grant_role", args=[self.staff_membership.pk]))
        self.assertEqual(suspend_response.status_code, 302)
        self.staff_membership.refresh_from_db()
        self.assertEqual(self.staff_membership.status, UserRole.STATUS_SUSPENDED)

        revoke_response = self.client.post(reverse("revoke_role", args=[self.staff_membership.pk]))
        self.assertEqual(revoke_response.status_code, 302)
        self.staff_membership.refresh_from_db()
        self.assertEqual(self.staff_membership.status, UserRole.STATUS_REVOKED)

        illegal_response = self.client.post(reverse("revoke_role", args=[self.staff_membership.pk]))
        self.assertEqual(illegal_response.status_code, 409)
        self.staff_membership.refresh_from_db()
        self.assertEqual(self.staff_membership.status, UserRole.STATUS_REVOKED)

    def test_staff_cannot_see_or_call_guard_delete(self):
        self.client.force_login(self.staff_user)

        inventory_response = self.client.get(reverse("inventory"))
        self.assertNotContains(inventory_response, reverse("guard_delete", args=[self.north_stock.pk]))

        delete_response = self.client.post(reverse("guard_delete", args=[self.north_stock.pk]))
        self.assertEqual(delete_response.status_code, 403)

    def test_manager_scope_blocks_other_department_and_chart_filters_by_department(self):
        self.client.force_login(self.manager_user)

        forbidden_response = self.client.post(reverse("delete-purchase", args=[self.south_purchase.pk]))
        self.assertEqual(forbidden_response.status_code, 403)

        chart_response = self.client.get(reverse("department_chart"))
        self.assertEqual(chart_response.status_code, 200)
        payload = chart_response.json()["data"]
        self.assertIn("North Bolts", payload["labels"])
        self.assertNotIn("South Bearings", payload["labels"])
        self.assertEqual(payload["summary"]["purchase_count"], 1)

    def test_change_department_updates_staff_chart_scope(self):
        self.client.force_login(self.staff_user)
        initial_payload = self.client.get(reverse("department_chart")).json()["data"]
        self.assertIn("North Bolts", initial_payload["labels"])
        self.assertNotIn("South Bearings", initial_payload["labels"])

        self.client.force_login(self.admin_user)
        move_response = self.client.post(
            reverse("change_department", args=[self.staff_membership.pk]),
            {"department": self.south.pk},
        )
        self.assertEqual(move_response.status_code, 302)

        self.client.force_login(self.staff_user)
        moved_payload = self.client.get(reverse("department_chart")).json()["data"]
        self.assertIn("South Bearings", moved_payload["labels"])
        self.assertNotIn("North Bolts", moved_payload["labels"])

    def test_purchase_delete_restores_stock_quantity(self):
        self.client.force_login(self.manager_user)

        delete_response = self.client.post(reverse("delete-purchase", args=[self.north_purchase.pk]))
        self.assertEqual(delete_response.status_code, 302)
        self.north_stock.refresh_from_db()
        self.assertEqual(self.north_stock.quantity, 20)
