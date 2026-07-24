from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.chat.models import Conversation, Message
from apps.chat.serializers import (
    ConversationCreateSerializer,
    ConversationSerializer,
    DisputeOpenSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)
from apps.chat.services import (
    after_message_sent,
    check_rate_limit,
    clear_conversation_unread,
    get_or_create_conversation_for_quote_request,
    get_unread_count,
    open_dispute,
    participant_role,
    resolve_dispute,
    send_message,
    user_can_access_conversation,
)
from apps.project.translation import TranslationError, translate_text
from apps.rfq.models import QuoteRequest
from core.pagination import StandardPagination
from core.permissions import IsAdminRole, IsBuyerRole, IsSupplierRole
from core.responses import error_response, success_response

CHAT_TRANSLATE_CACHE_TTL = 3600


def _conversation_queryset_for_user(user):
    return (
        Conversation.objects.filter(Q(buyer=user) | Q(supplier=user))
        .select_related("quote_request", "buyer", "supplier", "supplier__factory_profile")
        .order_by("-last_message_at", "-id")
    )


def _get_participant_conversation(user, pk):
    return get_object_or_404(_conversation_queryset_for_user(user), pk=pk)


def _message_translate_response(request, conversation, message_id):
    message = get_object_or_404(Message, pk=message_id, conversation=conversation)
    text = (message.body or "").strip()
    if not text:
        return error_response("VALIDATION_ERROR", "消息内容为空", request=request)
    target_lang = request.data.get("target_lang", "")
    cache_key = f"chat:msg_tr:{message.id}:{str(target_lang or '').strip().lower()}"
    cached = cache.get(cache_key)
    if cached:
        return success_response({"translated_text": cached}, request=request)
    try:
        translated = translate_text(text, target_lang)
    except TranslationError as exc:
        status_code = 503 if exc.code == "TRANSLATE_NOT_CONFIGURED" else 400
        if exc.code == "TRANSLATE_FAILED":
            status_code = 502
        return error_response(exc.code, exc.message, status=status_code, request=request)
    if translated:
        cache.set(cache_key, translated, CHAT_TRANSLATE_CACHE_TTL)
    return success_response({"translated_text": translated}, request=request)


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
                body=ser.validated_data["body"],
            )
        except ValueError as exc:
            code = str(exc)
            return error_response(code or "VALIDATION_ERROR", "消息内容无效", request=request)
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
        qs = conversation.messages.select_related("sender").prefetch_related("attachments").order_by("-id")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
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
