from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from access.models import Department, Role, UserRole
from inventory.models import Stock
from transactions.models import SaleBill, SaleBillDetails, SaleItem


class SaleCreateViewStockCheckTests(TestCase):
    """测试销售出库时的库存校验逻辑"""

    def setUp(self):
        user_model = get_user_model()
        self.password = "pass12345"

        self.staff_role = Role.objects.create(name=Role.STAFF, description="Operator access")
        self.dept = Department.objects.create(name="North Hub", code="north")

        self.staff_user = user_model.objects.create_user("staff_user", password=self.password)
        self.staff_membership = UserRole.objects.create(
            user=self.staff_user,
            role=self.staff_role,
            department=self.dept,
            status=UserRole.STATUS_ACTIVE,
            created_by=self.staff_user,
            approved_by=self.staff_user,
        )

        self.stock_a = Stock.objects.create(name="商品A", department=self.dept, quantity=10)
        self.stock_b = Stock.objects.create(name="商品B", department=self.dept, quantity=5)

        self.url = reverse("new-sale")
        self.client.login(username="staff_user", password=self.password)

    def _build_sale_post_data(self, items):
        """构造销售表单的 POST 数据（含 formset）"""
        data = {
            "name": "Test Customer",
            "phone": "1234567890",
            "address": "Test Address",
            "email": "test@example.com",
            "gstin": "123456789012345",
            "form-TOTAL_FORMS": str(len(items)),
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        for i, item in enumerate(items):
            data[f"form-{i}-stock"] = str(item["stock"].pk)
            data[f"form-{i}-quantity"] = str(item["quantity"])
            data[f"form-{i}-perprice"] = str(item.get("perprice", 10))
        return data

    def test_insufficient_stock_order_rejected(self):
        """库存不足时，订单应被拒绝，不创建 SaleBill"""
        data = self._build_sale_post_data([
            {"stock": self.stock_a, "quantity": 999},  # 远超库存
        ])
        response = self.client.post(self.url, data)

        # 订单不应被创建
        self.assertEqual(SaleBill.objects.count(), 0)
        # 页面应包含错误消息
        self.assertContains(response, "库存不足")
        self.assertContains(response, "商品A")

    def test_insufficient_stock_quantity_unchanged(self):
        """库存不足时，所有商品的库存数量应保持不变"""
        original_qty_a = self.stock_a.quantity
        original_qty_b = self.stock_b.quantity

        data = self._build_sale_post_data([
            {"stock": self.stock_a, "quantity": 3},   # 库存充足
            {"stock": self.stock_b, "quantity": 999}, # 库存不足
        ])
        response = self.client.post(self.url, data)

        # 两个商品的库存都不应变化
        self.stock_a.refresh_from_db()
        self.stock_b.refresh_from_db()
        self.assertEqual(self.stock_a.quantity, original_qty_a)
        self.assertEqual(self.stock_b.quantity, original_qty_b)

        # 不应创建任何销售记录
        self.assertEqual(SaleBill.objects.count(), 0)
        self.assertEqual(SaleItem.objects.count(), 0)

    def test_insufficient_stock_shows_product_name(self):
        """库存不足时应明确告知是哪个商品库存不足"""
        data = self._build_sale_post_data([
            {"stock": self.stock_a, "quantity": 999},
            {"stock": self.stock_b, "quantity": 999},
        ])
        response = self.client.post(self.url, data)

        # 应包含两个商品的名称
        content = response.content.decode()
        self.assertIn("商品A", content)
        self.assertIn("商品B", content)
        self.assertIn("当前库存", content)

    def test_sufficient_stock_order_succeeds(self):
        """库存充足时，订单应正常创建，库存正确扣减"""
        data = self._build_sale_post_data([
            {"stock": self.stock_a, "quantity": 3, "perprice": 100},
            {"stock": self.stock_b, "quantity": 2, "perprice": 50},
        ])
        response = self.client.post(self.url, data)

        # 订单应被创建
        self.assertEqual(SaleBill.objects.count(), 1)
        self.assertEqual(SaleItem.objects.count(), 2)

        # 库存应正确扣减
        self.stock_a.refresh_from_db()
        self.stock_b.refresh_from_db()
        self.assertEqual(self.stock_a.quantity, 7)  # 10 - 3
        self.assertEqual(self.stock_b.quantity, 3)  # 5 - 2

    def test_exact_stock_order_succeeds(self):
        """刚好等于库存数量时，订单应正常创建"""
        data = self._build_sale_post_data([
            {"stock": self.stock_a, "quantity": 10, "perprice": 100},
        ])
        response = self.client.post(self.url, data)

        self.assertEqual(SaleBill.objects.count(), 1)
        self.stock_a.refresh_from_db()
        self.assertEqual(self.stock_a.quantity, 0)
