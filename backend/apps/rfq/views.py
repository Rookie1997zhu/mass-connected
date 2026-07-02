from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from apps.rfq.models import RFQ, Quote, RFQAttachment, ServiceCategory
from apps.rfq.serializers import (
    AdminQuoteCreateSerializer,
    DemandHallDetailSerializer,
    DemandHallListSerializer,
    FactoryQuoteCreateSerializer,
    QuoteSerializer,
    RFQCreateSerializer,
    RFQDetailSerializer,
    RFQListSerializer,
    ServiceCategorySerializer,
)
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsFactoryRole, IsMemberRole
from core.responses import error_response, success_response

ALLOWED_ATTACHMENT_EXTENSIONS = {
    "pdf", "step", "stp", "igs", "iges", "dwg", "dxf", "x_t", "x_b",
    "sldprt", "stl", "3mf", "zip", "rar", "7z",
    "jpg", "jpeg", "png", "gif", "webp", "xlsx", "xls", "docx", "doc", "csv", "txt",
}
MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024
OPEN_RFQ_STATUSES = {"submitted", "quoting", "quoted", "negotiating"}


def get_lang(request):
    return request.query_params.get("lang") or request.headers.get("Accept-Language", "ko")[:2]


class PublicServiceCategoryListView(APIView):
    def get(self, request):
        qs = ServiceCategory.objects.filter(is_active=True).order_by("sort_order", "id")
        return success_response(
            {"items": ServiceCategorySerializer(qs, many=True).data},
            request=request,
        )


class MemberRFQListCreateView(APIView):
    permission_classes = [IsMemberRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = RFQ.objects.filter(buyer=request.user).select_related("service_category").order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = RFQListSerializer(page, many=True, context={"lang": get_lang(request)})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = RFQCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scope = serializer.validated_data.get("scope", "internal")
        if scope not in {"internal", "public"}:
            scope = "internal"
        rfq = serializer.save(buyer=request.user, scope=scope, status="submitted")
        return success_response(
            RFQDetailSerializer(rfq, context={"request": request, "lang": get_lang(request)}).data,
            message="询价已提交",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class MemberRFQDetailView(APIView):
    permission_classes = [IsMemberRole]

    def get(self, request, pk):
        rfq = get_object_or_404(
            RFQ.objects.select_related("service_category", "buyer")
            .prefetch_related("attachments", "quotes__supplier__factory_profile"),
            pk=pk,
            buyer=request.user,
        )
        return success_response(
            RFQDetailSerializer(rfq, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
        )


class MemberRFQAttachmentView(APIView):
    permission_classes = [IsMemberRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        file_obj = request.FILES.get("file")
        if not file_obj:
            return error_response("MEDIA_FILE_TYPE_INVALID", "请上传文件", request=request)
        ext = file_obj.name.rsplit(".", 1)[-1].lower() if "." in file_obj.name else ""
        if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
            return error_response(
                "MEDIA_FILE_TYPE_INVALID",
                "不支持的文件类型",
                errors={"ext": ext},
                request=request,
            )
        if file_obj.size > MAX_ATTACHMENT_SIZE:
            return error_response(
                "MEDIA_FILE_SIZE_EXCEEDED",
                "文件大小超限（最大 20MB）",
                request=request,
            )
        attachment = RFQAttachment.objects.create(
            rfq=rfq,
            file=file_obj,
            file_name=file_obj.name,
            file_type=ext,
            size=file_obj.size,
        )
        from apps.rfq.serializers import RFQAttachmentSerializer

        return success_response(
            RFQAttachmentSerializer(attachment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class MemberQuoteAcceptView(APIView):
    permission_classes = [IsMemberRole]

    def post(self, request, pk, quote_id):
        rfq = get_object_or_404(RFQ, pk=pk, buyer=request.user)
        quote = Quote.objects.filter(pk=quote_id, rfq=rfq).first()
        if not quote:
            return error_response(
                "QUOTE_NOT_FOUND",
                "报价不存在",
                status=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        if quote.valid_until and quote.valid_until < timezone.now().date():
            return error_response("QUOTE_EXPIRED", "报价已过期", request=request)
        quote.status = "accepted"
        quote.save(update_fields=["status", "updated_at"])
        rfq.quotes.exclude(pk=quote.pk).update(status="rejected")
        rfq.status = "won"
        rfq.save(update_fields=["status", "updated_at"])
        return success_response(
            QuoteSerializer(quote).data,
            message="已接受报价",
            request=request,
        )


class FactoryRFQListView(APIView):
    permission_classes = [IsFactoryRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = (
            RFQ.objects.filter(scope="public", status__in=OPEN_RFQ_STATUSES)
            .select_related("service_category")
            .order_by("-created_at")
        )
        category_id = request.query_params.get("service_category_id")
        if category_id:
            qs = qs.filter(service_category_id=category_id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = DemandHallListSerializer(page, many=True, context={"lang": get_lang(request)})
        return paginator.get_paginated_response(serializer.data)


class FactoryRFQDetailView(APIView):
    permission_classes = [IsFactoryRole]

    def get(self, request, pk):
        rfq = get_object_or_404(
            RFQ.objects.filter(scope="public", status__in=OPEN_RFQ_STATUSES)
            .select_related("service_category")
            .prefetch_related("attachments", "quotes"),
            pk=pk,
        )
        return success_response(
            DemandHallDetailSerializer(rfq, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
        )


class FactoryRFQQuoteCreateView(APIView):
    permission_classes = [IsFactoryRole]

    def post(self, request, pk):
        rfq = get_object_or_404(RFQ, pk=pk, scope="public", status__in=OPEN_RFQ_STATUSES)
        if Quote.objects.filter(rfq=rfq, supplier=request.user).exists():
            return error_response(
                "QUOTE_ALREADY_EXISTS",
                "您已对该需求提交过报价",
                request=request,
            )
        serializer = FactoryQuoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote = serializer.save(
            rfq=rfq,
            supplier=request.user,
            created_by=request.user,
            status="sent",
        )
        if rfq.status == "submitted":
            rfq.status = "quoting"
            rfq.save(update_fields=["status", "updated_at"])
        elif rfq.status == "quoting":
            rfq.status = "quoted"
            rfq.save(update_fields=["status", "updated_at"])
        return success_response(
            QuoteSerializer(quote).data,
            message="报价已提交",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class FactoryQuoteListView(APIView):
    permission_classes = [IsFactoryRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = (
            Quote.objects.filter(supplier=request.user)
            .select_related("rfq", "rfq__service_category")
            .order_by("-created_at")
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        items = []
        for quote in page:
            items.append(
                {
                    **QuoteSerializer(quote).data,
                    "rfq_no": quote.rfq.rfq_no,
                    "rfq_id": quote.rfq_id,
                    "rfq_status": quote.rfq.status,
                }
            )
        return paginator.get_paginated_response(items)


class AdminServiceCategoryListCreateView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = ServiceCategory.objects.all().order_by("sort_order", "id")
        return success_response(
            {"items": ServiceCategorySerializer(qs, many=True).data},
            request=request,
        )

    def post(self, request):
        serializer = ServiceCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminServiceCategoryDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        obj = get_object_or_404(ServiceCategory, pk=pk)
        return success_response(ServiceCategorySerializer(obj).data, request=request)

    def patch(self, request, pk):
        obj = get_object_or_404(ServiceCategory, pk=pk)
        serializer = ServiceCategorySerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)


class AdminRFQListView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = RFQ.objects.select_related("service_category", "buyer").order_by("-created_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        category_id = request.query_params.get("service_category_id")
        if category_id:
            qs = qs.filter(service_category_id=category_id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = RFQListSerializer(page, many=True, context={"lang": get_lang(request)})
        return paginator.get_paginated_response(serializer.data)


class AdminRFQDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        rfq = get_object_or_404(
            RFQ.objects.select_related("service_category", "buyer")
            .prefetch_related("attachments", "quotes__supplier__factory_profile"),
            pk=pk,
        )
        return success_response(
            RFQDetailSerializer(rfq, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
        )


class AdminRFQStatusView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        rfq = get_object_or_404(RFQ, pk=pk)
        new_status = request.data.get("status")
        valid_statuses = {choice[0] for choice in RFQ.STATUS_CHOICES}
        if new_status not in valid_statuses:
            return error_response(
                "RFQ_STATUS_INVALID",
                "无效的状态",
                errors={"status": list(valid_statuses)},
                request=request,
            )
        rfq.status = new_status
        rfq.save(update_fields=["status", "updated_at"])
        return success_response(
            RFQDetailSerializer(rfq, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
        )


class AdminRFQQuoteCreateView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        rfq = get_object_or_404(RFQ, pk=pk)
        serializer = AdminQuoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote = serializer.save(rfq=rfq, created_by=request.user, status="sent")
        if rfq.status in {"submitted", "quoting"}:
            rfq.status = "quoted"
            rfq.save(update_fields=["status", "updated_at"])
        return success_response(
            QuoteSerializer(quote).data,
            message="报价已发送",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminQuoteDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        quote = get_object_or_404(Quote, pk=pk)
        serializer = AdminQuoteCreateSerializer(quote, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(QuoteSerializer(quote).data, request=request)
