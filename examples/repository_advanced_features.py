#!/usr/bin/env python3
"""
Демонстрация расширенных возможностей BaseRepository

Этот файл демонстрирует использование новых функций:
- Полнотекстовый поиск PostgreSQL
- Кэширование запросов (Redis + Memory)
- Агрегации данных
- Курсорная пагинация
"""

import asyncio
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import relationship, sessionmaker

from src.core.base.models import BaseModel as SQLAlchemyBaseModel
from src.core.base.repo.repository import BaseRepository, CacheConfig
from src.tools.pydantic import BaseModel as PydanticBaseModel


# Модели данных
class Article(SQLAlchemyBaseModel):
    """Модель статьи для демонстрации."""

    __tablename__ = "articles"

    title: str = Column(String(200), nullable=False)
    content: str = Column(Text, nullable=False)
    author_id: uuid.UUID = Column(ForeignKey("users.id"), nullable=False)
    views: int = Column(Integer, default=0)
    likes: int = Column(Integer, default=0)
    published: bool = Column(Boolean, default=False)
    category: str = Column(String(50), nullable=True)

    # Связь с автором
    author = relationship("User", back_populates="articles")


class User(SQLAlchemyBaseModel):
    """Модель пользователя для демонстрации."""

    __tablename__ = "users"

    name: str = Column(String(100), nullable=False)
    email: str = Column(String(100), unique=True, nullable=False)
    age: int = Column(Integer, nullable=True)
    department: str = Column(String(50), nullable=True)
    salary: float = Column(Integer, nullable=True)
    is_active: bool = Column(Boolean, default=True)

    # Связь со статьями
    articles = relationship("Article", back_populates="author")


# Pydantic схемы
class ArticleCreate(PydanticBaseModel):
    title: str
    content: str
    author_id: uuid.UUID
    category: Optional[str] = None


class ArticleUpdate(PydanticBaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    published: Optional[bool] = None
    category: Optional[str] = None


class UserCreate(PydanticBaseModel):
    name: str
    email: str
    age: Optional[int] = None
    department: Optional[str] = None
    salary: Optional[float] = None


class UserUpdate(PydanticBaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    department: Optional[str] = None
    salary: Optional[float] = None
    is_active: Optional[bool] = None


async def demonstrate_advanced_features():
    """Демонстрация расширенных возможностей репозитория."""

    # Настройка подключения к БД (замените на свои параметры)
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Настройка кэша (опционально)
        cache_config = CacheConfig(
            default_ttl=300,  # 5 минут
            use_memory=True,
            use_redis=False,  # Отключаем Redis для демо
        )

        # Создаем репозитории
        user_repo = BaseRepository[User, UserCreate, UserUpdate](User, session, cache_config)
        article_repo = BaseRepository[Article, ArticleCreate, ArticleUpdate](Article, session, cache_config)

        print("=== Демонстрация расширенных возможностей BaseRepository ===\n")

        # 1. Полнотекстовый поиск
        print("1. ПОЛНОТЕКСТОВЫЙ ПОИСК POSTGRESQL")
        print("-" * 40)

        # Простой поиск
        search_results = await article_repo.fulltext_search(
            search_fields=["title", "content"], query_text="python fastapi", search_type="simple", limit=10
        )
        print(f"Найдено статей по запросу 'python fastapi': {len(search_results)}")

        # Поиск с рангом
        ranked_results = await article_repo.fulltext_search(
            search_fields=["title", "content"],
            query_text="машинное обучение",
            search_type="websearch",
            include_rank=True,
            min_rank=0.1,
            published=True,
        )
        print(f"Найдено статей с рангом по запросу 'машинное обучение': {len(ranked_results)}")

        if ranked_results:
            print("Топ результатов:")
            for result in ranked_results[:3]:
                print(f"  - Ранг: {result['rank']:.3f}, Статья: {result['item'].title}")

        print()

        # 2. Агрегации данных
        print("2. АГРЕГАЦИИ ДАННЫХ")
        print("-" * 20)

        # Статистика по просмотрам статей
        view_stats = await article_repo.aggregate(
            field="views", operations=["count", "sum", "avg", "min", "max"], published=True
        )

        if view_stats:
            stats = view_stats[0]
            print(f"Статистика просмотров статей:")
            print(f"  - Всего статей: {stats.count}")
            print(f"  - Общие просмотры: {stats.sum}")
            print(f"  - Среднее просмотров: {stats.avg:.2f}")
            print(f"  - Минимум: {stats.min}")
            print(f"  - Максимум: {stats.max}")

        # Группировка по категориям
        category_stats = await article_repo.aggregate(
            field="views", operations=["count", "sum"], group_by="category", published=True
        )

        print(f"\nСтатистика по категориям:")
        for stat in category_stats:
            category = stat.group_by.get("category", "Без категории") if stat.group_by else "Без категории"
            print(f"  - {category}: {stat.count} статей, {stat.sum} просмотров")

        # Статистика по зарплатам пользователей
        salary_stats = await user_repo.aggregate(
            field="salary", operations=["count", "avg", "min", "max"], group_by="department", is_active=True
        )

        print(f"\nСтатистика зарплат по отделам:")
        for stat in salary_stats:
            dept = stat.group_by.get("department", "Без отдела") if stat.group_by else "Без отдела"
            print(f"  - {dept}: {stat.count} сотрудников, средняя зарплата: {stat.avg:.2f}")

        print()

        # 3. Курсорная пагинация
        print("3. КУРСОРНАЯ ПАГИНАЦИЯ")
        print("-" * 25)

        # Первая страница
        print("Загружаем первые 5 статей:")
        page1 = await article_repo.paginate_cursor(
            cursor_field="created_at", limit=5, include_total=True, published=True
        )

        print(f"Страница 1:")
        print(f"  - Загружено: {len(page1.items)}")
        print(f"  - Есть следующая: {page1.has_next}")
        print(f"  - Есть предыдущая: {page1.has_prev}")
        print(f"  - Общее количество: {page1.total_count}")
        print(f"  - Следующий курсор: {page1.next_cursor}")

        # Вторая страница
        if page1.has_next:
            print("\nЗагружаем следующие 5 статей:")
            page2 = await article_repo.paginate_cursor(
                cursor_field="created_at", cursor_value=page1.next_cursor, direction="next", limit=5, published=True
            )

            print(f"Страница 2:")
            print(f"  - Загружено: {len(page2.items)}")
            print(f"  - Есть следующая: {page2.has_next}")
            print(f"  - Есть предыдущая: {page2.has_prev}")
            print(f"  - Предыдущий курсор: {page2.prev_cursor}")

        print()

        # 4. Демонстрация кэширования
        print("4. КЭШИРОВАНИЕ ЗАПРОСОВ")
        print("-" * 25)

        # Первый запрос (без кэша)
        start_time = datetime.now()
        users1 = await user_repo.list(limit=100, is_active=True)
        time1 = (datetime.now() - start_time).total_seconds()
        print(f"Первый запрос (без кэша): {time1:.4f}s, найдено: {len(users1)}")

        # Второй запрос (из кэша)
        start_time = datetime.now()
        users2 = await user_repo.list(limit=100, is_active=True)
        time2 = (datetime.now() - start_time).total_seconds()
        print(f"Второй запрос (из кэша): {time2:.4f}s, найдено: {len(users2)}")

        if time1 > 0 and time2 > 0:
            speedup = time1 / time2
            print(f"Ускорение за счет кэша: {speedup:.1f}x")

        # Очистка кэша
        await user_repo.invalidate_cache()
        print("Кэш очищен")

        print()

        # 5. Расширенная фильтрация
        print("5. РАСШИРЕННАЯ ФИЛЬТРАЦИЯ")
        print("-" * 30)

        # Комплексные фильтры
        complex_articles = await article_repo.list_with_complex_filters(
            {
                "AND": [
                    {"published": True},
                    {"views__gte": 100},
                    {"OR": [{"category": "technology"}, {"likes__gte": 50}]},
                    {"NOT": [{"title__icontains": "test"}]},
                ]
            }
        )
        print(f"Найдено статей по сложным фильтрам: {len(complex_articles)}")

        # Фильтры по связанным объектам
        popular_articles = await article_repo.list(
            views__gte=1000,
            likes__gte=100,
            author__department="engineering",
            created_at__date_gte=date(2023, 1, 1),
            published=True,
            order_by="views",
        )
        print(f"Популярные статьи от инженеров: {len(popular_articles)}")

        # Фильтры по датам
        recent_articles = await article_repo.list(
            created_at__date_gte=date(2023, 6, 1),
            created_at__hour__between=[9, 18],  # Рабочие часы
            created_at__week_day__in=[1, 2, 3, 4, 5],  # Будни
            published=True,
        )
        print(f"Статьи, опубликованные в рабочие часы: {len(recent_articles)}")

        print()

        # 6. Производительность
        print("6. МОНИТОРИНГ ПРОИЗВОДИТЕЛЬНОСТИ")
        print("-" * 35)

        # Сравнение обычной и курсорной пагинации
        print("Сравнение пагинации:")

        # Обычная пагинация (медленная на больших offset)
        start_time = datetime.now()
        offset_articles = await article_repo.list(offset=10000, limit=10)
        offset_time = (datetime.now() - start_time).total_seconds()
        print(f"Offset пагинация (10000 пропущено): {offset_time:.4f}s")

        # Курсорная пагинация (быстрая всегда)
        start_time = datetime.now()
        cursor_page = await article_repo.paginate_cursor(cursor_field="id", limit=10)
        cursor_time = (datetime.now() - start_time).total_seconds()
        print(f"Курсорная пагинация: {cursor_time:.4f}s")

        print("\n=== Демонстрация завершена ===")


async def setup_demo_data():
    """Создает демонстрационные данные для тестирования."""

    # Настройка подключения к БД
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        user_repo = BaseRepository[User, UserCreate, UserUpdate](User, session)
        article_repo = BaseRepository[Article, ArticleCreate, ArticleUpdate](Article, session)

        print("Создаем демонстрационные данные...")

        # Создаем пользователей
        departments = ["engineering", "marketing", "sales", "hr", "finance"]
        for i in range(20):
            user_data = UserCreate(
                name=f"User {i + 1}",
                email=f"user{i + 1}@company.com",
                age=25 + (i % 15),
                department=departments[i % len(departments)],
                salary=50000 + (i * 5000),
            )
            await user_repo.create(user_data)

        # Получаем всех пользователей
        users = await user_repo.list()

        # Создаем статьи
        categories = ["technology", "science", "business", "lifestyle", "education"]
        titles = [
            "Введение в Python",
            "FastAPI для начинающих",
            "Машинное обучение на практике",
            "Как создать API",
            "Основы PostgreSQL",
            "Docker и контейнеризация",
            "Тестирование в Python",
            "Асинхронное программирование",
            "Работа с базами данных",
            "Развертывание приложений",
        ]

        for i in range(100):
            title = f"{titles[i % len(titles)]} - Часть {i + 1}"
            content = f"Содержание статьи {i + 1}. Это подробное описание темы {title}."

            article_data = ArticleCreate(
                title=title,
                content=content,
                author_id=users[i % len(users)].id,
                category=categories[i % len(categories)],
            )

            article = await article_repo.create(article_data)

            # Добавляем случайные просмотры и лайки
            await article_repo.update(
                article,
                {
                    "views": (i * 37) % 5000,
                    "likes": (i * 17) % 500,
                    "published": i % 3 != 0,  # 2/3 статей опубликованы
                },
            )

        await session.commit()
        print("Демонстрационные данные созданы!")


if __name__ == "__main__":
    # Запуск демонстрации
    # Сначала создаем данные (раскомментируйте при первом запуске):
    # asyncio.run(setup_demo_data())

    # Затем запускаем демонстрацию:
    asyncio.run(demonstrate_advanced_features())
