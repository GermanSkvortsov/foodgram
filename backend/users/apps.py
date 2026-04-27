"""
Конфигурация приложения users.
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Конфигурация приложения для управления пользователями и подписками."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = "Пользователи и подписки"
