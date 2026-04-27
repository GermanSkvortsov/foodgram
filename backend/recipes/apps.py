"""
Конфигурация приложения recipes.
"""

from django.apps import AppConfig


class RecipesConfig(AppConfig):
    """Конфигурация приложения для управления рецептами и ингредиентами."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "recipes"
    verbose_name = "Рецепты и ингредиенты"
