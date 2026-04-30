"""
Кастомная пагинация для API.
Определяет размер страницы по умолчанию и поддержку параметра limit.
"""

from rest_framework.pagination import PageNumberPagination

PAGE_SIZE = 6


class RecipePagination(PageNumberPagination):
    """
    Пагинатор с поддержкой параметра limit.

    Позволяет клиенту указывать количество объектов на странице
    через query-параметр ?limit=.
    """

    page_size = PAGE_SIZE
    page_size_query_param = "limit"
