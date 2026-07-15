"""按 RFQ / 报价请求聚合履约信息（合同、付款、项目、文件）。"""

from apps.contract.serializers import ContractSerializer
from apps.payment.models import Payment
from apps.project.models import Project
from apps.project.serializers import ProjectDetailSerializer, ProjectFileSerializer
from apps.rfq.models import ProductionOrder
from apps.rfq.serializers import (
    ProductionOrderSerializer,
    QuoteAttachmentSerializer,
    RFQAttachmentSerializer,
    SupplierPaymentSummarySerializer,
)


def _serialize_contract(contract, request, *, viewer_is_supplier=False, production_order=None):
    if not contract:
        return None
    data = ContractSerializer(contract, context={"request": request}).data
    if viewer_is_supplier and production_order is not None:
        data = {**data, "amount": production_order.display_supplier_amount()}
    return data


def _serialize_payment(payment, request, *, viewer_is_supplier=False, production_order=None):
    if not payment:
        return None
    if viewer_is_supplier:
        return SupplierPaymentSummarySerializer(
            payment,
            context={"request": request, "production_order": production_order},
        ).data
    from apps.payment.serializers import PaymentSerializer

    return PaymentSerializer(payment, context={"request": request}).data


def _load_project(project):
    if not project:
        return None
    return (
        Project.objects.prefetch_related(
            "stages",
            "updates",
            "todos",
            "issues",
            "files__stage",
            "files__uploader",
        )
        .select_related("rfq", "production_order", "supplier")
        .get(pk=project.pk)
    )


def _serialize_project(project, request, *, customer_only=False):
    if not project:
        return None
    ctx = {"request": request, "customer_only": customer_only}
    return ProjectDetailSerializer(project, context=ctx).data


def _collect_files(rfq, quote, project, request, *, customer_only=False):
    files = []
    for att in rfq.attachments.all():
        item = RFQAttachmentSerializer(att, context={"request": request}).data
        ext = (item.get("file_type") or "").lower()
        files.append(
            {
                "id": f"rfq-{att.id}",
                "source": "rfq",
                "source_label": "rfq",
                "file_name": item.get("file_name"),
                "file_url": item.get("url") or "",
                "file_ext": ext,
                "is_previewable": ext
                in {"pdf", "jpg", "jpeg", "png", "gif", "webp", "xlsx", "xls", "csv"},
                "stage_name": None,
                "file_category": "rfq",
                "created_at": item.get("uploaded_at"),
            }
        )
    if quote is not None:
        for att in quote.attachments.all():
            item = QuoteAttachmentSerializer(att, context={"request": request}).data
            files.append(
                {
                    "id": f"quote-{att.id}",
                    "source": "quote",
                    "source_label": "quote",
                    "file_name": item.get("file_name"),
                    "file_url": item.get("file_url") or "",
                    "file_ext": item.get("file_ext") or "",
                    "is_previewable": bool(item.get("is_previewable")),
                    "stage_name": None,
                    "file_category": "quote",
                    "created_at": item.get("uploaded_at"),
                }
            )
    if project is not None:
        qs = list(project.files.select_related("stage", "uploader").all())
        if customer_only:
            qs = [f for f in qs if f.visibility == "all"]
        for pf in qs:
            item = ProjectFileSerializer(pf, context={"request": request}).data
            files.append(
                {
                    "id": f"project-{pf.id}",
                    "source": "project",
                    "source_label": "project",
                    "file_name": item.get("file_name"),
                    "file_url": item.get("file_url") or "",
                    "file_ext": item.get("file_ext") or "",
                    "is_previewable": bool(item.get("is_previewable")),
                    "stage_name": item.get("stage_name"),
                    "file_category": item.get("file_category"),
                    "created_at": item.get("created_at"),
                }
            )
    files.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return files


def build_buyer_fulfillment(rfq, request):
    """买家：按 RFQ 聚合已确认方案后的履约信息。"""
    order = (
        rfq.production_orders.select_related("quote", "quote__quote_request", "supplier", "buyer")
        .prefetch_related("quote__attachments")
        .order_by("-created_at")
        .first()
    )
    contract = None
    payment = None
    project = None
    quote = None
    if order:
        quote = order.quote
        contract = getattr(order, "contract", None)
        if contract:
            payment = contract.payments.filter(buyer=request.user).order_by("-created_at").first()
        project = _load_project(getattr(order, "project", None))

    ctx = {"request": request}
    return {
        "rfq_id": rfq.id,
        "rfq_no": rfq.rfq_no,
        "rfq_status": rfq.status,
        "production_order": (
            ProductionOrderSerializer(order, context=ctx).data if order else None
        ),
        "contract": _serialize_contract(contract, request),
        "payment": _serialize_payment(payment, request),
        "project": _serialize_project(project, request, customer_only=True),
        "files": _collect_files(rfq, quote, project, request, customer_only=True),
    }


def build_supplier_fulfillment(quote_request, request):
    """供应商：按报价请求聚合履约信息（含付款凭证，不含内部备注）。"""
    rfq = quote_request.rfq
    quote = (
        quote_request.quotes.filter(supplier=request.user)
        .prefetch_related("attachments")
        .first()
    )
    order = None
    if quote is not None:
        order = (
            ProductionOrder.objects.filter(quote=quote, supplier=request.user)
            .select_related("quote", "quote__quote_request", "supplier", "buyer")
            .first()
        )

    contract = None
    payment = None
    project = None
    if order:
        contract = getattr(order, "contract", None)
        if contract:
            payment = Payment.objects.filter(contract=contract).order_by("-created_at").first()
        project = _load_project(getattr(order, "project", None))

    ctx = {"request": request}
    return {
        "quote_request_id": quote_request.id,
        "request_no": quote_request.request_no,
        "rfq_id": rfq.id,
        "rfq_no": rfq.rfq_no,
        "rfq_status": rfq.status,
        "quote_request_status": quote_request.status,
        "production_order": (
            ProductionOrderSerializer(order, context=ctx).data if order else None
        ),
        "contract": _serialize_contract(
            contract, request, viewer_is_supplier=True, production_order=order
        ),
        "payment": _serialize_payment(
            payment, request, viewer_is_supplier=True, production_order=order
        ),
        "project": _serialize_project(project, request, customer_only=False),
        "files": _collect_files(rfq, quote, project, request, customer_only=False),
    }
