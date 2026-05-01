"""
Модели приложения recipes.

Содержит модели Tag, Ingredient, Recipe, IngredientAmount,
Favorite и ShoppingCart.
"""

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from users.models import User


TAG_NAME_MAX_LEN = 32
TAG_SLUG_MAX_LEN = 32
INGREDIENT_NAME_MAX_LEN = 128
INGREDIENT_UNIT_MAX_LEN = 64
RECIPE_NAME_MAX_LEN = 256
SHORT_CODE_MAX_LEN = 8
MIN_COOKING_TIME = 1
MAX_COOKING_TIME = 32000
MIN_AMOUNT = 1
MAX_AMOUNT = 32000


class Tag(models.Model):
    """Модель тегов для рецептов."""

    name = models.CharField(
        max_length=TAG_NAME_MAX_LEN, unique=True, verbose_name="Название тега"
    )
    slug = models.SlugField(
        max_length=TAG_SLUG_MAX_LEN,
        unique=True,
        verbose_name="Уникальный слаг"
    )

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель ингредиентов."""

    name = models.CharField(
        max_length=INGREDIENT_NAME_MAX_LEN, verbose_name="Название ингредиента"
    )
    measurement_unit = models.CharField(
        max_length=INGREDIENT_UNIT_MAX_LEN, verbose_name="Единица измерения"
    )

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        constraints = (
            models.UniqueConstraint(
                fields=("name", "measurement_unit"), name="unique_ingredient"
            ),
        )

    def __str__(self):
        return f"{self.name}, {self.measurement_unit}"


class Recipe(models.Model):
    """Модель рецептов."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор"
    )
    name = models.CharField(
        max_length=RECIPE_NAME_MAX_LEN,
        verbose_name="Название рецепта"
    )
    image = models.ImageField(upload_to="recipes/", verbose_name="Картинка")
    text = models.TextField(verbose_name="Описание")
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name="Время приготовления (в минутах)",
        validators=[
            MinValueValidator(
                MIN_COOKING_TIME,
                message="Время приготовления не может быть меньше"
                f"{MIN_COOKING_TIME} минуты",
            ),
            MaxValueValidator(
                MAX_COOKING_TIME,
                message="Время приготовления не может быть больше"
                f"{MAX_COOKING_TIME} минут",
            ),
        ],
    )
    tags = models.ManyToManyField(
        Tag, related_name="recipes", verbose_name="Теги"
    )
    short_code = models.CharField(
        max_length=SHORT_CODE_MAX_LEN,
        unique=True,
        blank=True,
        verbose_name="Короткий код",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата создания"
    )

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        ordering = ("-created_at",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.short_code:
            self.short_code = self._generate_short_code()
            while Recipe.objects.filter(short_code=self.short_code).exists():
                self.short_code = self._generate_short_code()
        super().save(*args, **kwargs)

    def _generate_short_code(self):
        """Генерирует уникальный короткий код для ссылки."""
        return uuid.uuid4().hex[:SHORT_CODE_MAX_LEN]


class IngredientAmount(models.Model):
    """Связующая модель для рецептов и ингредиентов с количеством."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="ingredients_amounts",
        verbose_name="Рецепт",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="recipes_amounts",
        verbose_name="Ингредиент",
    )
    amount = models.PositiveIntegerField(
        verbose_name="Количество",
        validators=[
            MinValueValidator(
                MIN_AMOUNT,
                message=f"Количество не может быть меньше {MIN_AMOUNT}",
            ),
            MaxValueValidator(
                MAX_AMOUNT,
                message=f"Количество не может быть больше {MAX_AMOUNT}",
            ),
        ],
    )

    class Meta:
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецепте"
        constraints = (
            models.UniqueConstraint(
                fields=("recipe", "ingredient"),
                name="unique_recipe_ingredient"
            ),
        )

    def __str__(self):
        return f"{self.ingredient.name} в {self.recipe.name}: {self.amount}"


class Favorite(models.Model):
    """Модель избранного (связь пользователь-рецепт)."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Рецепт",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата добавления"
    )

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        constraints = (
            models.UniqueConstraint(
                fields=("user", "recipe"), name="unique_favorite"
            ),
        )

    def __str__(self):
        return f"{self.user} добавил {self.recipe} в избранное"


class ShoppingCart(models.Model):
    """Модель корзины покупок (связь пользователь-рецепт)."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
        verbose_name="Рецепт",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата добавления"
    )

    class Meta:
        verbose_name = "Корзина покупок"
        verbose_name_plural = "Корзина покупок"
        constraints = (
            models.UniqueConstraint(
                fields=("user", "recipe"), name="unique_shopping_cart"
            ),
        )

    def __str__(self):
        return f"{self.user} добавил {self.recipe} в корзину"
