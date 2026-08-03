from datetime import date

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from apps.accounts.models import FactoryProfile, SupplierAttachment
from apps.accounts.serializers import (
    FactoryProfileSerializer,
    PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES,
    SupplierAttachmentSerializer,
    SupplierProfileUpdateSerializer,
)
from core.file_validation import validate_upload_file
from core.permissions import IsSupplierRole
from core.responses import error_response, success_response

PROJECT_TERMINAL_STATUSES = ("completed", "cancelled")
PENDING_QUOTE_REQUEST_STATUSES = ("assigned", "viewed", "needs_revision")


class FactoryProfileView(APIView):
    permission_classes = [IsSupplierRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        profile = (
            FactoryProfile.objects.select_related("user")
            .prefetch_related("processes", "tags", "attachments")
            .get(pk=request.user.factory_profile.pk)
        )
        return success_response(
            FactoryProfileSerializer(profile, context={"request": request}).data,
            request=request,
        )

    def patch(self, request):
        profile = get_object_or_404(FactoryProfile, user=request.user)
        serializer = SupplierProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user = request.user
        user_changed = False
        if "name" in request.data:
            user.name = request.data.get("name") or ""
            user_changed = True
        if "phone" in request.data:
            user.phone = request.data.get("phone") or ""
            user_changed = True
        if user_changed:
            user.save(update_fields=["name", "phone", "updated_at"])
        profile = (
            FactoryProfile.objects.select_related("user")
            .prefetch_related("processes", "tags", "attachments")
            .get(pk=profile.pk)
        )
        return success_response(
            FactoryProfileSerializer(profile, context={"request": request}).data,
            message="企业资料已更新",
            request=request,
        )


class SupplierLicenseDownloadView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request):
        profile = get_object_or_404(FactoryProfile, user=request.user)
        if not profile.business_license:
            return error_response("SUPPLIER_LICENSE_MISSING", "营业执照不存在", request=request)
        name = (profile.business_license.name or "").rsplit("/", 1)[-1] or "license"
        return FileResponse(
            profile.business_license.open("rb"), as_attachment=False, filename=name
        )


class SupplierProfileAttachmentView(APIView):
    """供应商维护自己的企业资料附件（可标记是否对买家公开）。"""

    permission_classes = [IsSupplierRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        profile = get_object_or_404(FactoryProfile, user=request.user)
        file_obj = request.FILES.get("file")
        code, msg = validate_upload_file(file_obj)
        if code:
            return error_response(code, msg, request=request)
        category = (request.data.get("category") or "company_profile").strip()
        allowed = {c[0] for c in SupplierAttachment.CATEGORY_CHOICES}
        if category not in allowed:
            return error_response(
                "SUPPLIER_ATTACHMENT_CATEGORY_INVALID",
                "无效的附件分类",
                errors={"category": list(allowed)},
                request=request,
            )
        is_public_raw = request.data.get("is_public", "true")
        if isinstance(is_public_raw, bool):
            is_public = is_public_raw
        else:
            is_public = str(is_public_raw).lower() in {"1", "true", "yes", "on"}
        if is_public and category not in PUBLIC_SUPPLIER_ATTACHMENT_CATEGORIES:
            return error_response(
                "SUPPLIER_ATTACHMENT_NOT_PUBLICABLE",
                "该类附件不可设为公开",
                request=request,
            )
        att = SupplierAttachment.objects.create(
            profile=profile,
            file=file_obj,
            file_name=file_obj.name,
            category=category,
            is_public=is_public,
        )
        return success_response(
            SupplierAttachmentSerializer(att, context={"request": request}).data,
            message="企业资料附件已上传",
            status=status.HTTP_201_CREATED,
            request=request,
        )

    def delete(self, request):
        profile = get_object_or_404(FactoryProfile, user=request.user)
        att_id = request.data.get("attachment_id") or request.query_params.get("attachment_id")
        att = get_object_or_404(SupplierAttachment, pk=att_id, profile=profile)
        if att.file:
            att.file.delete(save=False)
        att.delete()
        return success_response({}, message="附件已删除", request=request)


class SupplierProfileAttachmentDownloadView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request, file_id):
        profile = get_object_or_404(FactoryProfile, user=request.user)
        att = get_object_or_404(SupplierAttachment, pk=file_id, profile=profile)
        if not att.file:
            return error_response("SUPPLIER_ATTACHMENT_MISSING", "文件不存在", request=request)
        return FileResponse(att.file.open("rb"), as_attachment=False, filename=att.file_name)


class SupplierDashboardView(APIView):
    """供应商工作台聚合：企业信息、待办计数、临近截止、最近通知。"""

    permission_classes = [IsSupplierRole]

    def get(self, request):
        user = request.user
        today = date.today()

        company = {
            "company_name": "",
            "short_name": "",
            "city": "",
            "country": "",
            "score": None,
            "status": "",
        }
        try:
            profile = FactoryProfile.objects.get(user=user)
            company = {
                "company_name": profile.company_name or "",
                "short_name": profile.short_name or "",
                "city": profile.city or "",
                "country": profile.country or "",
                "score": profile.score,
                "status": profile.status or "",
            }
        except FactoryProfile.DoesNotExist:
            pass

        pending_quote_requests = 0
        pending_production_orders = 0
        active_projects = 0
        unread_notifications = 0
        upcoming_deadlines = []
        recent_notifications = []

        try:
            from apps.rfq.models import ProductionOrder, QuoteRequest

            pending_quote_requests = QuoteRequest.objects.filter(
                supplier=user,
                status__in=PENDING_QUOTE_REQUEST_STATUSES,
            ).count()
            pending_production_orders = ProductionOrder.objects.filter(
                supplier=user,
                status="pending_confirm",
            ).count()

            qr_rows = (
                QuoteRequest.objects.filter(
                    supplier=user,
                    deadline__isnull=False,
                    deadline__gte=today,
                )
                .select_related("rfq__service_category")
                .order_by("deadline")[:20]
            )
            from apps.i18n.fields import resolve_i18n

            lang = (request.headers.get("Accept-Language") or "ko").split(",")[0].strip()
            lang = lang.split("-")[0].strip()[:2] or "ko"

            for qr in qr_rows:
                cat = getattr(qr.rfq, "service_category", None) if qr.rfq_id else None
                subtitle = resolve_i18n(cat.name, lang) if cat else ""
                upcoming_deadlines.append(
                    {
                        "kind": "quote_request",
                        "id": qr.id,
                        "title": qr.request_no or f"QR-{qr.id}",
                        "subtitle": subtitle,
                        "deadline": qr.deadline.isoformat(),
                        "status": qr.status,
                    }
                )
        except Exception:  # noqa: BLE001
            pass

        try:
            from apps.project.models import Project

            active_projects = (
                Project.objects.filter(supplier=user)
                .exclude(status__in=PROJECT_TERMINAL_STATUSES)
                .count()
            )
            project_rows = (
                Project.objects.filter(
                    supplier=user,
                    expected_delivery_date__isnull=False,
                    expected_delivery_date__gte=today,
                )
                .order_by("expected_delivery_date")[:20]
            )
            for prj in project_rows:
                upcoming_deadlines.append(
                    {
                        "kind": "project",
                        "id": prj.id,
                        "title": prj.project_no or prj.title or f"PRJ-{prj.id}",
                        "subtitle": prj.title or "",
                        "deadline": prj.expected_delivery_date.isoformat(),
                        "status": prj.status,
                    }
                )
        except Exception:  # noqa: BLE001
            pass

        upcoming_deadlines.sort(key=lambda x: x["deadline"])
        upcoming_deadlines = upcoming_deadlines[:8]

        try:
            from apps.notification.models import Notification
            from apps.notification.serializers import NotificationSerializer

            unread_notifications = Notification.objects.filter(
                user=user, is_read=False
            ).count()
            recent_qs = Notification.objects.filter(user=user).order_by("-created_at")[:5]
            recent_notifications = NotificationSerializer(recent_qs, many=True).data
        except Exception:  # noqa: BLE001
            pass

        from apps.accounts.services.workbench import (
            build_supplier_action_items,
            build_unread_chats,
        )
        from core.fx_rate import get_cny_krw_rate

        data = {
            "company": company,
            "counts": {
                "pending_quote_requests": pending_quote_requests,
                "pending_production_orders": pending_production_orders,
                "active_projects": active_projects,
                "unread_notifications": unread_notifications,
            },
            "action_items": build_supplier_action_items(user),
            "unread_chats": build_unread_chats(user),
            "upcoming_deadlines": upcoming_deadlines,
            "recent_notifications": recent_notifications,
            "fx": get_cny_krw_rate(),
        }
        return success_response(data, request=request)
