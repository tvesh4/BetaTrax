from rest_framework import permissions

class IsUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='User').exists()

class IsDeveloper(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Developer').exists()

class IsOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Owner').exists()