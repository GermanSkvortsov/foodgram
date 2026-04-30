# Foodgram - сервис публикации рецептов

## Адрес проекта
- http://158.160.155.176:8001
- http://foodgram-test.servegame.com:8001

## Админка
- http://158.160.155.176:8001/admin/
- http://foodgram-test.servegame.com:8001/admin/

## API документация
- http://158.160.155.176:8001/api/docs/

## Данные для входа
- Тестовый пользователь: user1@test.ru / Testpass123
- Тестовый пользователь: user2@test.ru / Testpass123

## Описание
Сайт, на котором пользователи публикуют рецепты, добавляют чужие рецепты в избранное, подписываются на авторов и создают список покупок.

## Функционал
- Регистрация и аутентификация по токенам
- CRUD рецептов с ингредиентами и тегами
- Добавление в избранное и список покупок
- Подписки на авторов
- Фильтрация рецептов по тегам
- Скачивание списка покупок с суммированием ингредиентов
- Смена пароля и аватара
- Админ-панель Django
- Короткие ссылки на рецепты

## Стек технологий
- Django REST Framework
- PostgreSQL
- Docker
- Nginx
- React (фронтенд)
- GitHub Actions (CI/CD)
- Djoser (аутентификация)
- Django Filters

## Как развернуть в Docker

1. Склонируйте репозиторий:
```bash
git clone <url-репозитория>
cd foodgram
```

2. Создайте файл `.env` в корне проекта со следующими переменными:
```
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-host,127.0.0.1
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
DB_HOST=db
DB_PORT=5432
CSRF_TRUSTED_ORIGINS=http://your-domain:8001
```

3. Запустите контейнеры:
```bash
cd infra
docker compose --env-file ../.env -f docker-compose.production.yml up -d --build
```

4. Выполните миграции и соберите статику:
```bash
docker compose --env-file ../.env -f docker-compose.production.yml exec backend python manage.py migrate
docker compose --env-file ../.env -f docker-compose.production.yml exec backend python manage.py collectstatic --noinput
```

5. Загрузите ингредиенты и создайте теги:
```bash
docker compose --env-file ../.env -f docker-compose.production.yml exec backend python manage.py load_ingredients data/ingredients.json
docker compose --env-file ../.env -f docker-compose.production.yml exec backend python manage.py shell -c "
from recipes.models import Tag
for name, slug in [('Завтрак', 'breakfast'), ('Обед', 'lunch'), ('Ужин', 'dinner')]:
    Tag.objects.get_or_create(name=name, slug=slug)
"
```

6. Создайте суперпользователя:
```bash
docker compose --env-file ../.env -f docker-compose.production.yml exec backend python manage.py createsuperuser
```

## Примеры запросов к API

### Регистрация
```http
POST /api/users/
Content-Type: application/json

{
    "email": "user@example.com",
    "username": "user",
    "first_name": "Имя",
    "last_name": "Фамилия",
    "password": "password123"
}
```

### Получение токена
```http
POST /api/auth/token/login/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "password123"
}
```

Ответ:
```json
{
    "auth_token": "токен-пользователя"
}
```

### Создание рецепта
```http
POST /api/recipes/
Authorization: Token <auth_token>
Content-Type: application/json

{
    "ingredients": [{"id": 1, "amount": 100}],
    "tags": [1, 2],
    "image": "data:image/png;base64,...",
    "name": "Название рецепта",
    "text": "Описание",
    "cooking_time": 30
}
```

### Список рецептов
```http
GET /api/recipes/?tags=breakfast&limit=6
```

### Добавить в избранное
```http
POST /api/recipes/{id}/favorite/
Authorization: Token <auth_token>
```

### Скачать список покупок
```http
GET /api/recipes/download_shopping_cart/
Authorization: Token <auth_token>
```

## Автор
## Автор
Герман Скворцов — [GitHub](https://github.com/GermanSkvortsov/)
Разработано в рамках финального задания курса «Python-разработчик» Яндекс.Практикума.
