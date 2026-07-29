from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.inquiry.models import Inquiry
from apps.inquiry.serializers import InquirySerializer
from apps.notification.services import notify_staff
from core.pagination import StandardPagination
from core.permissions import IsAdminRole
from core.responses import success_response


class PublicInquiryCreateView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "inquiry"

    def post(self, request):
        serializer = InquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry = serializer.save(source=request.data.get("source", "contact"))
        notify_staff(
            "inquiry",
            "新询盘",
            f"收到新询盘：{inquiry.name or inquiry.email or '匿名'}",
            related_type="inquiry",
            related_id=inquiry.id,
        )
        return success_response(
            InquirySerializer(inquiry).data,
            message="提交成功",
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminInquiryListView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = Inquiry.objects.all().order_by("-created_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(InquirySerializer(page, many=True).data)


class AdminInquiryDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        obj = get_object_or_404(Inquiry, pk=pk)
        return success_response(InquirySerializer(obj).data, request=request)

    def patch(self, request, pk):
        obj = get_object_or_404(Inquiry, pk=pk)
        serializer = InquirySerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)
