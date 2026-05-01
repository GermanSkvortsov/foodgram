"""
Модели приложения users.

Содержит кастомную модель User и модель Follow (подписки).
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CheckConstraint, F, Q


USERNAME_MAX_LEN = 150
FIRST_NAME_MAX_LEN = 150
LAST_NAME_MAX_LEN = 150


class User(AbstractUser):
    """Кастомная модель пользователя с email в качестве логина."""

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ("username", "first_name", "last_name")  # type: ignore

    email = models.EmailField(
        unique=True,
        verbose_name="Адрес электронной почты"
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True, null=True,
        verbose_name="Аватар"
    )
    first_name = models.CharField(
        max_length=FIRST_NAME_MAX_LEN,
        blank=False,
        verbose_name="Имя"
    )
    last_name = models.CharField(
        max_length=LAST_NAME_MAX_LEN,
        blank=False,
        verbose_name="Фамилия"
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.username


class Follow(models.Model):
    """Модель подписки на авторов."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower",
        verbose_name="Подписчик",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following",
        verbose_name="Автор",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата подписки"
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = (
            models.UniqueConstraint(
                fields=("user", "author"), name="unique_follow"
            ),
            CheckConstraint(
                check=~Q(user=F("author")),
                name="user_not_author",
            ),
        )

    def __str__(self):
        return f"{self.user} подписан на {self.author}"
