from django.core.cache import cache
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.chat.models import ChatAttachment, Conversation, Message
from apps.chat.serializers import (
    ConversationCreateSerializer,
    ConversationSerializer,
    DisputeOpenSerializer,
    MessageCreateSerializer,
    MessageSerializer,
    OrderReminderCreateSerializer,
)
from core.file_validation import validate_upload_file
from apps.chat.services import (
    after_message_sent,
    check_rate_limit,
    clear_conversation_unread,
    get_or_create_conversation_for_quote_request,
    get_unread_count,
    issue_ws_ticket,
    list_remindable_orders,
    notify_order_reminder,
    open_dispute,
    participant_role,
    resolve_dispute,
    send_message,
    send_order_reminder,
    user_can_access_conversation,
    WS_TICKET_TTL_SECONDS,
)
from apps.rfq.models import QuoteRequest
from core.async_jobs import JOB_TTL_SECONDS, create_job, get_job
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsBuyerRole, IsSupplierRole
from core.responses import error_response, success_response

CHAT_TRANSLATE_CACHE_TTL = 3600


class ChatWsTicketView(APIView):
    """签发短时一次性 WS 握手 ticket（member / supplier / admin 共用逻辑）。"""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ws_ticket"

    def post(self, request):
        ticket = issue_ws_ticket(request.user.id)
        return success_response(
            {"ticket": ticket, "expires_in": WS_TICKET_TTL_SECONDS},
            request=request,
        )


def _conversation_queryset_for_user(user):
    return (
        Conversation.objects.filter(Q(buyer=user) | Q(supplier=user))
        .select_related(
            "quote_request",
            "quote_request__rfq",
            "buyer",
            "supplier",
            "supplier__factory_profile",
        )
        .order_by("-last_message_at", "-id")
    )


def _get_participant_conversation(user, pk):
    return get_object_or_404(_conversation_queryset_for_user(user), pk=pk)


def _message_translate_response(request, conversation, message_id):
    """缓存命中直接同步返回；未命中入队 heavy 任务并返回 job_id 供短轮询。"""
    message = get_object_or_404(Message, pk=message_id, conversation=conversation)
    text = (message.body or "").strip()
    if not text:
        return error_response("VALIDATION_ERROR", "消息内容为空", request=request)
    target_lang = request.data.get("target_lang", "")
    lang = str(target_lang or "").strip().lower()
    cache_key = f"chat:msg_tr:{message.id}:{lang}"
    cached = cache.get(cache_key)
    if cached:
        return success_response(
            {"translated_text": cached, "status": "done"}, request=request
        )

    from apps.chat.heavy_tasks import run_message_translate

    job_id = create_job(
        "chat_msg_translate",
        request.user.id,
        meta={"message_id": message.id, "target_lang": lang},
    )
    run_message_translate.delay(job_id, message.id, target_lang)
    return success_response(
        {
            "job_id": job_id,
            "status": "pending",
            "expires_in": JOB_TTL_SECONDS,
        },
        message="翻译任务已提交",
        status=status.HTTP_202_ACCEPTED,
        request=request,
    )


class _BaseTranslateJobDetailView(APIView):
    """短轮询聊天消息翻译任务状态（仅任务所有者可读），字段与 P2 解析任务对齐。"""

    def get(self, request, job_id):
        job = get_job(job_id)
        if not job:
            return error_response(
                "TRANSLATE_JOB_NOT_FOUND",
                "任务不存在或已过期",
                status=status.HTTP_404_NOT_FOUND,
                request=request,
            )
        if job.get("user_id") != request.user.id:
            return error_response(
                "TRANSLATE_JOB_FORBIDDEN",
                "无权访问该任务",
                status=status.HTTP_403_FORBIDDEN,
                request=request,
            )
        status_value = job.get("status") or "pending"
        payload = {
            "job_id": job.get("job_id") or job_id,
            "kind": job.get("kind"),
            "status": status_value,
            "result": job.get("result"),
            "error_code": job.get("error_code"),
            "error_message": job.get("error_message"),
            "expires_in": JOB_TTL_SECONDS,
        }
        http_status = (
            status.HTTP_202_ACCEPTED if status_value in {"pending", "running"} else 200
        )
        return success_response(payload, message="OK", status=http_status, request=request)


class MemberTranslateJobDetailView(_BaseTranslateJobDetailView):
    permission_classes = [IsBuyerRole]


class SupplierTranslateJobDetailView(_BaseTranslateJobDetailView):
    permission_classes = [IsSupplierRole]


class AdminTranslateJobDetailView(_BaseTranslateJobDetailView):
    permission_classes = [IsAdminRole]


class MemberConversationListCreateView(APIView):
    permission_classes = [IsBuyerRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = _conversation_queryset_for_user(request.user).filter(buyer=request.user)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        data = ConversationSerializer(page, many=True, context={"request": request}).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        ser = ConversationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        qr = get_object_or_404(
            QuoteRequest.objects.select_related("rfq", "supplier"),
            pk=ser.validated_data["quote_request_id"],
            rfq__buyer=request.user,
        )
        conversation = get_or_create_conversation_for_quote_request(qr)
        return success_response(
            ConversationSerializer(conversation, context={"request": request}).data,
            status=201,
            request=request,
        )


class SupplierConversationListCreateView(APIView):
    permission_classes = [IsSupplierRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = _conversation_queryset_for_user(request.user).filter(supplier=request.user)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        data = ConversationSerializer(page, many=True, context={"request": request}).data
        return paginator.get_paginated_response(data)

    def post(self, request):
        ser = ConversationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        qr = get_object_or_404(
            QuoteRequest.objects.select_related("rfq", "supplier"),
            pk=ser.validated_data["quote_request_id"],
            supplier=request.user,
        )
        conversation = get_or_create_conversation_for_quote_request(qr)
        return success_response(
            ConversationSerializer(conversation, context={"request": request}).data,
            status=201,
            request=request,
        )


class MemberChatUnreadCountView(APIView):
    permission_classes = [IsBuyerRole]

    def get(self, request):
        return success_response({"count": get_unread_count(request.user.id)}, request=request)


class SupplierChatUnreadCountView(APIView):
    permission_classes = [IsSupplierRole]

    def get(self, request):
        return success_response({"count": get_unread_count(request.user.id)}, request=request)


class _BaseMessageListCreateView(APIView):
    pagination_class = StandardPagination
    role_gate = None  # "buyer" | "supplier"

    def _get_conversation(self, request, pk):
        conversation = _get_participant_conversation(request.user, pk)
        role = participant_role(conversation, request.user)
        if self.role_gate == "buyer" and role != Message.ROLE_BUYER:
            return None, error_response(
                "CHAT_NOT_PARTICIPANT",
                "无权访问该会话",
                status=403,
                request=request,
            )
        if self.role_gate == "supplier" and role != Message.ROLE_SUPPLIER:
            return None, error_response(
                "CHAT_NOT_PARTICIPANT",
                "无权访问该会话",
                status=403,
                request=request,
            )
        return conversation, None

    def get(self, request, pk):
        conversation, err = self._get_conversation(request, pk)
        if err:
            return err
        qs = conversation.messages.select_related("sender").prefetch_related("attachments").order_by("id")
        after_id = request.query_params.get("after_id")
        if after_id:
            try:
                qs = qs.filter(id__gt=int(after_id))
            except (TypeError, ValueError):
                return error_response("VALIDATION_ERROR", "after_id 无效", request=request)
        before_id = request.query_params.get("before_id")
        if before_id:
            try:
                qs = qs.filter(id__lt=int(before_id))
            except (TypeError, ValueError):
                return error_response("VALIDATION_ERROR", "before_id 无效", request=request)
        # 增量拉取不分页；历史分页倒序再反转由前端处理——默认分页最新页
        if after_id:
            items = list(qs[:100])
            return success_response(
                {"items": MessageSerializer(items, many=True, context={"request": request}).data},
                request=request,
            )
        qs = qs.order_by("-id")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        # 返回时间正序便于聊天窗渲染
        page = list(reversed(page))
        data = MessageSerializer(page, many=True, context={"request": request}).data
        return paginator.get_paginated_response(data)

    def post(self, request, pk):
        conversation, err = self._get_conversation(request, pk)
        if err:
            return err
        if not check_rate_limit(request.user.id):
            return error_response(
                "CHAT_RATE_LIMITED",
                "发送过于频繁，请稍后再试",
                status=429,
                request=request,
            )
        ser = MessageCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        role = participant_role(conversation, request.user)
        try:
            message = send_message(
                conversation=conversation,
                sender=request.user,
                sender_role=role,
                body=ser.validated_data.get("body") or "",
            )
        except ValueError as exc:
            code = str(exc)
            if code == "CHAT_THREAD_READONLY":
                return error_response(
                    "CHAT_THREAD_READONLY",
                    "会话已结束，仅可查看历史消息",
                    status=status.HTTP_403_FORBIDDEN,
                    request=request,
                )
            msg = {
                "EMPTY_BODY": "消息内容不能为空",
                "BODY_TOO_LONG": "消息过长",
            }.get(code, "消息内容无效")
            return error_response(code or "VALIDATION_ERROR", msg, request=request)
        after_message_sent(message)
        return success_response(
            MessageSerializer(message, context={"request": request}).data,
            status=201,
            request=request,
        )


class MemberMessageListCreateView(_BaseMessageListCreateView):
    permission_classes = [IsBuyerRole]
    role_gate = "buyer"


class SupplierMessageListCreateView(_BaseMessageListCreateView):
    permission_classes = [IsSupplierRole]
    role_gate = "supplier"


class _BaseRemindableOrdersView(APIView):
    role_gate = None
    pagination_class = StandardPagination

    def get(self, request, pk):
        conversation = _get_participant_conversation(request.user, pk)
        role = participant_role(conversation, request.user)
        if role is None:
            return error_response("CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request)
        if self.role_gate == "buyer" and role != Message.ROLE_BUYER:
            return error_response("CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request)
        if self.role_gate == "supplier" and role != Message.ROLE_SUPPLIER:
            return error_response("CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request)

        q = request.query_params.get("q", "")
        status = request.query_params.get("status", "")
        items = list_remindable_orders(conversation, q=q, status=status)

        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", 20))
        except (TypeError, ValueError):
            page_size = 20
        page_size = min(max(page_size, 1), 100)
        total = len(items)
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
        start = (page - 1) * page_size
        page_items = items[start : start + page_size]
        return success_response(
            {
                "items": page_items,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                },
            },
            request=request,
        )


class MemberRemindableOrdersView(_BaseRemindableOrdersView):
    permission_classes = [IsBuyerRole]
    role_gate = "buyer"


class SupplierRemindableOrdersView(_BaseRemindableOrdersView):
    permission_classes = [IsSupplierRole]
    role_gate = "supplier"


class _BaseOrderReminderCreateView(APIView):
    role_gate = None

    def post(self, request, pk):
        conversation = _get_participant_conversation(request.user, pk)
        role = participant_role(conversation, request.user)
        if role is None:
            return error_response("CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request)
        if self.role_gate == "buyer" and role != Message.ROLE_BUYER:
            return error_response("CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request)
        if self.role_gate == "supplier" and role != Message.ROLE_SUPPLIER:
            return error_response("CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request)
        if not check_rate_limit(request.user.id):
            return error_response(
                "CHAT_RATE_LIMITED",
                "发送过于频繁，请稍后再试",
                status=429,
                request=request,
            )
        ser = OrderReminderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            message = send_order_reminder(
                conversation=conversation,
                sender=request.user,
                sender_role=role,
                production_order_id=ser.validated_data["production_order_id"],
                note=ser.validated_data.get("note") or "",
            )
        except ValueError as exc:
            code = str(exc)
            if code == "ORDER_NOT_FOUND":
                return error_response("ORDER_NOT_FOUND", "生产单不存在", status=404, request=request)
            if code == "ORDER_NOT_ALLOWED":
                return error_response(
                    "ORDER_NOT_ALLOWED",
                    "只能提醒双方共同的生产单",
                    status=403,
                    request=request,
                )
            return error_response(code or "VALIDATION_ERROR", "发送失败", request=request)
        after_message_sent(message)
        notify_order_reminder(message)
        return success_response(
            MessageSerializer(message, context={"request": request}).data,
            status=201,
            request=request,
        )


class MemberOrderReminderCreateView(_BaseOrderReminderCreateView):
    permission_classes = [IsBuyerRole]
    role_gate = "buyer"


class SupplierOrderReminderCreateView(_BaseOrderReminderCreateView):
    permission_classes = [IsSupplierRole]
    role_gate = "supplier"


class _BaseConversationReadView(APIView):
    role_gate = None

    def post(self, request, pk):
        conversation = _get_participant_conversation(request.user, pk)
        role = participant_role(conversation, request.user)
        if self.role_gate == "buyer" and role != Message.ROLE_BUYER:
            return error_response("CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request)
        if self.role_gate == "supplier" and role != Message.ROLE_SUPPLIER:
            return error_response("CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request)
        count = clear_conversation_unread(request.user.id, conversation)
        return success_response({"count": count}, request=request)


class MemberConversationReadView(_BaseConversationReadView):
    permission_classes = [IsBuyerRole]
    role_gate = "buyer"


class SupplierConversationReadView(_BaseConversationReadView):
    permission_classes = [IsSupplierRole]
    role_gate = "supplier"


class _BaseDisputeOpenView(APIView):
    role_gate = None

    def post(self, request, pk):
        conversation = _get_participant_conversation(request.user, pk)
        role = participant_role(conversation, request.user)
        if role is None:
            return error_response("CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request)
        ser = DisputeOpenSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        open_dispute(conversation, request.user, ser.validated_data.get("reason") or "")
        return success_response(
            ConversationSerializer(conversation, context={"request": request}).data,
            request=request,
        )


class MemberDisputeOpenView(_BaseDisputeOpenView):
    permission_classes = [IsBuyerRole]


class SupplierDisputeOpenView(_BaseDisputeOpenView):
    permission_classes = [IsSupplierRole]


class _BaseDisputeResolveView(APIView):
    def post(self, request, pk):
        conversation = _get_participant_conversation(request.user, pk)
        if participant_role(conversation, request.user) is None:
            return error_response("CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request)
        if conversation.dispute_status != Conversation.DISPUTE_OPEN:
            return error_response("CHAT_DISPUTE_REQUIRED", "当前无进行中的纠纷", request=request)
        resolve_dispute(conversation)
        return success_response(
            ConversationSerializer(conversation, context={"request": request}).data,
            request=request,
        )


class MemberDisputeResolveView(_BaseDisputeResolveView):
    permission_classes = [IsBuyerRole]


class SupplierDisputeResolveView(_BaseDisputeResolveView):
    permission_classes = [IsSupplierRole]


class AdminDisputeListView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request):
        qs = (
            Conversation.objects.filter(dispute_status=Conversation.DISPUTE_OPEN)
            .select_related("quote_request", "buyer", "supplier", "supplier__factory_profile")
            .order_by("-disputed_at", "-id")
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        data = ConversationSerializer(page, many=True, context={"request": request}).data
        return paginator.get_paginated_response(data)


class AdminConversationMessagesView(APIView):
    permission_classes = [IsAdminRole]
    pagination_class = StandardPagination

    def get(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        if not user_can_access_conversation(request.user, conversation, for_admin=True):
            return error_response(
                "CHAT_DISPUTE_REQUIRED",
                "仅纠纷中的会话可供管理员查看",
                status=403,
                request=request,
            )
        qs = conversation.messages.select_related("sender").prefetch_related("attachments")
        before_id = request.query_params.get("before_id")
        if before_id:
            try:
                qs = qs.filter(id__lt=int(before_id))
            except (TypeError, ValueError):
                return error_response("VALIDATION_ERROR", "before_id 无效", request=request)
        qs = qs.order_by("-id")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        # 返回时间正序便于聊天窗渲染
        page = list(reversed(page))
        data = MessageSerializer(
            page, many=True, context={"request": request, "include_original": True}
        ).data
        return paginator.get_paginated_response(data)

    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        if not user_can_access_conversation(request.user, conversation, for_admin=True):
            return error_response(
                "CHAT_DISPUTE_REQUIRED",
                "仅纠纷中的会话可供管理员回复",
                status=403,
                request=request,
            )
        if not check_rate_limit(request.user.id):
            return error_response(
                "CHAT_RATE_LIMITED",
                "发送过于频繁，请稍后再试",
                status=429,
                request=request,
            )
        ser = MessageCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            message = send_message(
                conversation=conversation,
                sender=request.user,
                sender_role=Message.ROLE_PLATFORM,
                body=ser.validated_data["body"],
            )
        except ValueError as exc:
            return error_response(str(exc) or "VALIDATION_ERROR", "消息内容无效", request=request)
        after_message_sent(message)
        return success_response(
            MessageSerializer(
                message, context={"request": request, "include_original": True}
            ).data,
            status=201,
            request=request,
        )


class AdminDisputeResolveView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        if conversation.dispute_status != Conversation.DISPUTE_OPEN:
            return error_response("CHAT_DISPUTE_REQUIRED", "当前无进行中的纠纷", request=request)
        resolve_dispute(conversation)
        return success_response(
            ConversationSerializer(conversation, context={"request": request}).data,
            request=request,
        )


class _BaseMessageTranslateView(APIView):
    role_gate = None  # "buyer" | "supplier" | None
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_translate"

    def post(self, request, pk, message_id):
        conversation = _get_participant_conversation(request.user, pk)
        role = participant_role(conversation, request.user)
        if role is None:
            return error_response(
                "CHAT_NOT_PARTICIPANT",
                "无权访问该会话",
                status=403,
                request=request,
            )
        if self.role_gate == "buyer" and role != Message.ROLE_BUYER:
            return error_response(
                "CHAT_NOT_PARTICIPANT",
                "无权访问该会话",
                status=403,
                request=request,
            )
        if self.role_gate == "supplier" and role != Message.ROLE_SUPPLIER:
            return error_response(
                "CHAT_NOT_PARTICIPANT",
                "无权访问该会话",
                status=403,
                request=request,
            )
        return _message_translate_response(request, conversation, message_id)


class MemberMessageTranslateView(_BaseMessageTranslateView):
    permission_classes = [IsBuyerRole]
    role_gate = "buyer"


class SupplierMessageTranslateView(_BaseMessageTranslateView):
    permission_classes = [IsSupplierRole]
    role_gate = "supplier"


class AdminMessageTranslateView(APIView):
    permission_classes = [IsAdminRole]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_translate"

    def post(self, request, pk, message_id):
        conversation = get_object_or_404(Conversation, pk=pk)
        if not user_can_access_conversation(request.user, conversation, for_admin=True):
            return error_response(
                "CHAT_DISPUTE_REQUIRED",
                "仅纠纷中的会话可供管理员翻译",
                status=403,
                request=request,
            )
        return _message_translate_response(request, conversation, message_id)


class _BaseChatAttachmentUploadView(APIView):
    """上传聊天附件：创建 Message（可空正文）+ ChatAttachment。"""

    parser_classes = [MultiPartParser, FormParser]
    role_gate = None

    def post(self, request, pk):
        conversation = _get_participant_conversation(request.user, pk)
        role = participant_role(conversation, request.user)
        if role is None:
            return error_response(
                "CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request
            )
        if self.role_gate == "buyer" and role != Message.ROLE_BUYER:
            return error_response(
                "CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request
            )
        if self.role_gate == "supplier" and role != Message.ROLE_SUPPLIER:
            return error_response(
                "CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request
            )
        if not check_rate_limit(request.user.id):
            return error_response(
                "CHAT_RATE_LIMITED",
                "发送过于频繁，请稍后再试",
                status=429,
                request=request,
            )
        upload = request.FILES.get("file")
        err_code, ext_or_msg = validate_upload_file(upload)
        if err_code:
            return error_response(err_code, ext_or_msg, request=request)
        body = (request.data.get("body") or "").strip()
        try:
            message = send_message(
                conversation=conversation,
                sender=request.user,
                sender_role=role,
                body=body,
                allow_empty_body=True,
            )
        except ValueError as exc:
            code = str(exc)
            if code == "CHAT_THREAD_READONLY":
                return error_response(
                    "CHAT_THREAD_READONLY",
                    "会话已结束，仅可查看历史消息",
                    status=status.HTTP_403_FORBIDDEN,
                    request=request,
                )
            return error_response(code or "VALIDATION_ERROR", "消息内容无效", request=request)

        att = ChatAttachment.objects.create(
            message=message,
            file=upload,
            file_name=getattr(upload, "name", "")[:255] or f"file.{ext_or_msg}",
            file_type=(getattr(upload, "content_type", "") or ext_or_msg or "")[:64],
            size=getattr(upload, "size", 0) or 0,
        )
        after_message_sent(message)
        data = MessageSerializer(message, context={"request": request}).data
        # 确保附件已刷新
        data["attachments"] = [
            {
                "id": att.id,
                "file_name": att.file_name,
                "file_type": att.file_type,
                "size": att.size,
                "uploaded_at": att.uploaded_at.isoformat() if att.uploaded_at else None,
                "file_url": request.build_absolute_uri(
                    f"/api/{'supplier' if self.role_gate == 'supplier' else 'member'}"
                    f"/chat/conversations/{conversation.id}/attachments/{att.id}/download"
                ),
            }
        ]
        return success_response(data, status=201, request=request)


class MemberChatAttachmentUploadView(_BaseChatAttachmentUploadView):
    permission_classes = [IsBuyerRole]
    role_gate = "buyer"


class SupplierChatAttachmentUploadView(_BaseChatAttachmentUploadView):
    permission_classes = [IsSupplierRole]
    role_gate = "supplier"


class _BaseChatAttachmentDownloadView(APIView):
    role_gate = None

    def get(self, request, pk, attachment_id):
        conversation = _get_participant_conversation(request.user, pk)
        role = participant_role(conversation, request.user)
        if role is None:
            return error_response(
                "CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request
            )
        if self.role_gate == "buyer" and role != Message.ROLE_BUYER:
            return error_response(
                "CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request
            )
        if self.role_gate == "supplier" and role != Message.ROLE_SUPPLIER:
            return error_response(
                "CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request
            )
        att = get_object_or_404(
            ChatAttachment.objects.select_related("message"),
            pk=attachment_id,
            message__conversation=conversation,
        )
        if not att.file:
            return error_response("CHAT_ATTACHMENT_MISSING", "文件不存在", request=request)
        return FileResponse(att.file.open("rb"), as_attachment=False, filename=att.file_name)


class MemberChatAttachmentDownloadView(_BaseChatAttachmentDownloadView):
    permission_classes = [IsBuyerRole]
    role_gate = "buyer"


class SupplierChatAttachmentDownloadView(_BaseChatAttachmentDownloadView):
    permission_classes = [IsSupplierRole]
    role_gate = "supplier"


class AdminChatAttachmentDownloadView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk, attachment_id):
        conversation = get_object_or_404(Conversation, pk=pk)
        if not user_can_access_conversation(request.user, conversation, for_admin=True):
            return error_response(
                "CHAT_DISPUTE_REQUIRED",
                "仅纠纷中的会话可供管理员下载附件",
                status=403,
                request=request,
            )
        att = get_object_or_404(
            ChatAttachment.objects.select_related("message"),
            pk=attachment_id,
            message__conversation=conversation,
        )
        if not att.file:
            return error_response("CHAT_ATTACHMENT_MISSING", "文件不存在", request=request)
        return FileResponse(att.file.open("rb"), as_attachment=False, filename=att.file_name)


class _BaseChatAttachmentUploadView(APIView):
    """multipart 上传聊天附件：创建 Message（可空正文）+ ChatAttachment。"""

    parser_classes = [MultiPartParser, FormParser]
    role_gate = None

    def post(self, request, pk):
        conversation = _get_participant_conversation(request.user, pk)
        role = participant_role(conversation, request.user)
        if role is None:
            return error_response(
                "CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request
            )
        if self.role_gate == "buyer" and role != Message.ROLE_BUYER:
            return error_response(
                "CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request
            )
        if self.role_gate == "supplier" and role != Message.ROLE_SUPPLIER:
            return error_response(
                "CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request
            )
        if not check_rate_limit(request.user.id):
            return error_response(
                "CHAT_RATE_LIMITED",
                "发送过于频繁，请稍后再试",
                status=429,
                request=request,
            )
        upload = request.FILES.get("file")
        err_code, ext_or_msg = validate_upload_file(upload)
        if err_code:
            return error_response(err_code, ext_or_msg, request=request)
        body = (request.data.get("body") or "").strip()
        try:
            message = send_message(
                conversation=conversation,
                sender=request.user,
                sender_role=role,
                body=body,
                allow_empty_body=True,
            )
        except ValueError as exc:
            code = str(exc)
            if code == "CHAT_THREAD_READONLY":
                return error_response(
                    "CHAT_THREAD_READONLY",
                    "会话已结束，仅可查看历史消息",
                    status=status.HTTP_403_FORBIDDEN,
                    request=request,
                )
            return error_response(code or "VALIDATION_ERROR", "消息内容无效", request=request)
        ChatAttachment.objects.create(
            message=message,
            file=upload,
            file_name=upload.name[:255],
            file_type=ext_or_msg,
            size=getattr(upload, "size", 0) or 0,
        )
        after_message_sent(message)
        message = Message.objects.prefetch_related("attachments").get(pk=message.pk)
        return success_response(
            MessageSerializer(message, context={"request": request}).data,
            status=201,
            request=request,
        )


class MemberChatAttachmentUploadView(_BaseChatAttachmentUploadView):
    permission_classes = [IsBuyerRole]
    role_gate = "buyer"


class SupplierChatAttachmentUploadView(_BaseChatAttachmentUploadView):
    permission_classes = [IsSupplierRole]
    role_gate = "supplier"


class _BaseChatAttachmentDownloadView(APIView):
    role_gate = None

    def get(self, request, pk, attachment_id):
        conversation = _get_participant_conversation(request.user, pk)
        role = participant_role(conversation, request.user)
        if role is None:
            return error_response(
                "CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request
            )
        if self.role_gate == "buyer" and role != Message.ROLE_BUYER:
            return error_response(
                "CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request
            )
        if self.role_gate == "supplier" and role != Message.ROLE_SUPPLIER:
            return error_response(
                "CHAT_NOT_PARTICIPANT", "无权访问该会话", status=403, request=request
            )
        att = get_object_or_404(
            ChatAttachment.objects.select_related("message"),
            pk=attachment_id,
            message__conversation=conversation,
        )
        if not att.file:
            return error_response("CHAT_ATTACHMENT_MISSING", "文件不存在", request=request)
        return FileResponse(
            att.file.open("rb"), as_attachment=False, filename=att.file_name or "file"
        )


class MemberChatAttachmentDownloadView(_BaseChatAttachmentDownloadView):
    permission_classes = [IsBuyerRole]
    role_gate = "buyer"


class SupplierChatAttachmentDownloadView(_BaseChatAttachmentDownloadView):
    permission_classes = [IsSupplierRole]
    role_gate = "supplier"


class AdminChatAttachmentDownloadView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, pk, attachment_id):
        conversation = get_object_or_404(Conversation, pk=pk)
        if not user_can_access_conversation(request.user, conversation, for_admin=True):
            return error_response(
                "CHAT_DISPUTE_REQUIRED",
                "仅纠纷中的会话可供管理员下载附件",
                status=403,
                request=request,
            )
        att = get_object_or_404(
            ChatAttachment.objects.select_related("message"),
            pk=attachment_id,
            message__conversation=conversation,
        )
        if not att.file:
            return error_response("CHAT_ATTACHMENT_MISSING", "文件不存在", request=request)
        return FileResponse(
            att.file.open("rb"), as_attachment=False, filename=att.file_name or "file"
        )
