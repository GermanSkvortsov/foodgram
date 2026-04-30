"""
Views для API.

Содержит ViewSet для тегов, ингредиентов, подписок и рецептов.
"""

import base64
import uuid

from django.core.files.base import ContentFile
from django.db.models import F, Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from recipes.models import Ingredient, IngredientAmount, Recipe, Tag
from users.models import User
from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    FavoriteCreateSerializer,
    FollowCreateSerializer,
    IngredientSerializer,
    RecipeCreateUpdateSerializer,
    RecipeSerializer,
    ShoppingCartCreateSerializer,
    TagSerializer,
    UserWithRecipesSerializer,
)


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
    filterset_class = IngredientFilter
    pagination_class = None


class SubscriptionViewSet(UserViewSet):
    """ViewSet для подписок и аватара пользователя."""

    queryset = User.objects.all()

    # Djoser требует get_permissions для разных прав на разные actions.
    # Без этого метода retrieve требует авторизацию,
    # что противоречит спецификации API.
    def get_permissions(self):
        if self.action in ("retrieve", "list", "create"):
            return (AllowAny(),)
        return (IsAuthenticated(),)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=(IsAuthenticated,),
        url_path="me",
    )
    def me(self, request):
        """Возвращает данные текущего пользователя."""
        return super().me(request)

    @action(detail=False, methods=["put"], url_path="me/avatar")
    def avatar(self, request):
        """Добавляет аватар текущего пользователя."""
        avatar_data = request.data.get("avatar")
        if not avatar_data:
            return Response(
                {"avatar": "Это поле обязательно."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        format, imgstr = avatar_data.split(";base64,")
        ext = format.split("/")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        data = ContentFile(base64.b64decode(imgstr), name=filename)
        request.user.avatar.save(filename, data, save=True)

        return Response(
            {"avatar": request.build_absolute_uri(request.user.avatar.url)},
            status=status.HTTP_200_OK,
        )

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаляет аватар текущего пользователя."""
        if request.user.avatar:
            request.user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="subscribe")
    def subscribe(self, request, id=None):
        """Подписывает текущего пользователя на автора."""
        author = self.get_object()
        data = {"user": request.user.id, "author": author.id}
        serializer = FollowCreateSerializer(
            data=data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        """Отписывает текущего пользователя от автора."""
        author = self.get_object()
        user = request.user
        deleted_count, _ = user.follower.filter(author=author).delete()
        if not deleted_count:
            return Response(
                {"error": "Вы не подписаны на этого автора"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="subscriptions")
    def subscriptions(self, request):
        """Возвращает список авторов, на которых подписан пользователь."""
        user = request.user
        authors = User.objects.filter(following__user=user)
        page = self.paginate_queryset(authors)
        serializer = UserWithRecipesSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для рецептов (полный CRUD)."""

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = RecipeFilter
    search_fields = ("name",)

    def get_serializer_class(self):
        """Возвращает нужный сериализатор в зависимости от действия."""
        if self.action in ("create", "partial_update"):
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    @action(
        detail=True,
        methods=["get"],
        permission_classes=[AllowAny],
        url_path="get-link",
    )
    def get_link(self, request, pk=None):
        """Возвращает короткую ссылку на рецепт."""
        recipe = self.get_object()
        short_url = request.build_absolute_uri(f"/s/{recipe.short_code}/")
        return Response({"short-link": short_url})

    @action(detail=True,
            methods=["post"],
            permission_classes=[IsAuthenticated]
            )
    def favorite(self, request, pk=None):
        """Добавляет рецепт в избранное."""
        recipe = self.get_object()
        data = {"user": request.user.id, "recipe": recipe.id}
        serializer = FavoriteCreateSerializer(
            data=data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        """Удаляет рецепт из избранного."""
        recipe = self.get_object()
        deleted_count, _ = request.user.favorites.filter(
            recipe=recipe).delete()
        if not deleted_count:
            return Response(
                {"error": "Рецепта нет в избранном"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=["post"],
            permission_classes=[IsAuthenticated]
            )
    def shopping_cart(self, request, pk=None):
        """Добавляет рецепт в корзину покупок."""
        recipe = self.get_object()
        data = {"user": request.user.id, "recipe": recipe.id}
        serializer = ShoppingCartCreateSerializer(
            data=data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        """Удаляет рецепт из корзины покупок."""
        recipe = self.get_object()
        deleted_count, _ = (
            request.user.shopping_cart.filter(recipe=recipe).delete()
        )
        if not deleted_count:
            return Response(
                {"error": "Рецепта нет в корзине"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        """Скачивает список покупок в формате txt."""
        user = request.user

        if not user.shopping_cart.exists():
            return Response(
                {"error": "Корзина покупок пуста"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ingredients = (
            IngredientAmount.objects
            .filter(recipe__shopping_cart__user=user)
            .values(
                name=F("ingredient__name"),
                unit=F("ingredient__measurement_unit"),
            )
            .annotate(total=Sum("amount"))
            .order_by("name")
        )

        lines = [
            f"{item['name']} ({item['unit']}) — {item['total']}"
            for item in ingredients
        ]
        content = "\n".join(lines)

        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response


def redirect_to_recipe(request, code):
    """Редирект с короткой ссылки на страницу рецепта."""
    recipe = get_object_or_404(Recipe, short_code=code)
    return HttpResponseRedirect(f"/recipes/{recipe.pk}/")
