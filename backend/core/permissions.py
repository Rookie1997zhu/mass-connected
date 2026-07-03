from rest_framework.permissions import BasePermission


def _is_active_member(user):
    return bool(user and user.is_authenticated and user.role == "member" and user.is_active)


def _has_approved_supplier_profile(user):
    profile = getattr(user, "factory_profile", None)
    return bool(profile and profile.status == "approved")


class IsAdminRole(BasePermission):
    message = "无管理权限"

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in {"super_admin", "operator", "sales"})


class IsBuyerRole(BasePermission):
    message = "需要会员登录"

    def has_permission(self, request, view):
        return _is_active_member(request.user)


class IsMemberRole(IsBuyerRole):
    """Alias for buyer-facing member APIs."""


class IsSupplierRole(BasePermission):
    message = "需要已审核的企业会员"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.role == "factory":
            return _has_approved_supplier_profile(user)
        if user.role == "member" and user.member_type == "enterprise":
            return _has_approved_supplier_profile(user)
        return False


class IsFactoryRole(IsSupplierRole):
    """Legacy alias."""


class IsMemberOrFactoryRole(BasePermission):
    message = "需要登录"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.role == "member":
            return True
        if user.role == "factory":
            return _has_approved_supplier_profile(user)
        return False
