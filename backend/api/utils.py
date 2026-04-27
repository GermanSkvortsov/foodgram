"""
Утилиты для создания коротких ссылок.

Содержит функции кодирования/декодирования ID в base62 и проверки кода.
"""

import re

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)


def encode_id(number: int) -> str:
    """Кодирует числовой ID в короткую строку (base62)."""
    if number == 0:
        return ALPHABET[0]

    result = []
    while number > 0:
        number, remainder = divmod(number, BASE)
        result.append(ALPHABET[remainder])
    return "".join(reversed(result))


def decode_code(code: str) -> int:
    """Декодирует короткую строку обратно в числовой ID."""
    number = 0
    for char in code:
        number = number * BASE + ALPHABET.index(char)
    return number


def is_valid_code(code: str) -> bool:
    """Проверяет, что код состоит только из допустимых символов."""
    return bool(re.match(f"^[{ALPHABET}]+$", code))
