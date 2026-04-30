"""
Сериализаторы для API.

Содержит сериализаторы пользователей, рецептов, тегов и ингредиентов.
"""

from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (
    Favorite,
    Ingredient,
    IngredientAmount,
    Recipe,
    ShoppingCart,
    Tag,
)
from users.models import Follow, User


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
        return bool(
            request
            and request.user.is_authenticated
            and request.user.follower.filter(author=obj).exists()
        )

    def get_avatar(self, obj):
        """Возвращает абсолютный URL аватара."""
        if obj and obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
        return None


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов внутри рецепта (чтение)."""

    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

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
        return bool(
            request
            and request.user.is_authenticated
            and obj.favorites.filter(user=request.user).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """Проверяет, в корзине ли рецепт у текущего пользователя."""
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and obj.shopping_cart.filter(user=request.user).exists()
        )

    def get_image(self, obj):
        """Возвращает абсолютный URL изображения."""
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class IngredientCreateSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиента при создании/обновлении рецепта."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source="ingredient"
    )

    class Meta:
        model = IngredientAmount
        fields = ("id", "amount")


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания и обновления рецептов.

    Принимает ID тегов и список ингредиентов с id и amount.
    """

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    ingredients = IngredientCreateSerializer(
        many=True, write_only=True, required=True
    )
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "ingredients",
            "image",
            "name",
            "text",
            "cooking_time",
        )

    def validate(self, data):
        """Валидация тегов, ингредиентов и изображения."""
        tags = data.get("tags", [])
        ingredients = data.get("ingredients", [])
        image = data.get("image")

        if not image:
            raise serializers.ValidationError(
                {"image": "Изображение обязательно"}
            )

        if not tags:
            raise serializers.ValidationError(
                {"tags": "Укажите хотя бы один тег"}
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {"tags": "Теги не должны повторяться"}
            )

        if not ingredients:
            raise serializers.ValidationError(
                {"ingredients": "Добавьте хотя бы один ингредиент"}
            )

        ingredient_ids = [item["ingredient"].id for item in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {"ingredients": "Ингредиенты не должны повторяться"}
            )

        return data

    def _save_ingredients(self, recipe, ingredients_data):
        """Сохраняет ингредиенты для рецепта через bulk_create."""
        ingredient_amounts = [
            IngredientAmount(
                recipe=recipe,
                ingredient=item["ingredient"],
                amount=item["amount"],
            )
            for item in ingredients_data
        ]
        IngredientAmount.objects.bulk_create(ingredient_amounts)

    def create(self, validated_data):
        """Создаёт рецепт с тегами и ингредиентами."""
        tags = validated_data.pop("tags")
        ingredients_data = validated_data.pop("ingredients")
        validated_data["author"] = self.context["request"].user
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self._save_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        """Обновляет рецепт."""
        tags = validated_data.pop("tags", None)
        ingredients_data = validated_data.pop("ingredients", None)

        instance = super().update(instance, validated_data)

        if tags is not None:
            instance.tags.set(tags)
        if ingredients_data is not None:
            instance.ingredients_amounts.all().delete()
            self._save_ingredients(instance, ingredients_data)

        return instance

    def to_representation(self, instance):
        """Возвращает полные данные рецепта после создания/обновления."""
        return RecipeSerializer(instance, context=self.context).data


class FollowCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания подписки."""

    class Meta:
        model = Follow
        fields = ("user", "author")

    def validate(self, data):
        if data["user"] == data["author"]:
            raise serializers.ValidationError(
                {"error": "Нельзя подписаться на самого себя"}
            )
        if Follow.objects.filter(
            user=data["user"], author=data["author"]
        ).exists():
            raise serializers.ValidationError(
                {"error": "Вы уже подписаны на этого автора"}
            )
        return data

    def to_representation(self, instance):
        return UserWithRecipesSerializer(
            instance.author, context=self.context
        ).data


class FavoriteCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления в избранное."""

    class Meta:
        model = Favorite
        fields = ("user", "recipe")

    def validate(self, data):
        if Favorite.objects.filter(
            user=data["user"], recipe=data["recipe"]
        ).exists():
            raise serializers.ValidationError(
                {"error": "Рецепт уже в избранном"}
            )
        return data

    def to_representation(self, instance):
        return RecipeMinifiedSerializer(
            instance.recipe, context=self.context
        ).data


class ShoppingCartCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления в корзину покупок."""

    class Meta:
        model = ShoppingCart
        fields = ("user", "recipe")

    def validate(self, data):
        if ShoppingCart.objects.filter(
            user=data["user"], recipe=data["recipe"]
        ).exists():
            raise serializers.ValidationError(
                {"error": "Рецепт уже в корзине"}
            )
        return data

    def to_representation(self, instance):
        return RecipeMinifiedSerializer(
            instance.recipe, context=self.context
        ).data


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
            try:
                limit = int(limit)
                if limit > 0:
                    recipes = recipes[:limit]
            except (ValueError, TypeError):
                pass
        return RecipeMinifiedSerializer(
            recipes, many=True, context=self.context
        ).data

    def get_recipes_count(self, obj):
        """Возвращает количество рецептов пользователя."""
        return obj.recipes.count()
