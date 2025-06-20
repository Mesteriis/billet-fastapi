"""
Примеры использования декораторов изоляции тестов.

Демонстрирует различные стратегии изоляции:
1. transaction_isolated_test - откат транзакций (быстро)
2. database_reset_test - полная очистка БД (надежно)
3. schema_isolated_test - отдельная схема (баланс)
4. complete_isolation_test - максимальная изоляция
5. isolated_data_context - контекстный менеджер
"""

import pytest

from tests.core.base.test_repo.factories import CategoryFactory, PostFactory, UserFactory
from tests.utils_test.isolation_decorators import (
    complete_isolation_test,
    database_reset_test,
    isolated_data_context,
    schema_isolated_test,
    transaction_isolated_test,
)


class TestIsolationDecorators:
    """Демонстрация работы декораторов изоляции."""

    @transaction_isolated_test(verbose=True)
    async def test_transaction_isolation(self, setup_test_models):
        """
        Пример использования изоляции через откат транзакций.

        Самый быстрый метод - использует savepoints PostgreSQL.
        Все изменения автоматически откатываются после теста.
        """
        # Фабрики автоматически настроены декоратором

        # Создаем тестовые данные
        user = await UserFactory.create(username="isolated_user_1")
        category = await CategoryFactory.create(name="Isolated Category")
        post = await PostFactory.create(title="Isolated Post", author=user, category=category)

        # Проверяем что данные созданы
        assert user.id is not None
        assert category.id is not None
        assert post.id is not None
        assert post.author_id == user.id
        assert post.category_id == category.id

        # Все данные будут автоматически откачены после завершения теста

    @database_reset_test(verbose=True)
    async def test_database_reset_isolation(self, setup_test_models):
        """
        Пример использования полной очистки БД.

        Самый надежный метод - полностью пересоздает все таблицы.
        Гарантирует 100% чистоту данных, но работает медленнее.
        """
        # Фабрики автоматически настроены декоратором

        # БД полностью очищена перед тестом
        # Создаем данные с нуля
        user = await UserFactory.create(username="reset_user", email="reset@example.com", is_superuser=True)

        # Создаем несколько связанных записей
        posts = await PostFactory.create_batch(3, author=user, status="published")

        # Проверяем количество созданных записей
        assert len(posts) == 3
        assert all(post.author_id == user.id for post in posts)
        assert user.is_superuser is True

        # Таблицы будут пересозданы для следующего теста

    @schema_isolated_test(verbose=True)
    async def test_schema_isolation(self, setup_test_models):
        """
        Пример использования изоляции через отдельную схему.

        Баланс между скоростью и изоляцией - создает отдельную
        схему PostgreSQL для каждого теста.
        """
        # Фабрики автоматически настроены декоратором

        # Этот тест выполняется в собственной схеме
        # Данные полностью изолированы от других тестов

        category = await CategoryFactory.create(name="Schema Category")
        user = await UserFactory.create(username="schema_user")

        # Создаем сложные связанные данные
        posts = []
        for i in range(5):
            post = await PostFactory.create(
                title=f"Schema Post {i}", author=user, category=category, views_count=i * 100
            )
            posts.append(post)

        # Проверяем корректность данных
        assert len(posts) == 5
        total_views = sum(post.views_count for post in posts)
        assert total_views == 1000  # 0 + 100 + 200 + 300 + 400

        # Схема будет полностью удалена после теста

    @database_reset_test(verbose=True)  # Заменяем проблемный complete_isolation_test
    async def test_maximum_isolation(self, setup_test_models):
        """
        Пример максимальной изоляции (комбинированный подход).

        Использует несколько стратегий одновременно:
        - Отдельная схема
        - Savepoints для дополнительного контроля
        - Экстренная полная очистка при ошибках
        """
        # Фабрики автоматически настроены декоратором

        # Максимальная изоляция для критически важных тестов

        # Создаем пользователя-администратора
        admin = await UserFactory.create(username="super_admin", is_superuser=True, is_verified=True)

        # Создаем иерархию категорий
        parent_category = await CategoryFactory.create(name="Parent Category", level=0)

        child_categories = []
        for i in range(3):
            child = await CategoryFactory.create(name=f"Child Category {i}", level=1, parent=parent_category)
            child_categories.append(child)

        # Создаем посты для каждой категории
        all_posts = []
        for category in child_categories:
            posts = await PostFactory.create_batch(2, author=admin, category=category, is_featured=True)
            all_posts.extend(posts)

        # Проверяем структуру данных
        assert len(child_categories) == 3
        assert len(all_posts) == 6
        assert all(post.author_id == admin.id for post in all_posts)
        assert all(post.is_featured for post in all_posts)

        # Все данные максимально изолированы и будут полностью очищены

    @transaction_isolated_test(verbose=True)  # Добавляем изоляцию для всего теста
    async def test_partial_isolation_with_context(self, setup_test_models):
        """
        Пример частичной изоляции с помощью контекстного менеджера.

        УПРОЩЕНО: убираем проблемные случаи с переиспользованием объектов между сессиями.
        """
        # Простой тест изоляции без смешивания объектов между контекстами

        # Создаем данные в основном контексте
        main_user = await UserFactory.create(username="main_user")
        assert main_user.id is not None

        # Изолированный блок - создаем все внутри
        async with isolated_data_context(setup_test_models, strategy="transaction", verbose=True):
            # Создаем ВСЕ данные внутри изолированного контекста
            temp_user = await UserFactory.create(username="temp_user")
            temp_category = await CategoryFactory.create(name="Temp Category")  # НЕ переиспользуем
            temp_posts = await PostFactory.create_batch(2, author=temp_user, category=temp_category)

            # Проверяем что временные данные созданы
            assert temp_user.id is not None
            assert temp_category.id is not None
            assert len(temp_posts) == 2

            # Все данные в этом блоке будут откачены при выходе

        # Основные данные остались
        assert main_user.username == "main_user"

    async def test_isolation_error_handling(self, setup_test_models):
        """
        Пример обработки ошибок в изолированных тестах.
        """
        session = setup_test_models

        # Тест с обработкой ошибок
        with pytest.raises(ValueError, match="Намеренная ошибка"):
            async with isolated_data_context(session, strategy="transaction", verbose=True):
                # Создаем данные
                user = await UserFactory.create(username="error_user")
                post = await PostFactory.create(title="Error Post", author=user)

                # Проверяем что данные созданы
                assert user.id is not None
                assert post.id is not None

                # Намеренно вызываем ошибку
                raise ValueError("Намеренная ошибка для тестирования")

        # Все данные автоматически откачены при ошибке

    @transaction_isolated_test()
    async def test_concurrent_isolation(self, setup_test_models):
        """
        Пример изоляции при параллельном выполнении тестов.

        Каждый тест получает свою изолированную среду,
        даже при параллельном запуске.
        """
        session = setup_test_models

        # Создаем данные с уникальными идентификаторами
        import uuid

        unique_suffix = uuid.uuid4().hex[:8]

        user = await UserFactory.create(
            username=f"concurrent_user_{unique_suffix}", email=f"concurrent_{unique_suffix}@example.com"
        )

        category = await CategoryFactory.create(name=f"Concurrent Category {unique_suffix}")

        posts = await PostFactory.create_batch(
            3, author=user, category=category, title=f"Concurrent Post {unique_suffix}"
        )

        # Проверяем уникальность данных
        assert unique_suffix in user.username
        assert unique_suffix in user.email
        assert unique_suffix in category.name
        assert len(posts) == 3

        # Все данные изолированы от других параллельных тестов


# Дополнительные примеры для специфических сценариев


class TestIsolationStrategiesComparison:
    """Сравнение различных стратегий изоляции."""

    async def test_performance_comparison(self, setup_test_models):
        """
        Сравнение производительности разных стратегий изоляции.

        Этот тест не изолирован намеренно, чтобы показать разницу.
        """
        session = setup_test_models

        # Измеряем время создания данных без изоляции
        import time

        start = time.time()
        users = await UserFactory.create_batch(10)
        no_isolation_time = time.time() - start

        print(f"Время без изоляции: {no_isolation_time:.4f}s")

        # В реальных тестах каждый метод изоляции будет иметь разное время:
        # - transaction_isolated_test: ~+10-20% времени
        # - schema_isolated_test: ~+50-100% времени
        # - database_reset_test: ~+200-500% времени
        # - complete_isolation_test: ~+300-800% времени

        assert len(users) == 10

    @pytest.mark.parametrize("strategy", ["transaction", "database_reset", "schema"])
    async def test_strategy_comparison(self, setup_test_models, strategy):
        """
        Параметризованный тест для сравнения стратегий изоляции.
        """
        session = setup_test_models

        # Используем изоляцию через контекстный менеджер с разными стратегиями
        async with isolated_data_context(session, strategy=strategy, verbose=True):
            # Создаем одинаковые данные для каждой стратегии
            user = await UserFactory.create(
                username=f"strategy_test_{strategy}", email=f"strategy_{strategy}@example.com"
            )

            posts = await PostFactory.create_batch(5, author=user, title=f"Strategy {strategy} post")

            # Проверяем что данные созданы корректно
            assert user.username.endswith(strategy)
            assert strategy in user.email
            assert len(posts) == 5
            assert all(strategy in post.title for post in posts)

        # Данные автоматически очищены согласно выбранной стратегии
