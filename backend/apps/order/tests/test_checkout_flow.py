"""商城加购 -> 结账主链路：成功路径与库存不足（含 M12 结账行锁重校验）。"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product
from apps.order.models import CartItem, Order

User = get_user_model()

CART_ITEMS_URL = "/api/member/cart/items"
CART_URL = "/api/member/cart"
ORDERS_URL = "/api/member/orders"


class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.member = User.objects.create_user(
            email="buyer_checkout@test.local",
            password="pass12345",
            role="member",
            is_active=True,
        )
        self.client.force_authenticate(user=self.member)
        self.category = Category.objects.create(name={"ko": "Test", "en": "Test"}, slug="checkout-test-cat")
        self.product = Product.objects.create(
            category=self.category,
            sku="SKU-CHECKOUT-1",
            name={"ko": "Test Product", "en": "Test Product"},
            price_amount=1000,
            stock=5,
        )

    def _add_to_cart(self, quantity, client=None, product=None):
        client = client or self.client
        product = product or self.product
        return client.post(
            CART_ITEMS_URL, {"product_id": product.id, "quantity": quantity}, format="json"
        )

    def _checkout(self, client=None):
        client = client or self.client
        return client.post(
            ORDERS_URL,
            {
                "shipping_name": "Kim",
                "shipping_phone": "010-1234-5678",
                "shipping_address": "Seoul",
                "remark": "",
            },
            format="json",
        )

    def test_add_to_cart_then_checkout_success(self):
        add_res = self._add_to_cart(2)
        self.assertEqual(add_res.status_code, 201, add_res.data)
        self.assertEqual(add_res.data["code"], "OK")

        cart_res = self.client.get(CART_URL)
        self.assertEqual(cart_res.status_code, 200)
        self.assertEqual(len(cart_res.data["data"]["items"]), 1)
        self.assertEqual(cart_res.data["data"]["total_amount"], 2000)

        checkout_res = self._checkout()
        self.assertEqual(checkout_res.status_code, 201, checkout_res.data)
        self.assertEqual(checkout_res.data["code"], "OK")
        order_data = checkout_res.data["data"]
        self.assertEqual(order_data["total_amount"], 2000)
        self.assertEqual(order_data["status"], "pending")
        self.assertEqual(len(order_data["items"]), 1)

        self.assertEqual(CartItem.objects.filter(member=self.member).count(), 0)
        self.assertEqual(Order.objects.filter(member=self.member).count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_checkout_fails_when_cart_empty(self):
        res = self._checkout()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "CART_EMPTY")

    def test_add_to_cart_fails_when_stock_insufficient(self):
        res = self._add_to_cart(self.product.stock + 1)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "PRODUCT_STOCK_INSUFFICIENT")
        self.assertEqual(CartItem.objects.filter(member=self.member).count(), 0)

    def test_update_cart_item_fails_when_stock_insufficient(self):
        add_res = self._add_to_cart(2)
        item_id = add_res.data["data"]["id"]
        patch_res = self.client.patch(
            f"{CART_ITEMS_URL}/{item_id}", {"quantity": self.product.stock + 1}, format="json"
        )
        self.assertEqual(patch_res.status_code, 400)
        self.assertEqual(patch_res.data["code"], "PRODUCT_STOCK_INSUFFICIENT")

    def test_checkout_revalidates_stock_drop_after_add_to_cart(self):
        """M12：加购后库存被外部改小，结账须失败且不扣库存、不建单。"""
        add_res = self._add_to_cart(2)
        self.assertEqual(add_res.status_code, 201, add_res.data)

        self.product.stock = 1
        self.product.save(update_fields=["stock"])

        checkout_res = self._checkout()
        self.assertEqual(checkout_res.status_code, 400)
        self.assertEqual(checkout_res.data["code"], "PRODUCT_STOCK_INSUFFICIENT")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertEqual(Order.objects.filter(member=self.member).count(), 0)
        self.assertEqual(CartItem.objects.filter(member=self.member).count(), 1)

    def test_second_checkout_fails_when_stock_exhausted(self):
        """同 SKU 连续两笔：第一笔扣光可用库存后，第二笔须失败且总扣减不超过原库存。"""
        other = User.objects.create_user(
            email="buyer_checkout2@test.local",
            password="pass12345",
            role="member",
            is_active=True,
        )
        other_client = APIClient()
        other_client.force_authenticate(user=other)

        self.product.stock = 3
        self.product.save(update_fields=["stock"])

        add1 = self._add_to_cart(3)
        self.assertEqual(add1.status_code, 201, add1.data)
        add2 = self._add_to_cart(2, client=other_client)
        self.assertEqual(add2.status_code, 201, add2.data)

        first = self._checkout()
        self.assertEqual(first.status_code, 201, first.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)

        second = self._checkout(client=other_client)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.data["code"], "PRODUCT_STOCK_INSUFFICIENT")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
        self.assertEqual(Order.objects.count(), 1)
