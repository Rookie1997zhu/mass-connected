from django.urls import path

from apps.ops.views import OpsBehaviorView, OpsRuntimeView, OpsStorageView

urlpatterns = [
    path("admin/ops/runtime", OpsRuntimeView.as_view()),
    path("admin/ops/storage", OpsStorageView.as_view()),
    path("admin/ops/behavior", OpsBehaviorView.as_view()),
]
