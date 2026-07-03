from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

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
from core.pagination import StandardPagination
from core.permissions import IsAdminRole
from core.responses import error_response, success_response


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
    def get(self, request):
        qs = Case.objects.filter(is_published=True).order_by("-published_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(CaseSerializer(page, many=True).data)


class PublicCaseDetailView(APIView):
    def get(self, request, pk):
        obj = get_object_or_404(Case, pk=pk, is_published=True)
        return success_response(CaseSerializer(obj).data, request=request)


class PublicNewsListView(APIView):
    def get(self, request):
        qs = News.objects.filter(is_published=True).order_by("-published_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(NewsSerializer(page, many=True).data)


class PublicNewsDetailView(APIView):
    def get(self, request, pk):
        obj = get_object_or_404(News, pk=pk, is_published=True)
        return success_response(NewsSerializer(obj).data, request=request)


class PublicFAQListView(APIView):
    def get(self, request):
        qs = FAQ.objects.filter(is_active=True).order_by("sort_order")
        return success_response({"items": FAQSerializer(qs, many=True).data}, request=request)


class PublicDownloadListView(APIView):
    def get(self, request):
        qs = Download.objects.filter(is_active=True).order_by("sort_order")
        locale = request.query_params.get("locale")
        if locale:
            qs = qs.filter(locale=locale)
        return success_response(
            {"items": DownloadSerializer(qs, many=True, context={"request": request}).data},
            request=request,
        )


class PublicContentPageView(APIView):
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


class AdminFAQView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = FAQ.objects.all().order_by("sort_order")
        return success_response({"items": FAQSerializer(qs, many=True).data}, request=request)

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

    def get(self, request):
        qs = Download.objects.all().order_by("sort_order")
        return success_response(
            {"items": DownloadSerializer(qs, many=True, context={"request": request}).data},
            request=request,
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

    def get(self, request):
        qs = ContentPage.objects.all().order_by("page_key")
        return success_response({"items": ContentPageSerializer(qs, many=True).data}, request=request)

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
    def get(self, request):
        qs = NavItem.objects.filter(is_active=True).order_by("sort_order", "id")
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
        url = request.build_absolute_uri(default_storage.url(path))
        return success_response({"path": path, "url": url}, status=status.HTTP_201_CREATED, request=request)
