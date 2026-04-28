"""
Административная панель для приложения recipes.

Регистрирует модели Tag, Ingredient, Recipe, Favorite, ShoppingCart.
"""

from django.contrib import admin

from .models import (
    Favorite,
    Ingredient,
    IngredientAmount,
    Recipe,
    ShoppingCart,
    Tag
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Настройка отображения тегов в админке."""

    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Настройка отображения ингредиентов в админке."""

    list_display = ("id", "name", "measurement_unit")
    search_fields = ("name",)
    list_filter = ("measurement_unit",)


class IngredientAmountInline(admin.TabularInline):
    """Inline-форма для редактирования ингредиентов внутри рецепта."""

    model = IngredientAmount
    extra = 1
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Настройка отображения рецептов в админке."""

    list_display = ("id", "name", "author", "cooking_time", "created_at")
    list_filter = ("tags", "author", "created_at")
    search_fields = ("name", "author__username", "tags__name")
    inlines = [IngredientAmountInline]
    readonly_fields = ("created_at", "favorite_count")

    def favorite_count(self, obj):
        """Возвращает число добавлений рецепта в избранное."""
        return obj.favorites.count()
    favorite_count.short_description = "Число добавлений в избранное"


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Настройка отображения избранного в админке."""

    list_display = ("id", "user", "recipe", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "recipe__name")


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    """Настройка отображения корзины покупок в админке."""

    list_display = ("id", "user", "recipe", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "recipe__name")
