"""
Custom permissions for role-based access control
"""
from rest_framework import permissions


class IsStaff(permissions.BasePermission):
    """Allow access only to staff users"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff_role()


class IsApprover(permissions.BasePermission):
    """Allow access only to approvers"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.can_approve()


class IsFinance(permissions.BasePermission):
    """Allow access only to finance team"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_finance()


class IsStaffOrFinance(permissions.BasePermission):
    """Allow access to staff or finance"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_staff_role() or request.user.is_finance()
        )


class IsOwnerOrApprover(permissions.BasePermission):
    """Allow access to owner or approvers"""
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'created_by'):
            return (
                obj.created_by == request.user or
                request.user.can_approve() or
                request.user.is_finance()
            )
        return False

