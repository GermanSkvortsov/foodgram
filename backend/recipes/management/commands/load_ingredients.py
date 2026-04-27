"""
Кастомные команды управления для загрузки данных.
"""

import json

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from recipes.models import Ingredient


class Command(BaseCommand):
    """Загружает ингредиенты из JSON-файла в базу данных."""

    help = "Загружает ингредиенты из JSON-файла в базу данных"

    def add_arguments(self, parser):
        parser.add_argument(
            "file_path", type=str, help="Путь к JSON-файлу с ингредиентами"
        )

    def handle(self, *args, **options):
        file_path = options["file_path"]
        created_count = 0
        skipped_count = 0

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                ingredients_data = json.load(file)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Файл не найден: {file_path}"))
            return
        except json.JSONDecodeError:
            self.stderr.write(
                self.style.ERROR(f"Ошибка декодирования JSON: {file_path}")
            )
            return

        for item in ingredients_data:
            name = item.get("name")
            measurement_unit = item.get("measurement_unit")

            if not name or not measurement_unit:
                self.stdout.write(
                    self.style.WARNING(
                        f"Пропущен ингредиент с некорректными данными: {item}"
                    )
                )
                skipped_count += 1
                continue

            try:
                Ingredient.objects.create(
                    name=name, measurement_unit=measurement_unit
                )
                created_count += 1
            except IntegrityError:
                self.stdout.write(
                    self.style.WARNING(
                        f"Ингредиент уже существует: {name}, "
                        f"{measurement_unit}"
                    )
                )
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Загрузка завершена. Создано: {created_count}, "
                f"Пропущено: {skipped_count}"
            )
        )
