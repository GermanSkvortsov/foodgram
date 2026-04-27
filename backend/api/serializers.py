"""
Сериализаторы для API.

Содержит сериализаторы пользователей, рецептов, тегов и ингредиентов.
"""

import base64
import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import Ingredient, IngredientAmount, Recipe, Tag
from users.models import User


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор профиля пользователя."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_subscribed",
            "avatar",
        )

    def get_is_subscribed(self, obj):
        """Проверяет, подписан ли текущий пользователь на автора."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return request.user.follower.filter(author=obj).exists()

    def get_avatar(self, obj):
        """Возвращает абсолютный URL аватара."""
        if obj and obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя."""

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password"
        )

    def create(self, validated_data):
        """Создаёт пользователя с хешированным паролем."""
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов внутри рецепта (чтение)."""

    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit")

    class Meta:
        model = IngredientAmount
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Упрощённый сериализатор для рецептов (подписки, избранное, корзина)."""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""

    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientAmountSerializer(
        source="ingredients_amounts", many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_is_favorited(self, obj):
        """Проверяет, в избранном ли рецепт у текущего пользователя."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.favorites.filter(user=request.user).exists()

    def get_is_in_shopping_cart(self, obj):
        """Проверяет, в корзине ли рецепт у текущего пользователя."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.shopping_cart.filter(user=request.user).exists()

    def get_image(self, obj):
        """Возвращает абсолютный URL изображения."""
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания и обновления рецептов.

    Принимает ID тегов и список ингредиентов с id и amount.
    """

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True)
    ingredients = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=True
    )
    image = serializers.CharField(required=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "ingredients",
            "image",
            "name",
            "text",
            "cooking_time"
        )

    def validate(self, data):
        """Валидация тегов и времени приготовления."""
        tags = data.get("tags", [])
        cooking_time = data.get("cooking_time")
        request = self.context.get("request")
        is_patch = request and request.method == "PATCH"
        initial_data = getattr(self, "initial_data", {})

        if is_patch and "ingredients" not in initial_data:
            raise serializers.ValidationError(
                {"ingredients": "Это поле обязательно при обновлении рецепта."}
            )
        if not tags:
            raise serializers.ValidationError(
                {"tags": "Укажите хотя бы один тег"})
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError({
                "tags": "Теги не должны повторяться"})
        if cooking_time is not None and cooking_time < 1:
            raise serializers.ValidationError(
                {"cooking_time": (
                    "Время приготовления должно быть не менее 1 минуты")}
            )
        return data

    def validate_ingredients(self, value):
        """Валидация списка ингредиентов."""
        if not value:
            raise serializers.ValidationError(
                "Добавьте хотя бы один ингредиент")

        ingredient_ids = [item.get("id") for item in value if item.get("id")]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                "Ингредиенты не должны повторяться")

        for item in value:
            if not item.get("id") or not item.get("amount"):
                raise serializers.ValidationError(
                    "У каждого ингредиента должны быть указаны id и amount"
                )
            if int(item.get("amount", 0)) <= 0:
                raise serializers.ValidationError(
                    "Количество ингредиента должно быть больше 0"
                )
        return value

    def _decode_base64_image(self, image_data):
        """Декодирует base64 строку в файл изображения."""
        try:
            format, imgstr = image_data.split(";base64,")
            ext = format.split("/")[-1]
            filename = f"{uuid.uuid4()}.{ext}"
            return ContentFile(base64.b64decode(imgstr), name=filename)
        except Exception:
            raise serializers.ValidationError(
                {"image": "Неверный формат изображения"})

    def _save_ingredients(self, recipe, ingredients_data):
        """Сохраняет ингредиенты для рецепта."""
        for ingredient_data in ingredients_data:
            try:
                Ingredient.objects.get(id=ingredient_data["id"])
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    {"ingredients": f'Ингредиент с id {ingredient_data["id"]} не существует'}  # noqa
                )
            IngredientAmount.objects.create(
                recipe=recipe,
                ingredient_id=ingredient_data["id"],
                amount=ingredient_data["amount"],
            )

    def create(self, validated_data):
        """Создаёт рецепт с тегами и ингредиентами."""
        tags = validated_data.pop("tags")
        ingredients_data = validated_data.pop("ingredients")
        image_data = validated_data.pop("image")
        image_file = self._decode_base64_image(image_data)

        recipe = Recipe.objects.create(image=image_file, **validated_data)
        recipe.tags.set(tags)
        self._save_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        """Обновляет рецепт."""
        tags = validated_data.pop("tags", None)
        ingredients_data = validated_data.pop("ingredients", None)
        image_data = validated_data.pop("image", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if image_data:
            instance.image = self._decode_base64_image(image_data)

        instance.save()

        if tags is not None:
            instance.tags.set(tags)

        if ingredients_data is not None:
            instance.ingredients_amounts.all().delete()
            self._save_ingredients(instance, ingredients_data)

        return instance


class UserWithRecipesSerializer(UserSerializer):
    """Сериализатор для подписок с рецептами пользователя."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("recipes", "recipes_count")

    def get_recipes(self, obj):
        """Возвращает рецепты пользователя с учётом recipes_limit."""
        request = self.context.get("request")
        limit = request.query_params.get("recipes_limit") if request else None
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[: int(limit)]
        return RecipeMinifiedSerializer(
            recipes, many=True, context=self.context).data

    def get_recipes_count(self, obj):
        """Возвращает количество рецептов пользователя."""
        return obj.recipes.count()
