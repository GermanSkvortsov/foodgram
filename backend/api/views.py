"""
Views для API.

Содержит ViewSet для тегов, ингредиентов, подписок и рецептов.
"""

import base64
import uuid

from django.core.files.base import ContentFile
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from recipes.models import Ingredient, Recipe, Tag
from users.models import User

from .serializers import (
    IngredientSerializer,
    RecipeCreateUpdateSerializer,
    RecipeMinifiedSerializer,
    RecipeSerializer,
    TagSerializer,
    UserSerializer,
    UserWithRecipesSerializer,
)
from .utils import decode_code, encode_id, is_valid_code


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для тегов (только чтение)."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для ингредиентов (только чтение)."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("name",)
    pagination_class = None


class SubscriptionViewSet(viewsets.GenericViewSet):
    """ViewSet для подписок и аватара пользователя."""

    queryset = User.objects.all()
    permission_classes = (IsAuthenticated,)

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """Возвращает данные текущего пользователя."""
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["put", "delete"], url_path="me/avatar")
    def avatar(self, request):
        """Добавляет или удаляет аватар текущего пользователя."""
        if request.method == "PUT":
            avatar_data = request.data.get("avatar")
            if not avatar_data:
                return Response(
                    {"avatar": "Это поле обязательно."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                format, imgstr = avatar_data.split(";base64,")
                ext = format.split("/")[-1]
                filename = f"{uuid.uuid4()}.{ext}"
                data = ContentFile(base64.b64decode(imgstr), name=filename)
                request.user.avatar.save(filename, data, save=True)
            except Exception:
                return Response(
                    {"avatar": "Неверный формат изображения"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {"avatar": request.build_absolute_uri(
                    request.user.avatar.url)},
                status=status.HTTP_200_OK,
            )
        elif request.method == "DELETE":
            if request.user.avatar:
                request.user.avatar.delete()
                request.user.avatar = None
                request.user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post", "delete"], url_path="subscribe")
    def subscribe(self, request, pk=None):
        """Подписывает или отписывает текущего пользователя от автора."""
        author = self.get_object()
        user = request.user

        if user == author:
            return Response(
                {"error": "Нельзя подписаться на самого себя"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.method == "POST":
            if user.follower.filter(author=author).exists():
                return Response(
                    {"error": "Вы уже подписаны на этого автора"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.follower.create(author=author)
            serializer = UserWithRecipesSerializer(
                author, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            subscription = user.follower.filter(author=author)
            if not subscription.exists():
                return Response(
                    {"error": "Вы не подписаны на этого автора"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="subscriptions")
    def subscriptions(self, request):
        """Возвращает список авторов, на которых подписан пользователь."""
        user = request.user
        authors = User.objects.filter(following__user=user)

        page = self.paginate_queryset(authors)
        if page is not None:
            serializer = UserWithRecipesSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = UserWithRecipesSerializer(
            authors, many=True, context={"request": request}
        )
        return Response(serializer.data)


class BaseRecipeRelationMixin:
    """Миксин для работы с избранным и корзиной покупок."""

    def _toggle_relation(self, request, pk, relation_name, error_messages):
        """
        Универсальный метод для добавления/удаления рецепта из отношения.

        relation_name: имя related_name в модели User
        ('favorites' или 'shopping_cart')
        error_messages: словарь с сообщениями для ошибок
        """
        recipe = self.get_object()  # type: ignore
        user = request.user
        relation = getattr(user, relation_name)

        if request.method == "POST":
            if relation.filter(recipe=recipe).exists():
                return Response(
                    {"error": error_messages["already_exists"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            relation.create(recipe=recipe)
            serializer = RecipeMinifiedSerializer(
                recipe, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == "DELETE":
            relation_item = relation.filter(recipe=recipe)
            if not relation_item.exists():
                return Response(
                    {"error": error_messages["not_exists"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            relation_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(BaseRecipeRelationMixin, viewsets.ModelViewSet):
    """ViewSet для рецептов (полный CRUD)."""

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ("name",)

    def get_serializer_class(self):
        """Возвращает нужный сериализатор в зависимости от действия."""
        if self.action in ("create", "update", "partial_update"):
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    def get_queryset(self):
        """
        Фильтрует queryset по тегам (OR-логика), автору,
        избранному и корзине покупок.
        """
        queryset = super().get_queryset()
        user = self.request.user

        # Фильтрация по тегам с OR-логикой (через __in)
        tags = self.request.query_params.getlist("tags")
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()

        # Фильтрация по автору
        author = self.request.query_params.get("author")
        if author:
            queryset = queryset.filter(author_id=author)

        if not user.is_authenticated:
            return queryset

        is_favorited = self.request.query_params.get("is_favorited")
        is_in_shopping_cart = self.request.query_params.get(
            "is_in_shopping_cart")

        if is_favorited == "1":
            queryset = queryset.filter(favorites__user=user)
        if is_in_shopping_cart == "1":
            queryset = queryset.filter(shopping_cart__user=user)

        return queryset

    def create(self, request, *args, **kwargs):
        """Создаёт новый рецепт и возвращает полные данные."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = RecipeSerializer(
            serializer.instance, context={"request": request}
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Обновляет рецепт с проверкой прав и возвращает полные данные."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        if instance.author != request.user:
            raise PermissionDenied("Вы не можете редактировать чужой рецепт")

        serializer = self.get_serializer(
            instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        read_serializer = RecipeSerializer(
            serializer.instance, context={"request": request}
        )
        return Response(read_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Удаляет рецепт с проверкой прав."""
        instance = self.get_object()
        if instance.author != request.user:
            raise PermissionDenied("Вы не можете удалить чужой рецепт")
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=[
            "get"], permission_classes=[AllowAny], url_path="get-link"
    )
    def get_link(self, request, pk=None):
        """Возвращает короткую ссылку на рецепт."""
        recipe = self.get_object()
        code = encode_id(recipe.id)
        short_url = request.build_absolute_uri(f"/s/{code}/")
        return Response({"short-link": short_url})

    def perform_create(self, serializer):
        """Сохраняет рецепт с автором."""
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        """Проверяет права при обновлении и сохраняет рецепт."""
        if serializer.instance.author != self.request.user:
            raise PermissionDenied("Вы не можете редактировать чужой рецепт")
        serializer.save()

    @action(
        detail=True, methods=[
            "post", "delete"], permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        """Добавляет или удаляет рецепт из избранного."""
        return self._toggle_relation(
            request,
            pk,
            relation_name="favorites",
            error_messages={
                "already_exists": "Рецепт уже в избранном",
                "not_exists": "Рецепта нет в избранном",
            },
        )

    @action(
        detail=True, methods=[
            "post", "delete"], permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        """Добавляет или удаляет рецепт из корзины покупок."""
        return self._toggle_relation(
            request,
            pk,
            relation_name="shopping_cart",
            error_messages={
                "already_exists": "Рецепт уже в корзине",
                "not_exists": "Рецепта нет в корзине",
            },
        )

    @action(detail=False, methods=[
        "get"], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """Скачивает список покупок в формате txt."""
        user = request.user
        cart_items = user.shopping_cart.all()

        if not cart_items:
            return Response(
                {"error": "Корзина покупок пуста"},
                status=status.HTTP_400_BAD_REQUEST
            )

        recipes = [item.recipe for item in cart_items]

        ingredients_dict = {}
        for recipe in recipes:
            for ingredient_amount in recipe.ingredients_amounts.all():
                ingredient = ingredient_amount.ingredient
                name = ingredient.name
                unit = ingredient.measurement_unit
                amount = ingredient_amount.amount

                key = (name, unit)
                ingredients_dict[key] = ingredients_dict.get(key, 0) + amount

        lines = []
        for (name, unit), total_amount in ingredients_dict.items():
            lines.append(f"{name} ({unit}) — {total_amount}")

        content = "\n".join(lines)

        response = HttpResponse(content, content_type="text/plain")
        response[
            "Content-Disposition"] = 'attachment; filename="shopping_list.txt"'
        return response


def redirect_to_recipe(request, code):
    """Редирект с короткой ссылки на страницу рецепта."""
    if not is_valid_code(code):
        raise Http404("Неверный формат короткой ссылки")

    try:
        recipe_id = decode_code(code)
        get_object_or_404(Recipe, id=recipe_id)
    except (ValueError, OverflowError):
        raise Http404("Рецепт не найден")

    return redirect(f"/recipes/{recipe_id}/")
