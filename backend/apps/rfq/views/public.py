from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.rfq.models import ServiceCategory
from apps.rfq.serializers import (
    DemandHallDetailSerializer,
    DemandHallListSerializer,
    ServiceCategorySerializer,
)
from core.pagination import StandardPagination
from core.responses import success_response

from ._helpers import get_lang, open_demand_hall_queryset


class PublicServiceCategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = ServiceCategory.objects.filter(is_active=True).order_by("sort_order", "id")
        return success_response(
            {"items": ServiceCategorySerializer(qs, many=True).data},
            request=request,
        )


class PublicDemandHallListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get(self, request):
        qs = open_demand_hall_queryset()
        category_id = request.query_params.get("service_category_id")
        if category_id:
            qs = qs.filter(service_category_id=category_id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = DemandHallListSerializer(page, many=True, context={"lang": get_lang(request)})
        return paginator.get_paginated_response(serializer.data)


class PublicDemandHallDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        rfq = get_object_or_404(
            open_demand_hall_queryset().prefetch_related("attachments", "quotes"),
            pk=pk,
        )
        return success_response(
            DemandHallDetailSerializer(rfq, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
        )
