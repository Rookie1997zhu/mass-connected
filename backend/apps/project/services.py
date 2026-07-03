from django.db import transaction

from apps.notification.services import notify
from apps.project.models import Project, ProjectStage

DEFAULT_STAGES = ["需求确认", "打样/开模", "批量生产", "质检", "交付"]


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
        amount=production_order.price_amount,
        currency=production_order.currency,
        status="in_progress",
    )
    for idx, name in enumerate(DEFAULT_STAGES):
        ProjectStage.objects.create(
            project=project,
            name=name,
            sort_order=idx,
            status="in_progress" if idx == 0 else "pending",
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
