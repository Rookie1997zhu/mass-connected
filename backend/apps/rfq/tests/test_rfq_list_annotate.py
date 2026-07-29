from django.db.models import Count
from django.test import TestCase

from apps.accounts.models import User
from apps.rfq.models import Quote, RFQ, ServiceCategory
from apps.rfq.serializers import RFQListSerializer


class RfqListAnnotateTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email="buyer_rfq_ann@test.com", password="pass12345", role="member", is_active=True
        )
        self.cat = ServiceCategory.objects.create(name={"ko": "CNC"}, slug="cnc-ann-test")
        self.rfq = RFQ.objects.create(
            buyer=self.buyer,
            service_category=self.cat,
            scope="internal",
            status="submitted",
            quantity=10,
        )
        Quote.objects.create(rfq=self.rfq, price_amount=1000, status="sent")
        Quote.objects.create(rfq=self.rfq, price_amount=2000, status="sent")

    def test_annotated_quotes_count_used(self):
        qs = RFQ.objects.filter(pk=self.rfq.pk).annotate(quotes_count=Count("quotes", distinct=True))
        obj = qs.get()
        data = RFQListSerializer(obj).data
        self.assertEqual(data["quotes_count"], 2)
        # annotated attribute present (no per-row .count() needed)
        self.assertEqual(obj.quotes_count, 2)
