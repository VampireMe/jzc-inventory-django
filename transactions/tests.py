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


class BillDetailValidationTests(TestCase):
    """Verify that bill detail views reject invalid total values via form validation."""

    def setUp(self):
        user_model = get_user_model()
        self.password = "testpass123"

        self.role = Role.objects.create(name=Role.MANAGER, description="Manager")
        self.dept = Department.objects.create(name="Test Dept", code="test")
        self.user = user_model.objects.create_user("testuser", password=self.password)
        UserRole.objects.create(
            user=self.user,
            role=self.role,
            department=self.dept,
            status=UserRole.STATUS_ACTIVE,
            created_by=self.user,
            approved_by=self.user,
        )

        self.stock = Stock.objects.create(
            name="Widget", department=self.dept, quantity=100, created_by=self.user
        )

        # Purchase bill fixtures
        self.supplier = Supplier.objects.create(
            name="Acme",
            department=self.dept,
            phone="1234567890",
            address="123 St",
            email="acme@test.com",
            gstin="11AAAAA1111A1Z1",
            created_by=self.user,
        )
        self.purchase_bill = PurchaseBill.objects.create(
            supplier=self.supplier, department=self.dept, created_by=self.user
        )
        PurchaseItem.objects.create(
            billno=self.purchase_bill,
            stock=self.stock,
            quantity=10,
            perprice=5,
            totalprice=50,
        )
        self.purchase_details = PurchaseBillDetails.objects.create(
            billno=self.purchase_bill, total=50
        )

        # Sale bill fixtures
        self.sale_bill = SaleBill.objects.create(
            department=self.dept,
            name="Customer",
            phone="0987654321",
            address="456 Ave",
            email="cust@test.com",
            gstin="22BBBBB2222B2Z2",
            created_by=self.user,
        )
        SaleItem.objects.create(
            billno=self.sale_bill,
            stock=self.stock,
            quantity=5,
            perprice=10,
            totalprice=50,
        )
        self.sale_details = SaleBillDetails.objects.create(
            billno=self.sale_bill, total=50
        )

        self.client.login(username="testuser", password=self.password)

        self.purchase_url = reverse(
            "purchase-bill", kwargs={"billno": self.purchase_bill.pk}
        )
        self.sale_url = reverse("sale-bill", kwargs={"billno": self.sale_bill.pk})

    def _valid_payload(self, **overrides):
        data = {
            "eway": "",
            "veh": "",
            "destination": "",
            "po": "",
            "cgst": "",
            "sgst": "",
            "igst": "",
            "cess": "",
            "tcs": "",
            "total": "100",
        }
        data.update(overrides)
        return data

    # ── Purchase bill tests ──────────────────────────────────────

    def test_purchase_negative_total_rejected(self):
        resp = self.client.post(self.purchase_url, self._valid_payload(total="-1"))
        self.purchase_details.refresh_from_db()
        self.assertEqual(self.purchase_details.total, 50)
        self.assertNotContains(resp, "modified successfully")

    def test_purchase_string_total_rejected(self):
        resp = self.client.post(self.purchase_url, self._valid_payload(total="abc"))
        self.purchase_details.refresh_from_db()
        self.assertEqual(self.purchase_details.total, 50)
        self.assertNotContains(resp, "modified successfully")

    def test_purchase_overflow_total_rejected(self):
        resp = self.client.post(
            self.purchase_url, self._valid_payload(total="9999999999")
        )
        self.purchase_details.refresh_from_db()
        self.assertEqual(self.purchase_details.total, 50)
        self.assertNotContains(resp, "modified successfully")

    def test_purchase_valid_total_accepted(self):
        resp = self.client.post(self.purchase_url, self._valid_payload(total="200"))
        self.purchase_details.refresh_from_db()
        self.assertEqual(self.purchase_details.total, 200)
        self.assertContains(resp, "modified successfully")

    # ── Sale bill tests ──────────────────────────────────────────

    def test_sale_negative_total_rejected(self):
        resp = self.client.post(self.sale_url, self._valid_payload(total="-1"))
        self.sale_details.refresh_from_db()
        self.assertEqual(self.sale_details.total, 50)
        self.assertNotContains(resp, "modified successfully")

    def test_sale_string_total_rejected(self):
        resp = self.client.post(self.sale_url, self._valid_payload(total="abc"))
        self.sale_details.refresh_from_db()
        self.assertEqual(self.sale_details.total, 50)
        self.assertNotContains(resp, "modified successfully")

    def test_sale_overflow_total_rejected(self):
        resp = self.client.post(self.sale_url, self._valid_payload(total="9999999999"))
        self.sale_details.refresh_from_db()
        self.assertEqual(self.sale_details.total, 50)
        self.assertNotContains(resp, "modified successfully")

    def test_sale_valid_total_accepted(self):
        resp = self.client.post(self.sale_url, self._valid_payload(total="200"))
        self.sale_details.refresh_from_db()
        self.assertEqual(self.sale_details.total, 200)
        self.assertContains(resp, "modified successfully")
