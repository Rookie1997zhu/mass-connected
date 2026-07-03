from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.notification.models import Notification
from apps.notification.serializers import NotificationSerializer
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsSupplierRole
from core.responses import success_response


class MemberNotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        is_read = request.query_params.get("is_read")
        if is_read in {"true", "false"}:
            qs = qs.filter(is_read=(is_read == "true"))
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class MemberNotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return success_response({"count": count}, request=request)


class MemberNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return success_response(NotificationSerializer(notification).data, request=request)


class MemberNotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return success_response({}, message="全部已读", request=request)


class AdminNotificationListView(MemberNotificationListView):
    permission_classes = [IsAdminRole]


class AdminNotificationUnreadCountView(MemberNotificationUnreadCountView):
    permission_classes = [IsAdminRole]


class AdminNotificationReadView(MemberNotificationReadView):
    permission_classes = [IsAdminRole]


class AdminNotificationReadAllView(MemberNotificationReadAllView):
    permission_classes = [IsAdminRole]


class SupplierNotificationListView(MemberNotificationListView):
    permission_classes = [IsSupplierRole]


class SupplierNotificationUnreadCountView(MemberNotificationUnreadCountView):
    permission_classes = [IsSupplierRole]


class SupplierNotificationReadView(MemberNotificationReadView):
    permission_classes = [IsSupplierRole]


class SupplierNotificationReadAllView(MemberNotificationReadAllView):
    permission_classes = [IsSupplierRole]
