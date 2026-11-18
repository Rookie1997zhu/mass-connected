"""工作台待办动作与未读聊天聚合（买家 / 供应商）。"""

from __future__ import annotations

from types import SimpleNamespace

ACTION_RFQ_STATUSES = ("quoted", "comparing", "customer_confirming", "negotiating")
PENDING_QUOTE_REQUEST_STATUSES = ("assigned", "viewed", "needs_revision", "pending")
ACTION_ITEMS_LIMIT = 10
UNREAD_CHATS_LIMIT = 5
UNREAD_SCAN_LIMIT = 40


def _item(kind, id_, title, subtitle, status, priority, href, *, cta="", meta=None):
    row = {
        "kind": kind,
        "id": id_,
        "title": title or "",
        "subtitle": subtitle or "",
        "status": status or "",
        "priority": priority,
        "href": href,
        "cta": cta or "",
    }
    if meta:
        row["meta"] = meta
    return row


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
                    f"/my/rfqs/{rfq.id}?tab=quotes",
                    cta="compare",
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.rfq.models import QuoteCounterOffer

        cos = (
            QuoteCounterOffer.objects.filter(
                rfq__buyer=user,
                status__in={"pending", "accepted"},
            )
            .select_related("rfq", "quote")
            .order_by("-created_at")[:ACTION_ITEMS_LIMIT]
        )
        for co in cos:
            kind = "counter_offer_pending" if co.status == "pending" else "counter_offer_accepted"
            cta = "withdraw" if co.status == "pending" else "await_revise"
            items.append(
                _item(
                    kind,
                    co.id,
                    f"CO-{co.id}",
                    f"{co.rfq.rfq_no} · {co.target_total_amount} {co.currency}",
                    co.status,
                    15 if co.status == "pending" else 16,
                    f"/my/rfqs/{co.rfq_id}?tab=quotes",
                    cta=cta,
                    meta={"rfq_id": co.rfq_id, "quote_id": co.quote_id},
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.payment.models import Payment

        unpaid = (
            Payment.objects.filter(buyer=user, status="unpaid")
            .select_related("contract", "contract__rfq")
            .order_by("-created_at")[:ACTION_ITEMS_LIMIT]
        )
        for pay in unpaid:
            rfq_id = getattr(getattr(pay, "contract", None), "rfq_id", None)
            href = f"/my/rfqs/{rfq_id}?tab=payment" if rfq_id else "/my?tab=payments"
            items.append(
                _item(
                    "payment_unpaid",
                    pay.id,
                    pay.payment_no or f"PAY-{pay.id}",
                    str(pay.amount),
                    pay.status,
                    20,
                    href,
                    cta="upload_proof",
                    meta={"rfq_id": rfq_id, "section": "payment"},
                )
            )
        pending = (
            Payment.objects.filter(buyer=user, status="pending_confirm")
            .select_related("contract", "contract__rfq")
            .order_by("-created_at")[:ACTION_ITEMS_LIMIT]
        )
        for pay in pending:
            rfq_id = getattr(getattr(pay, "contract", None), "rfq_id", None)
            href = f"/my/rfqs/{rfq_id}?tab=payment" if rfq_id else "/my?tab=payments"
            items.append(
                _item(
                    "payment_pending_confirm",
                    pay.id,
                    pay.payment_no or f"PAY-{pay.id}",
                    str(pay.amount),
                    pay.status,
                    30,
                    href,
                    cta="await_confirm",
                    meta={"rfq_id": rfq_id, "section": "payment"},
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
                    cta="sign",
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.contract.models import Contract

        contracts = (
            Contract.objects.filter(buyer=user, status="pending_sign")
            .select_related("rfq")
            .order_by("-created_at")[:ACTION_ITEMS_LIMIT]
        )
        for ct in contracts:
            href = f"/my/rfqs/{ct.rfq_id}?tab=contract" if ct.rfq_id else "/my?tab=contracts"
            items.append(
                _item(
                    "contract_pending_sign",
                    ct.id,
                    ct.contract_no or ct.title or f"CT-{ct.id}",
                    ct.title or "",
                    ct.status,
                    50,
                    href,
                    cta="sign",
                    meta={"rfq_id": ct.rfq_id, "section": "contract"},
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.project.models import ProjectTodo

        todos = (
            ProjectTodo.objects.filter(
                project__buyer=user, assignee_type="customer", is_done=False
            )
            .select_related("project")
            .order_by("due_date", "id")[:ACTION_ITEMS_LIMIT]
        )
        for todo in todos:
            prj = todo.project
            items.append(
                _item(
                    "project_todo",
                    todo.id,
                    todo.title,
                    (prj.project_no if prj else "") or "",
                    "open",
                    55,
                    f"/my/projects/{prj.id}" if prj else "/my?tab=projects",
                    cta="toggle_todo",
                    meta={"project_id": prj.id if prj else None},
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
            cta = "revise" if qr.status == "quoted" else "quote"
            items.append(
                _item(
                    "quote_request",
                    qr.id,
                    qr.request_no or f"QR-{qr.id}",
                    qr.status,
                    qr.status,
                    10,
                    f"/supplier/quote-requests/{qr.id}?tab=quotes",
                    cta=cta,
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.rfq.models import QuoteCounterOffer

        cos = (
            QuoteCounterOffer.objects.filter(
                quote__supplier=user,
                status="pending",
            )
            .select_related("rfq", "quote", "quote__quote_request")
            .order_by("-created_at")[:ACTION_ITEMS_LIMIT]
        )
        for co in cos:
            qr_id = getattr(co.quote, "quote_request_id", None)
            href = (
                f"/supplier/quote-requests/{qr_id}?tab=quotes"
                if qr_id
                else "/supplier/quote-requests"
            )
            items.append(
                _item(
                    "counter_offer_pending",
                    co.id,
                    f"CO-{co.id}",
                    f"{co.rfq.rfq_no} · {co.target_total_amount} {co.currency}",
                    co.status,
                    12,
                    href,
                    cta="respond_counter",
                    meta={
                        "quote_id": co.quote_id,
                        "quote_request_id": qr_id,
                        "rfq_id": co.rfq_id,
                    },
                )
            )
        accepted = (
            QuoteCounterOffer.objects.filter(
                quote__supplier=user,
                status="accepted",
            )
            .select_related("rfq", "quote")
            .order_by("-updated_at")[:ACTION_ITEMS_LIMIT]
        )
        for co in accepted:
            qr_id = getattr(co.quote, "quote_request_id", None)
            href = (
                f"/supplier/quote-requests/{qr_id}?tab=quotes"
                if qr_id
                else "/supplier/quote-requests"
            )
            items.append(
                _item(
                    "counter_offer_revise",
                    co.id,
                    f"CO-{co.id}",
                    f"{co.rfq.rfq_no} · revise quote",
                    co.status,
                    13,
                    href,
                    cta="revise",
                    meta={"quote_request_id": qr_id, "quote_id": co.quote_id},
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.rfq.models import ProductionOrder

        rows = (
            ProductionOrder.objects.filter(supplier=user, status="pending_confirm")
            .select_related("quote", "quote__quote_request", "rfq")
            .order_by("-created_at")[:ACTION_ITEMS_LIMIT]
        )
        for order in rows:
            qr_id = getattr(getattr(order, "quote", None), "quote_request_id", None)
            href = (
                f"/supplier/quote-requests/{qr_id}?tab=quotes"
                if qr_id
                else "/supplier/orders"
            )
            items.append(
                _item(
                    "production_order",
                    order.id,
                    order.order_no or f"PO-{order.id}",
                    order.status,
                    order.status,
                    20,
                    href,
                    cta="confirm_order",
                    meta={
                        "quote_request_id": qr_id,
                        "rfq_id": order.rfq_id,
                        "section": "order",
                    },
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.payment.models import Payment

        pays = (
            Payment.objects.filter(
                contract__production_order__supplier=user,
                status="pending_confirm",
            )
            .select_related("contract", "contract__rfq", "contract__production_order__quote")
            .order_by("-created_at")[:ACTION_ITEMS_LIMIT]
        )
        for pay in pays:
            quote = getattr(getattr(pay.contract, "production_order", None), "quote", None)
            qr_id = getattr(quote, "quote_request_id", None)
            href = (
                f"/supplier/quote-requests/{qr_id}?tab=payment"
                if qr_id
                else "/supplier/orders"
            )
            items.append(
                _item(
                    "payment_confirm",
                    pay.id,
                    pay.payment_no or f"PAY-{pay.id}",
                    str(pay.amount),
                    pay.status,
                    25,
                    href,
                    cta="confirm_payment",
                    meta={"quote_request_id": qr_id, "section": "payment"},
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
                    cta="view",
                )
            )
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.project.models import ProjectTodo

        todos = (
            ProjectTodo.objects.filter(
                project__supplier=user, assignee_type="supplier", is_done=False
            )
            .select_related("project")
            .order_by("due_date", "id")[:ACTION_ITEMS_LIMIT]
        )
        for todo in todos:
            prj = todo.project
            items.append(
                _item(
                    "project_todo",
                    todo.id,
                    todo.title,
                    (prj.project_no if prj else "") or "",
                    "open",
                    35,
                    f"/supplier/projects/{prj.id}" if prj else "/supplier/projects",
                    cta="toggle_todo",
                    meta={"project_id": prj.id if prj else None},
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
            .select_related(
                "quote_request",
                "quote_request__rfq",
                "buyer",
                "supplier",
                "supplier__factory_profile",
            )
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
