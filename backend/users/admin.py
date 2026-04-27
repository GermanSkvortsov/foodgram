"""
Административная панель для приложения users.

Регистрирует кастомную модель User и модель Follow.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from .models import Follow, User


class UserAdmin(BaseUserAdmin):
    """Настройка отображения кастомной модели пользователя в админке."""

    list_display = (
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "avatar"
    )
    search_fields = ("username", "email")
    list_filter = ("is_staff", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (  # type: ignore
        ("Дополнительно", {"fields": ("avatar",)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Дополнительно", {"fields": ("avatar",)}),
    )


admin.site.register(User, UserAdmin)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Настройка отображения подписок в админке."""

    list_display = ("id", "user", "author", "created_at")
    search_fields = ("user__username", "author__username")
    list_filter = ("created_at",)


admin.site.unregister(Group)
