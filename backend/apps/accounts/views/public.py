from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.accounts.models import FactoryProfile, SupplierAttachment
from apps.accounts.serializers import (
    PublicPartnerSerializer,
    PublicWebsitePartnerDetailSerializer,
)
from apps.accounts.serializers.base import PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES
from apps.accounts.views._helpers import get_lang
from core.pagination import StandardPagination
from core.responses import success_response


def publicly_listed_partners_queryset():
    return (
        FactoryProfile.objects.filter(status="approved", is_public=True)
        .prefetch_related("processes", "tags", "attachments")
        .order_by("-created_at")
    )


class PublicPartnerListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get(self, request):
        qs = publicly_listed_partners_queryset()
        category_id = request.query_params.get("service_category_id")
        if category_id:
            qs = qs.filter(processes__id=category_id).distinct()
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(company_name__icontains=q)
                | Q(region__icontains=q)
                | Q(intro__icontains=q)
            )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = PublicPartnerSerializer(
            page, many=True, context={"lang": get_lang(request), "request": request}
        )
        return paginator.get_paginated_response(serializer.data)


class PublicPartnerDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        profile = get_object_or_404(publicly_listed_partners_queryset(), pk=pk)
        return success_response(
            PublicWebsitePartnerDetailSerializer(
                profile, context={"lang": get_lang(request), "request": request}
            ).data,
            request=request,
        )


class PublicPartnerAttachmentDownloadView(APIView):
    """网站公开附件下载：档案须 approved+is_public，附件须公开白名单类别。"""

    permission_classes = [AllowAny]

    def get(self, request, file_id):
        att = get_object_or_404(
            SupplierAttachment.objects.select_related("profile"),
            pk=file_id,
            is_public=True,
            category__in=PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES,
            profile__status="approved",
            profile__is_public=True,
        )
        return FileResponse(att.file.open("rb"), as_attachment=False, filename=att.file_name)
