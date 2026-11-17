import csv
import logging
from datetime import datetime

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.blog.authentication import BlogMcpApiKeyAuthentication
from apps.content.models import Case, ContentPage, Download, FAQ, NavItem, News
from apps.content.serializers import (
    CaseSerializer,
    ContentPageSerializer,
    DownloadSerializer,
    FAQSerializer,
    NavItemSerializer,
    NewsSerializer,
)
from core.exceptions import AppAPIException
from core.media_urls import absolute_media_url
from core.pagination import StandardPagination
from core.permissions import IsAdminRole
from core.responses import error_response, success_response

logger = logging.getLogger(__name__)

FULL_LIST_WARN_THRESHOLD = 500


def _warn_if_large_full_list(label: str, count: int) -> None:
    if count > FULL_LIST_WARN_THRESHOLD:
        logger.warning("full_list_large label=%s count=%s", label, count)


class _CsvEcho:
    """伪缓冲：csv.writer 写入后直接返回该行，供 StreamingHttpResponse 逐行输出。"""

    def write(self, value):
        return value


def _i18n_value(field, lang: str) -> str:
    """从 I18n JSON 字段取指定语言文本；缺失时回退到任意已填值。"""
    if isinstance(field, dict):
        value = field.get(lang)
        if value:
            return str(value)
        for fallback in field.values():
            if fallback:
                return str(fallback)
        return ""
    return str(field or "")


def _stream_csv_response(filename_prefix: str, header: list[str], row_iter):
    """构造带 UTF-8 BOM 的流式 CSV 响应；row_iter 逐行产出（内部使用 queryset.iterator()）。"""
    writer = csv.writer(_CsvEcho())

    def generate():
        # UTF-8 BOM：让 Excel 正确识别中文/韩文
        yield "\ufeff"
        yield writer.writerow(header)
        for row in row_iter:
            yield writer.writerow(row)

    date_str = datetime.now().strftime("%Y%m%d")
    response = StreamingHttpResponse(generate(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{filename_prefix}_{date_str}.csv"'
    )
    return response


def admin_crud_list_create(model, serializer_class, request, ordering="-updated_at"):
    if request.method == "GET":
        qs = model.objects.all().order_by(ordering)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(serializer_class(page, many=True, context={"request": request}).data)
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


def admin_crud_detail(model, serializer_class, request, pk):
    obj = get_object_or_404(model, pk=pk)
    if request.method == "GET":
        return success_response(serializer_class(obj, context={"request": request}).data, request=request)
    if request.method == "PATCH":
        serializer = serializer_class(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)
    obj.delete()
    return success_response({}, message="已删除", request=request)


class PublicCaseListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Case.objects.filter(is_published=True).order_by("-published_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(CaseSerializer(page, many=True).data)


class PublicCaseDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        obj = get_object_or_404(Case, pk=pk, is_published=True)
        return success_response(CaseSerializer(obj).data, request=request)


class PublicNewsListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = News.objects.filter(is_published=True).order_by("-published_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(NewsSerializer(page, many=True).data)


class PublicNewsDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        obj = get_object_or_404(News, pk=pk, is_published=True)
        return success_response(NewsSerializer(obj).data, request=request)


class PublicFAQListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get(self, request):
        qs = FAQ.objects.filter(is_active=True).order_by("sort_order")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(FAQSerializer(page, many=True).data)


class PublicDownloadListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Download.objects.filter(is_active=True).order_by("sort_order")
        locale = request.query_params.get("locale")
        if locale:
            qs = qs.filter(locale=locale)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            DownloadSerializer(page, many=True, context={"request": request}).data
        )


class PublicContentPageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, page_key):
        obj = get_object_or_404(ContentPage, page_key=page_key)
        return success_response(ContentPageSerializer(obj).data, request=request)


class AdminCaseView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        return admin_crud_list_create(Case, CaseSerializer, request)

    def post(self, request):
        return admin_crud_list_create(Case, CaseSerializer, request)


class AdminCaseDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        return admin_crud_detail(Case, CaseSerializer, request, pk)

    def patch(self, request, pk):
        return admin_crud_detail(Case, CaseSerializer, request, pk)

    def delete(self, request, pk):
        return admin_crud_detail(Case, CaseSerializer, request, pk)


class AdminNewsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        return admin_crud_list_create(News, NewsSerializer, request)

    def post(self, request):
        return admin_crud_list_create(News, NewsSerializer, request)


class AdminNewsDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        return admin_crud_detail(News, NewsSerializer, request, pk)

    def patch(self, request, pk):
        return admin_crud_detail(News, NewsSerializer, request, pk)

    def delete(self, request, pk):
        return admin_crud_detail(News, NewsSerializer, request, pk)


class AdminNewsExportView(APIView):
    """导出资讯列表为 CSV（与列表同筛选/排序，不分页，流式输出）。"""

    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = News.objects.all().order_by("-updated_at")
        header = [
            "id",
            "title_ko",
            "title_en",
            "title_zh",
            "is_published",
            "published_at",
            "created_at",
            "updated_at",
        ]

        def rows():
            for obj in qs.iterator():
                yield [
                    obj.id,
                    _i18n_value(obj.title, "ko"),
                    _i18n_value(obj.title, "en"),
                    _i18n_value(obj.title, "zh"),
                    "1" if obj.is_published else "0",
                    obj.published_at.isoformat() if obj.published_at else "",
                    obj.created_at.isoformat() if obj.created_at else "",
                    obj.updated_at.isoformat() if obj.updated_at else "",
                ]

        return _stream_csv_response("news", header, rows())


class AdminDownloadExportView(APIView):
    """导出下载资源列表为 CSV（与列表同筛选/排序，不分页，流式输出）。"""

    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = Download.objects.all().order_by("sort_order")
        header = [
            "id",
            "title_ko",
            "title_en",
            "title_zh",
            "file_type",
            "locale",
            "sort_order",
            "is_active",
            "file",
        ]

        def rows():
            for obj in qs.iterator():
                yield [
                    obj.id,
                    _i18n_value(obj.title, "ko"),
                    _i18n_value(obj.title, "en"),
                    _i18n_value(obj.title, "zh"),
                    obj.file_type,
                    obj.locale,
                    obj.sort_order,
                    "1" if obj.is_active else "0",
                    obj.file.name if obj.file else "",
                ]

        return _stream_csv_response("downloads", header, rows())


class AdminFAQView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = FAQ.objects.all().order_by("sort_order")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(FAQSerializer(page, many=True).data)

    def post(self, request):
        serializer = FAQSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminFAQDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        return admin_crud_detail(FAQ, FAQSerializer, request, pk)

    def delete(self, request, pk):
        return admin_crud_detail(FAQ, FAQSerializer, request, pk)


class AdminDownloadView(APIView):
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Download.objects.all().order_by("sort_order")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            DownloadSerializer(page, many=True, context={"request": request}).data
        )

    def post(self, request):
        import json

        data = request.data.copy()
        title = data.get("title")
        if isinstance(title, str):
            try:
                data["title"] = json.loads(title)
            except json.JSONDecodeError:
                data["title"] = {"ko": title}
        serializer = DownloadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminContentPageView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = ContentPage.objects.all().order_by("page_key")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ContentPageSerializer(page, many=True).data)

    def post(self, request):
        serializer = ContentPageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminContentPageDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        return admin_crud_detail(ContentPage, ContentPageSerializer, request, pk)


class PublicNavigationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = NavItem.objects.filter(is_active=True).order_by("sort_order", "id")
        _warn_if_large_full_list("public_nav", qs.count())
        roots = [item for item in qs if item.parent_id is None]
        items = []
        for root in roots:
            children = [c for c in qs if c.parent_id == root.id]
            if not children and not root.path:
                continue
            node = NavItemSerializer(root).data
            node["children"] = NavItemSerializer(children, many=True).data
            items.append(node)
        return success_response({"items": items}, request=request)


class AdminNavigationView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = NavItem.objects.all().order_by("sort_order", "id")
        _warn_if_large_full_list("admin_nav", qs.count())
        return success_response({"items": NavItemSerializer(qs, many=True).data}, request=request)

    def post(self, request):
        serializer = NavItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminNavigationDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        return admin_crud_detail(NavItem, NavItemSerializer, request, pk)

    def delete(self, request, pk):
        return admin_crud_detail(NavItem, NavItemSerializer, request, pk)


class AdminMediaUploadView(APIView):
    """通用媒体上传（供富文本编辑器等复用）。"""

    authentication_classes = [BlogMcpApiKeyAuthentication, JWTAuthentication]
    permission_classes = [IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from django.core.files.storage import default_storage

        file_obj = request.FILES.get("file")
        if not file_obj:
            raise AppAPIException("请上传文件", code="MEDIA_FILE_TYPE_INVALID")
        if file_obj.size > 5 * 1024 * 1024:
            return error_response("MEDIA_FILE_SIZE_EXCEEDED", "文件大小超限", request=request)
        path = default_storage.save(f"uploads/{file_obj.name}", file_obj)
        url = absolute_media_url(request, default_storage.url(path))
        return success_response({"path": path, "url": url}, status=status.HTTP_201_CREATED, request=request)
