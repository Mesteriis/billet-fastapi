# Расширенные возможности BaseRepository

## Обзор новых функций

BaseRepository теперь поддерживает четыре мощные функции для работы с большими данными:

1. **Полнотекстовый поиск PostgreSQL** - быстрый поиск по содержимому
2. **Кэширование запросов** - Redis + Memory fallback для ускорения
3. **Агрегации данных** - SUM, AVG, MAX, MIN с группировкой
4. **Курсорная пагинация** - эффективная пагинация больших данных

## 1. Полнотекстовый поиск PostgreSQL

Использует встроенные возможности PostgreSQL для быстрого поиска по тексту.

### Основные операторы:

- `search` - обычный поиск (русский язык)
- `search_phrase` - поиск точной фразы
- `search_websearch` - веб-поиск с операторами AND/OR
- `search_raw` - расширенный tsquery синтаксис
- `search_en` - поиск на английском языке

### Пример использования:

```python
# Простой поиск
results = await repo.fulltext_search(
    search_fields=["title", "content"],
    query_text="python fastapi",
    search_type="simple"
)

# Поиск с рангом релевантности
ranked_results = await repo.fulltext_search(
    search_fields=["title", "description"],
    query_text="машинное обучение",
    search_type="websearch",
    include_rank=True,
    min_rank=0.1,
    status="published"
)
```

## 2. Кэширование запросов

Двухуровневая система кэширования для ускорения повторных запросов.

### Настройка кэша:

```python
from redis.asyncio import Redis
from core.base.repo.repository import CacheConfig

# Полная настройка с Redis
redis_client = Redis.from_url("redis://localhost:6379")
cache_config = CacheConfig(
    redis_client=redis_client,
    default_ttl=600,  # 10 минут
    use_redis=True,
    use_memory=True
)

# Только memory кэш
cache_config = CacheConfig(
    default_ttl=300,
    use_redis=False,
    use_memory=True
)

# Создание репозитория с кэшем
repo = BaseRepository(User, db_session, cache_config)
```

### Управление кэшем:

```python
# Очистка всего кэша модели
await repo.invalidate_cache()

# Очистка по паттерну
await repo.invalidate_cache("list:*")
```

## 3. Агрегации данных

Выполнение агрегатных функций на уровне базы данных.

### Доступные операции:

- `count` - количество записей
- `sum` - сумма значений
- `avg` - среднее значение
- `min` - минимальное значение
- `max` - максимальное значение

### Примеры:

```python
# Базовая статистика
stats = await repo.aggregate(
    field="salary",
    operations=["count", "avg", "min", "max"],
    is_active=True
)

# С группировкой
dept_stats = await repo.aggregate(
    field="salary",
    operations=["count", "avg"],
    group_by="department",
    is_active=True
)

# Результат:
for stat in dept_stats:
    print(f"Отдел: {stat.group_by['department']}")
    print(f"Сотрудников: {stat.count}")
    print(f"Средняя зарплата: {stat.avg}")
```

## 4. Курсорная пагинация

Эффективная пагинация больших датасетов без производительных проблем offset.

### Преимущества:

- Константная скорость независимо от позиции
- Устойчивость к изменениям данных
- Эффективное использование индексов

### Пример использования:

```python
# Первая страница
page1 = await repo.paginate_cursor(
    cursor_field="created_at",
    limit=20,
    include_total=True  # Медленно на больших данных
)

print(f"Загружено: {len(page1.items)}")
print(f"Есть следующая: {page1.has_next}")
print(f"Курсор: {page1.next_cursor}")

# Следующая страница
if page1.has_next:
    page2 = await repo.paginate_cursor(
        cursor_field="created_at",
        cursor_value=page1.next_cursor,
        direction="next",
        limit=20
    )

# Предыдущая страница
if page2.has_prev:
    page_prev = await repo.paginate_cursor(
        cursor_field="created_at",
        cursor_value=page2.prev_cursor,
        direction="prev",
        limit=20
    )
```

## Производительность

### Рекомендации:

1. **Полнотекстовый поиск**: Создайте GIN индексы для ускорения:

   ```sql
   CREATE INDEX idx_articles_search ON articles
   USING gin(to_tsvector('russian', title || ' ' || content));
   ```

2. **Кэширование**: Используйте Redis для распределенного кэширования

3. **Агрегации**: Добавьте индексы на поля группировки и агрегации

4. **Курсорная пагинация**: Используйте уникальные, упорядоченные поля (id, created_at)

### Сравнение производительности:

```python
# Медленно на больших offset
users = await repo.list(offset=100000, limit=20)  # ~500ms

# Быстро всегда
page = await repo.paginate_cursor(limit=20)  # ~2ms
```

## Интеграция с существующим кодом

Все новые функции полностью совместимы с существующими методами:

```python
# Обычные запросы работают как прежде
users = await repo.list(is_active=True)
user = await repo.get(user_id)

# Новые функции доступны опционально
search_results = await repo.fulltext_search(...)
stats = await repo.aggregate(...)
page = await repo.paginate_cursor(...)
```

Кэш автоматически инвалидируется при изменениях данных (create/update/delete).

## Настройка PostgreSQL

Для полнотекстового поиска рекомендуется:

```sql
-- Установка русского языка (если нужно)
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Создание индексов для поиска
CREATE INDEX idx_articles_search_ru ON articles
USING gin(to_tsvector('russian', title || ' ' || content));

CREATE INDEX idx_articles_search_en ON articles
USING gin(to_tsvector('english', title || ' ' || content));
```
