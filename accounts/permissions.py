from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminRole(BasePermission):
    message = "Only administrators can do this."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_role)


class IsApprovedAgent(BasePermission):
    message = "Only approved agents can do this."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_approved_agent)


class IsApprovedAgentOrAdmin(BasePermission):
    message = "Only approved agents or administrators can do this."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_admin_role or u.is_approved_agent))


class IsOwnerOrAdmin(BasePermission):
    """Object-level: only the creator of an object (or an admin) may change it."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner = getattr(obj, "created_by", None)
        return request.user.is_admin_role or owner == request.user
