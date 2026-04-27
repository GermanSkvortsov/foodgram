"""
Кастомная пагинация для API.
Определяет размер страницы по умолчанию и поддержку параметра limit.
"""

from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    """
    Пагинатор с поддержкой параметра limit.

    Позволяет клиенту указывать количество объектов на странице
    через query-параметр ?limit=.
    """

    page_size = 6
    page_size_query_param = "limit"
    max_page_size = 100
