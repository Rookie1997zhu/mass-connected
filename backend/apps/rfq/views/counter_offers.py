from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from apps.notification.services import notify
from apps.rfq.models import Quote, QuoteCounterOffer, RFQ
from apps.rfq.serializers.counter_offers import (
    QuoteCounterOfferCreateSerializer,
    QuoteCounterOfferSerializer,
)
from core.permissions import IsBuyerRole, IsSupplierRole
from core.responses import error_response, success_response


def _buyer_visible_quote(rfq, quote_id):
    return (
        Quote.objects.filter(pk=quote_id, rfq=rfq, is_customer_visible=True)
        .exclude(status="rejected")
        .first()
    )


class MemberQuoteCounterOfferListCreateView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request, pk, quote_id):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        quote = _buyer_visible_quote(rfq, quote_id)
        if not quote:
            return error_response(
                "QUOTE_NOT_FOUND",
                "报价不存在或不可见",
                status=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        qs = QuoteCounterOffer.objects.filter(quote=quote, rfq=rfq).order_by("-created_at", "-id")
        return success_response(
            QuoteCounterOfferSerializer(qs, many=True).data,
            request=request,
        )

    def post(self, request, pk, quote_id):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        if rfq.status in {"won", "closed"}:
            return error_response(
                "RFQ_NOT_OPEN",
                "询价已结束，无法发起还价",
                status=status.HTTP_403_FORBIDDEN,
                request=request,
            )
        quote = _buyer_visible_quote(rfq, quote_id)
        if not quote:
            return error_response(
                "QUOTE_NOT_FOUND",
                "报价不存在或不可见",
                status=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        if quote.status != "sent":
            return error_response(
                "QUOTE_NOT_AVAILABLE",
                "当前方案状态不可还价",
                status=status.HTTP_403_FORBIDDEN,
                request=request,
            )
        ser = QuoteCounterOfferCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        # 同一报价仅保留一条 pending
        QuoteCounterOffer.objects.filter(
            quote=quote, status=QuoteCounterOffer.STATUS_PENDING
        ).update(status=QuoteCounterOffer.STATUS_WITHDRAWN, updated_at=timezone.now())
        co = QuoteCounterOffer.objects.create(
            quote=quote,
            rfq=rfq,
            created_by=request.user,
            quantity=data.get("quantity"),
            target_total_amount=data["target_total_amount"],
            currency=(data.get("currency") or quote.currency or "KRW").upper()[:3],
            lead_time_days=data.get("lead_time_days"),
            note=data.get("note") or "",
            valid_until=data.get("valid_until"),
            status=QuoteCounterOffer.STATUS_PENDING,
        )
        if quote.supplier_id:
            notify(
                quote.supplier,
                "quote",
                "收到客户还价",
                f"询价 {rfq.rfq_no} 有新的结构化还价，请接受/拒绝后按需修订正式报价。"
                " 注意：聊天口头同意≠接受还价≠下单。",
                related_type="quote",
                related_id=quote.id,
                send_email=True,
            )
        return success_response(
            QuoteCounterOfferSerializer(co).data,
            status=status.HTTP_201_CREATED,
            message="还价已提交",
            request=request,
        )


class MemberQuoteCounterOfferWithdrawView(APIView):
    permission_classes = [IsBuyerRole]

    def post(self, request, pk, counter_offer_id):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        co = get_object_or_404(QuoteCounterOffer, pk=counter_offer_id, rfq=rfq)
        if co.status != QuoteCounterOffer.STATUS_PENDING:
            return error_response(
                "COUNTER_OFFER_NOT_PENDING",
                "仅待处理的还价可撤回",
                request=request,
            )
        co.status = QuoteCounterOffer.STATUS_WITHDRAWN
        co.responded_at = timezone.now()
        co.save(update_fields=["status", "responded_at", "updated_at"])
        return success_response(
            QuoteCounterOfferSerializer(co).data,
            message="还价已撤回",
            request=request,
        )


class SupplierQuoteCounterOfferListView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, quote_id):
        quote = get_object_or_404(Quote, pk=quote_id, supplier=request.user)
        qs = QuoteCounterOffer.objects.filter(quote=quote).order_by("-created_at", "-id")
        return success_response(
            QuoteCounterOfferSerializer(qs, many=True).data,
            request=request,
        )


class SupplierQuoteCounterOfferAcceptView(APIView):
    permission_classes = [IsSupplierRole]

    def post(self, request, counter_offer_id):
        co = get_object_or_404(
            QuoteCounterOffer.objects.select_related("quote", "rfq", "quote__supplier"),
            pk=counter_offer_id,
            quote__supplier=request.user,
        )
        if co.status != QuoteCounterOffer.STATUS_PENDING:
            return error_response(
                "COUNTER_OFFER_NOT_PENDING",
                "还价已处理",
                status=status.HTTP_409_CONFLICT,
                request=request,
            )
        if co.rfq.status in {"won", "closed"}:
            return error_response(
                "RFQ_NOT_OPEN",
                "询价已结束",
                status=status.HTTP_403_FORBIDDEN,
                request=request,
            )
        if co.valid_until and co.valid_until < timezone.now().date():
            co.status = QuoteCounterOffer.STATUS_EXPIRED
            co.responded_at = timezone.now()
            co.save(update_fields=["status", "responded_at", "updated_at"])
            return error_response("COUNTER_OFFER_EXPIRED", "还价已过期", request=request)
        # 接受还价不改 Quote 金额；供应商需另行修订正式报价
        co.status = QuoteCounterOffer.STATUS_ACCEPTED
        co.responded_at = timezone.now()
        co.save(update_fields=["status", "responded_at", "updated_at"])
        notify(
            co.rfq.buyer,
            "quote",
            "供应商已接受还价意向",
            f"询价 {co.rfq.rfq_no} 的还价意向已被接受；正式成交价以供应商修订后的公开报价为准。"
            " 聊天口头同意≠接受还价≠下单。",
            related_type="rfq",
            related_id=co.rfq_id,
            send_email=True,
        )
        notify(
            request.user,
            "quote",
            "请修订正式报价",
            f"您已接受询价 {co.rfq.rfq_no} 的还价意向，请尽快修订并提交正式报价。",
            related_type="quote",
            related_id=co.quote_id,
        )
        return success_response(
            QuoteCounterOfferSerializer(co).data,
            message="已接受还价意向，请修订正式报价（不会自动改价）",
            request=request,
        )


class SupplierQuoteCounterOfferRejectView(APIView):
    permission_classes = [IsSupplierRole]

    def post(self, request, counter_offer_id):
        co = get_object_or_404(
            QuoteCounterOffer.objects.select_related("quote", "rfq"),
            pk=counter_offer_id,
            quote__supplier=request.user,
        )
        if co.status != QuoteCounterOffer.STATUS_PENDING:
            return error_response(
                "COUNTER_OFFER_NOT_PENDING",
                "还价已处理",
                request=request,
            )
        co.status = QuoteCounterOffer.STATUS_REJECTED
        co.responded_at = timezone.now()
        co.save(update_fields=["status", "responded_at", "updated_at"])
        notify(
            co.rfq.buyer,
            "quote",
            "供应商已拒绝还价",
            f"询价 {co.rfq.rfq_no} 的还价意向已被拒绝。",
            related_type="rfq",
            related_id=co.rfq_id,
        )
        return success_response(
            QuoteCounterOfferSerializer(co).data,
            message="已拒绝还价",
            request=request,
        )
