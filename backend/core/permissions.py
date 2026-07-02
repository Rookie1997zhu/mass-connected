from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    message = "无管理权限"

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in {"super_admin", "operator", "sales"})


class IsMemberRole(BasePermission):
    message = "需要会员登录"

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "member" and user.is_active)


class IsFactoryRole(BasePermission):
    message = "需要工厂账号登录"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or user.role != "factory" or not user.is_active:
            return False
        profile = getattr(user, "factory_profile", None)
        return bool(profile and profile.status == "approved")


class IsMemberOrFactoryRole(BasePermission):
    message = "需要登录"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.role == "member":
            return True
        if user.role == "factory":
            profile = getattr(user, "factory_profile", None)
            return bool(profile and profile.status == "approved")
        return False
