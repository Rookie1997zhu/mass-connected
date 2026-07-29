from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
import logging

from apps.catalog.models import Category, Product, ProductImage
from apps.catalog.serializers import (
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductWriteSerializer,
)
from core.pagination import StandardPagination
from core.permissions import IsAdminRole
from core.responses import success_response

logger = logging.getLogger(__name__)


def get_lang(request):
    return request.query_params.get("lang") or request.headers.get("Accept-Language", "ko")[:2]


class PublicCategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Category.objects.filter(is_active=True).order_by("sort_order", "id")
        count = qs.count()
        if count > 500:
            logger.warning("full_list_large label=public_categories count=%s", count)
        return success_response({"items": CategorySerializer(qs, many=True).data}, request=request)


class PublicProductListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Product.objects.filter(is_active=True, is_shop_visible=True).select_related("category").prefetch_related("images")
        category_id = request.query_params.get("category_id")
        if category_id:
            qs = qs.filter(category_id=category_id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = ProductListSerializer(page, many=True, context={"request": request, "lang": get_lang(request)})
        return paginator.get_paginated_response(serializer.data)


class PublicProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        product = get_object_or_404(
            Product.objects.filter(is_active=True, is_shop_visible=True)
            .select_related("category")
            .prefetch_related("images"),
            pk=pk,
        )
        return success_response(
            ProductDetailSerializer(product, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
        )


class AdminCategoryListCreateView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = Category.objects.all().order_by("sort_order", "id")
        return success_response({"items": CategorySerializer(qs, many=True).data}, request=request)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminCategoryDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        obj = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)


class AdminProductListCreateView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Product.objects.select_related("category").prefetch_related("images").order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = ProductListSerializer(page, many=True, context={"request": request, "lang": get_lang(request)})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ProductWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return success_response(
            ProductDetailSerializer(product, context={"request": request, "lang": get_lang(request)}).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )


class AdminProductDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        product = get_object_or_404(Product.objects.select_related("category").prefetch_related("images"), pk=pk)
        return success_response(
            ProductDetailSerializer(product, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
        )

    def patch(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductWriteSerializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return success_response(
            ProductDetailSerializer(product, context={"request": request, "lang": get_lang(request)}).data,
            request=request,
        )


class AdminProductImageUploadView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        file_obj = request.FILES.get("file")
        is_cover = request.data.get("is_cover") in {True, "true", "1", 1}
        image = ProductImage.objects.create(product=product, file=file_obj, is_cover=is_cover)
        if is_cover:
            product.images.exclude(pk=image.pk).update(is_cover=False)
        from apps.catalog.serializers import ProductImageSerializer

        return success_response(
            ProductImageSerializer(image, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
            request=request,
        )
