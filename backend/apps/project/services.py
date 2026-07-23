from django.db import transaction
from django.utils import timezone

from apps.notification.services import notify
from apps.project.models import Project, ProjectStage

# 新项目默认制作流程；存量项目不回填覆盖
DEFAULT_STAGES = ["订单", "采购", "生产", "出库", "物流"]


def get_current_stage(project):
    stages = list(project.stages.all())
    for stage in stages:
        if stage.status == "in_progress":
            return stage
    for stage in stages:
        if stage.status == "pending":
            return stage
    return stages[-1] if stages else None


def advance_next_stage(project, completed_stage):
    """完成后自动将下一 pending 阶段置为 in_progress。"""
    from django.utils import timezone

    next_stage = (
        project.stages.filter(sort_order__gt=completed_stage.sort_order, status="pending")
        .order_by("sort_order", "id")
        .first()
    )
    if next_stage:
        next_stage.status = "in_progress"
        if not next_stage.started_at:
            next_stage.started_at = timezone.now()
        next_stage.save(update_fields=["status", "started_at"])


def recalc_progress(project):
    stages = list(project.stages.all())
    if not stages:
        return
    completed = sum(1 for s in stages if s.status == "completed")
    project.progress_percent = round(completed * 100 / len(stages))
    if project.progress_percent >= 100:
        project.status = "completed"
    elif project.progress_percent > 0 and project.status == "pending":
        project.status = "in_progress"
    project.save(update_fields=["progress_percent", "status", "updated_at"])


@transaction.atomic
def create_project_from_production_order(production_order, title=None):
    if Project.objects.filter(production_order=production_order).exists():
        return Project.objects.get(production_order=production_order)
    rfq = production_order.rfq
    project = Project.objects.create(
        project_no=Project.generate_no(),
        title=title or f"项目 {rfq.rfq_no}",
        rfq=rfq,
        production_order=production_order,
        buyer=production_order.buyer,
        supplier=production_order.supplier,
        amount=production_order.display_customer_amount(),
        currency=production_order.currency,
        status="in_progress",
    )
    for idx, name in enumerate(DEFAULT_STAGES):
        ProjectStage.objects.create(
            project=project,
            name=name,
            sort_order=idx,
            status="in_progress" if idx == 0 else "pending",
            started_at=timezone.now() if idx == 0 else None,
        )
    quote_request_id = None
    if production_order.quote_id:
        quote_request_id = getattr(production_order.quote, "quote_request_id", None)
        if quote_request_id is None:
            from apps.rfq.models import Quote

            quote_request_id = (
                Quote.objects.filter(pk=production_order.quote_id)
                .values_list("quote_request_id", flat=True)
                .first()
            )
    if quote_request_id:
        from apps.chat.services import link_conversation_to_order

        link_conversation_to_order(
            quote_request_id,
            production_order=production_order,
            project=project,
        )
    notify(
        project.buyer,
        "project",
        "项目已启动",
        f"项目 {project.project_no} 已创建，可在 MY PAGE 查看生产进度。",
        related_type="project",
        related_id=project.id,
    )
    if project.supplier:
        notify(
            project.supplier,
            "project",
            "新项目已分配",
            f"项目 {project.project_no} 已分配给您，请及时更新进度。",
            related_type="project",
            related_id=project.id,
        )
    return project
