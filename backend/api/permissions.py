"""
Права доступа для API.
"""

from rest_framework.permissions import BasePermission


class IsAuthorOrReadOnly(BasePermission):
    """Разрешает редактирование/удаление только автору объекта."""

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return obj.author == request.user
