from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import (
    AdminFactoryDetailView,
    AdminFactoryListView,
    AdminLoginView,
    AdminUserListCreateView,
    FactoryProfileView,
    FactoryRegisterView,
    LogoutView,
    MemberLoginView,
    MemberProfileView,
    MemberRegisterView,
)

urlpatterns = [
    path("member/auth/register", MemberRegisterView.as_view()),
    path("factory/auth/register", FactoryRegisterView.as_view()),
    path("member/auth/login", MemberLoginView.as_view()),
    path("member/auth/refresh", TokenRefreshView.as_view()),
    path("member/auth/logout", LogoutView.as_view()),
    path("member/profile", MemberProfileView.as_view()),
    path("factory/profile", FactoryProfileView.as_view()),
    path("admin/auth/login", AdminLoginView.as_view()),
    path("admin/auth/refresh", TokenRefreshView.as_view()),
    path("admin/auth/logout", LogoutView.as_view()),
    path("admin/admin-users", AdminUserListCreateView.as_view()),
    path("admin/factories", AdminFactoryListView.as_view()),
    path("admin/factories/<int:pk>", AdminFactoryDetailView.as_view()),
]
