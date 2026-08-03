"""工作台待办动作与未读聊天聚合（买家 / 供应商）。"""

from __future__ import annotations

from types import SimpleNamespace

ACTION_RFQ_STATUSES = ("quoted", "comparing", "customer_confirming", "negotiating")
PENDING_QUOTE_REQUEST_STATUSES = ("assigned", "viewed", "needs_revision")
ACTION_ITEMS_LIMIT = 8
UNREAD_CHATS_LIMIT = 5
UNREAD_SCAN_LIMIT = 40


def _item(kind, id_, title, subtitle, status, priority, href):
    return {
        "kind": kind,
        "id": id_,
        "title": title or "",
        "subtitle": subtitle or "",
        "status": status or "",
        "priority": priority,
        "href": href,
    }


def build_buyer_action_items(user) -> list[dict]:
    items: list[dict] = []

    try:
        from apps.rfq.models import RFQ

        rows = (
            RFQ.objects.filter(buyer=user, status__in=ACTION_RFQ_STATUSES)
            .select_related("service_category")
            .order_by("-updated_at")[:ACTION_ITEMS_LIMIT]
        )
        for rfq in rows:
            cat = getattr(rfq, "service_category", None)
            subtitle = ""
            if cat is not None:
                name = getattr(cat, "name", None)
                if isinstance(name, dict):
                    subtitle = name.get("zh") or name.get("ko") or name.get("en") or ""
                elif name:
                    subtitle = str(name)
            items.append(
                _item(
                    "rfq_action",
                    rfq.id,
                    rfq.rfq_no or f"RFQ-{rfq.id}",
                    subtitle or rfq.status,
                    rfq.status,
                    10,
                    f"/my/rfqs/{rfq.id}",
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.payment.models import Payment

        unpaid = Payment.objects.filter(buyer=user, status="unpaid").order_by("-created_at")[:ACTION_ITEMS_LIMIT]
        for pay in unpaid:
            items.append(
                _item(
                    "payment_unpaid",
                    pay.id,
                    pay.payment_no or f"PAY-{pay.id}",
                    str(pay.amount),
                    pay.status,
                    20,
                    "/my?tab=payments",
                )
            )
        pending = Payment.objects.filter(buyer=user, status="pending_confirm").order_by("-created_at")[
            :ACTION_ITEMS_LIMIT
        ]
        for pay in pending:
            items.append(
                _item(
                    "payment_pending_confirm",
                    pay.id,
                    pay.payment_no or f"PAY-{pay.id}",
                    str(pay.amount),
                    pay.status,
                    30,
                    "/my?tab=payments",
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.contract.models import NdaSignature

        ndas = NdaSignature.objects.filter(buyer=user, status="pending").order_by("-created_at")[
            :ACTION_ITEMS_LIMIT
        ]
        for nda in ndas:
            items.append(
                _item(
                    "nda_pending",
                    nda.id,
                    nda.company_name or f"NDA-{nda.id}",
                    "",
                    nda.status,
                    40,
                    "/my/nda",
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.contract.models import Contract

        contracts = Contract.objects.filter(buyer=user, status="pending_sign").order_by("-created_at")[
            :ACTION_ITEMS_LIMIT
        ]
        for ct in contracts:
            items.append(
                _item(
                    "contract_pending_sign",
                    ct.id,
                    ct.contract_no or ct.title or f"CT-{ct.id}",
                    ct.title or "",
                    ct.status,
                    50,
                    "/my?tab=contracts",
                )
            )
    except Exception:  # noqa: BLE001
        pass

    items.sort(key=lambda x: (x["priority"], -int(x["id"] or 0)))
    return items[:ACTION_ITEMS_LIMIT]


def build_supplier_action_items(user) -> list[dict]:
    items: list[dict] = []

    try:
        from apps.rfq.models import QuoteRequest

        rows = (
            QuoteRequest.objects.filter(supplier=user, status__in=PENDING_QUOTE_REQUEST_STATUSES)
            .select_related("rfq")
            .order_by("-updated_at")[:ACTION_ITEMS_LIMIT]
        )
        for qr in rows:
            items.append(
                _item(
                    "quote_request",
                    qr.id,
                    qr.request_no or f"QR-{qr.id}",
                    qr.status,
                    qr.status,
                    10,
                    f"/supplier/quote-requests/{qr.id}",
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.rfq.models import ProductionOrder

        rows = ProductionOrder.objects.filter(supplier=user, status="pending_confirm").order_by(
            "-created_at"
        )[:ACTION_ITEMS_LIMIT]
        for order in rows:
            items.append(
                _item(
                    "production_order",
                    order.id,
                    order.order_no or f"PO-{order.id}",
                    order.status,
                    order.status,
                    20,
                    "/supplier/orders",
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.project.models import ProjectIssue

        issues = (
            ProjectIssue.objects.filter(project__supplier=user, status="open")
            .select_related("project")
            .order_by("-created_at")[:ACTION_ITEMS_LIMIT]
        )
        for issue in issues:
            prj = issue.project
            items.append(
                _item(
                    "project_issue",
                    issue.id,
                    issue.title or f"ISSUE-{issue.id}",
                    (prj.project_no if prj else "") or "",
                    issue.status,
                    30,
                    f"/supplier/projects/{prj.id}" if prj else "/supplier/projects",
                )
            )
    except Exception:  # noqa: BLE001
        pass

    items.sort(key=lambda x: (x["priority"], -int(x["id"] or 0)))
    return items[:ACTION_ITEMS_LIMIT]


def build_unread_chats(user) -> list[dict]:
    try:
        from django.db.models import Q

        from apps.chat.models import Conversation
        from apps.chat.serializers import ConversationSerializer

        qs = (
            Conversation.objects.filter(Q(buyer=user) | Q(supplier=user))
            .select_related("quote_request", "buyer", "supplier", "supplier__factory_profile")
            .order_by("-last_message_at", "-id")[:UNREAD_SCAN_LIMIT]
        )
        request = SimpleNamespace(user=user)
        rows = ConversationSerializer(qs, many=True, context={"request": request}).data
        out = []
        for row in rows:
            unread = int(row.get("unread") or 0)
            if unread <= 0:
                continue
            title = (
                row.get("peer_display_name")
                or row.get("quote_request_no")
                or f"Chat#{row.get('id')}"
            )
            last_at = row.get("last_message_at")
            if hasattr(last_at, "isoformat"):
                last_at = last_at.isoformat()
            out.append(
                {
                    "conversation_id": row.get("id"),
                    "quote_request_id": row.get("quote_request_id"),
                    "title": title,
                    "preview": row.get("last_message_preview") or "",
                    "unread": unread,
                    "last_message_at": last_at or "",
                }
            )
            if len(out) >= UNREAD_CHATS_LIMIT:
                break
        return out
    except Exception:  # noqa: BLE001
        return []
