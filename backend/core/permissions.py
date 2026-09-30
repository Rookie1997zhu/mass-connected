from rest_framework import status
from rest_framework.exceptions import APIException
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


class IsSuperAdmin(BasePermission):
    message = "无超级管理员权限"

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "super_admin")


class IsBuyerRole(BasePermission):
    message = "需要会员登录"

    def has_permission(self, request, view):
        user = request.user
        allowed = _is_active_member(user)
        # 已登录但非买家：避免误报「需要会员登录」
        if (
            not allowed
            and user
            and getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) == "factory"
        ):
            self.message = "该功能仅限买家会员使用，当前为企业账号"
        elif not allowed:
            self.message = "需要会员登录"
        return allowed


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


class EmailNotVerifiedError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "EMAIL_NOT_VERIFIED"
    default_detail = "请先验证邮箱后再进行此操作"


class IsEmailVerified(BasePermission):
    message = "请先验证邮箱后再进行此操作"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return True
        if getattr(user, "is_verified", True):
            return True
        raise EmailNotVerifiedError()


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
