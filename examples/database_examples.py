#!/usr/bin/env python3
"""
Примеры работы с базой данных и системой миграций.

Этот файл содержит практические примеры:
- Автоматического создания базы данных
- Работы с миграциями Alembic
- CRUD операций с SQLAlchemy
- Использования DatabaseManager
- Мониторинга состояния БД
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Импорты системы БД и миграций
from core.database import get_async_session, get_engine
from core.migrations import DatabaseManager, MigrationManager, MigrationValidator
from core.migrations.backup import MigrationBackup
from core.migrations.monitor import MigrationMonitor

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def database_creation_example():
    """Пример автоматического создания базы данных."""
    print("🗄️ Пример автоматического создания БД")

    db_manager = DatabaseManager()

    try:
        # Проверка существования БД
        print("🔍 Проверка существования базы данных...")
        exists = await db_manager.database_exists()
        print(f"   База данных существует: {'✅' if exists else '❌'}")

        if not exists:
            print("🔨 Создание базы данных...")
            created = await db_manager.create_database()
            if created:
                print("✅ База данных создана успешно")
            else:
                print("❌ Не удалось создать базу данных")

        # Тестирование подключения
        print("🔗 Тестирование подключения...")
        connection_ok = await db_manager.test_connection()
        print(f"   Подключение: {'✅' if connection_ok else '❌'}")

        # Получение информации о БД
        print("📊 Получение информации о базе данных...")
        info = await db_manager.get_database_info()

        print("📋 Информация о БД:")
        for key, value in info.items():
            print(f"   {key}: {value}")

        # Автоматическая проверка/создание
        print("\n🔄 Автоматическая проверка/создание БД...")
        ensured = await db_manager.ensure_database_exists()
        print(f"   БД готова к использованию: {'✅' if ensured else '❌'}")

    except Exception as e:
        logger.error(f"Ошибка работы с БД: {e}")


async def migration_management_example():
    """Пример управления миграциями."""
    print("\n🔄 Пример управления миграциями")

    migration_manager = MigrationManager()

    try:
        # Проверка текущего состояния
        print("📋 Проверка состояния миграций...")
        status = await migration_manager.get_migration_status()

        print("📊 Статус миграций:")
        print(f"   Текущая версия: {status.get('current_revision', 'Не определена')}")
        print(f"   Последняя версия: {status.get('head_revision', 'Не определена')}")
        print(f"   Ожидающие миграции: {len(status.get('pending_migrations', []))}")

        # Валидация миграций
        print("\n🔍 Валидация миграций...")
        validator = MigrationValidator()
        validation_result = await validator.validate_all_migrations()

        if validation_result["is_valid"]:
            print("✅ Все миграции валидны")
        else:
            print("❌ Найдены проблемы в миграциях:")
            for error in validation_result.get("errors", []):
                print(f"   - {error}")

        # Безопасное применение миграций
        print("\n🛡️ Безопасное применение миграций...")
        # result = await migration_manager.safe_migrate()
        # print(f"   Результат: {'✅' if result else '❌'}")
        print("   (Закомментировано для безопасности)")

    except Exception as e:
        logger.error(f"Ошибка управления миграциями: {e}")


async def migration_backup_example():
    """Пример создания бэкапов перед миграциями."""
    print("\n💾 Пример создания бэкапов")

    backup_manager = MigrationBackup()

    try:
        # Создание бэкапа
        print("📦 Создание бэкапа базы данных...")
        backup_path = await backup_manager.create_backup()

        if backup_path:
            print(f"✅ Бэкап создан: {backup_path}")

            # Получение информации о бэкапе
            backup_info = await backup_manager.get_backup_info(backup_path)
            print("📋 Информация о бэкапе:")
            for key, value in backup_info.items():
                print(f"   {key}: {value}")
        else:
            print("❌ Не удалось создать бэкап")

        # Список бэкапов
        print("\n📚 Список доступных бэкапов...")
        backups = await backup_manager.list_backups()

        if backups:
            print(f"   Найдено бэкапов: {len(backups)}")
            for backup in backups[:3]:  # Показываем только первые 3
                print(f"   - {backup}")
        else:
            print("   Бэкапы не найдены")

        # Очистка старых бэкапов
        print("\n🧹 Очистка старых бэкапов...")
        cleaned = await backup_manager.cleanup_old_backups(keep_count=5)
        print(f"   Удалено старых бэкапов: {cleaned}")

    except Exception as e:
        logger.error(f"Ошибка работы с бэкапами: {e}")


async def migration_monitoring_example():
    """Пример мониторинга миграций."""
    print("\n📊 Пример мониторинга миграций")

    monitor = MigrationMonitor()

    try:
        # Получение детального статуса
        print("📋 Детальный статус миграций...")
        detailed_status = await monitor.get_detailed_status()

        print("📊 Детальная информация:")
        for key, value in detailed_status.items():
            if isinstance(value, list):
                print(f"   {key}: {len(value)} элементов")
                for item in value[:2]:  # Показываем только первые 2
                    print(f"     - {item}")
            else:
                print(f"   {key}: {value}")

        # Проверка целостности
        print("\n🔍 Проверка целостности...")
        integrity_check = await monitor.check_integrity()

        if integrity_check["is_valid"]:
            print("✅ Целостность БД в порядке")
        else:
            print("❌ Найдены проблемы целостности:")
            for issue in integrity_check.get("issues", []):
                print(f"   - {issue}")

        # Анализ производительности
        print("\n⚡ Анализ производительности...")
        performance = await monitor.analyze_performance()

        print("📈 Метрики производительности:")
        for metric, value in performance.items():
            print(f"   {metric}: {value}")

    except Exception as e:
        logger.error(f"Ошибка мониторинга: {e}")


async def crud_operations_example():
    """Пример CRUD операций с SQLAlchemy."""
    print("\n📝 Пример CRUD операций")

    try:
        # Получение сессии БД
        # В реальном приложении используйте Depends(get_async_session)
        print("🔗 Подключение к базе данных...")

        # Пример простых запросов
        queries = [
            "SELECT version() as db_version",
            "SELECT current_database() as current_db",
            "SELECT current_user as current_user",
            "SELECT now() as current_time",
        ]

        print("📊 Выполнение тестовых запросов:")

        # В реальном приложении:
        # async with get_async_session() as session:
        #     for query in queries:
        #         result = await session.execute(text(query))
        #         row = result.fetchone()
        #         print(f"   {query}: {row[0] if row else 'Нет результата'}")

        # Имитация результатов
        mock_results = {
            "SELECT version() as db_version": "PostgreSQL 15.0",
            "SELECT current_database() as current_db": "mango_msg",
            "SELECT current_user as current_user": "postgres",
            "SELECT now() as current_time": datetime.now().isoformat(),
        }

        for query, result in mock_results.items():
            print(f"   {query}: {result}")

        print("✅ CRUD операции выполнены")

    except Exception as e:
        logger.error(f"Ошибка CRUD операций: {e}")


async def database_health_check_example():
    """Пример проверки здоровья базы данных."""
    print("\n🏥 Пример проверки здоровья БД")

    try:
        health_checks = [
            {
                "name": "Подключение к БД",
                "status": "healthy",
                "response_time": "15ms",
                "details": "Соединение установлено успешно",
            },
            {"name": "Размер БД", "status": "healthy", "size": "45.2 MB", "details": "Размер в пределах нормы"},
            {"name": "Активные соединения", "status": "healthy", "connections": "5/100", "details": "Низкая нагрузка"},
            {
                "name": "Последняя миграция",
                "status": "healthy",
                "last_migration": "2024-12-19 10:30:00",
                "details": "Миграции актуальны",
            },
            {"name": "Индексы", "status": "healthy", "unused_indexes": 0, "details": "Все индексы используются"},
        ]

        print("🔍 Результаты проверки здоровья:")

        for check in health_checks:
            status_icon = "✅" if check["status"] == "healthy" else "❌"
            print(f"\n   {status_icon} {check['name']}")
            print(f"      Статус: {check['status']}")

            # Дополнительные поля
            for key, value in check.items():
                if key not in ["name", "status", "details"]:
                    print(f"      {key.title()}: {value}")

            print(f"      Детали: {check['details']}")

        # Общий статус
        all_healthy = all(check["status"] == "healthy" for check in health_checks)
        overall_status = "✅ Здоровая" if all_healthy else "❌ Требует внимания"
        print(f"\n🏥 Общий статус БД: {overall_status}")

    except Exception as e:
        logger.error(f"Ошибка проверки здоровья: {e}")


async def database_optimization_example():
    """Пример оптимизации базы данных."""
    print("\n⚡ Пример оптимизации БД")

    try:
        optimization_tasks = [
            {
                "task": "VACUUM ANALYZE",
                "description": "Очистка и обновление статистики",
                "estimated_time": "2-5 минут",
                "impact": "Улучшение производительности запросов",
            },
            {
                "task": "REINDEX",
                "description": "Перестроение индексов",
                "estimated_time": "5-10 минут",
                "impact": "Ускорение поиска и сортировки",
            },
            {
                "task": "Анализ медленных запросов",
                "description": "Поиск неоптимальных запросов",
                "estimated_time": "1-2 минуты",
                "impact": "Выявление узких мест",
            },
            {
                "task": "Проверка неиспользуемых индексов",
                "description": "Поиск избыточных индексов",
                "estimated_time": "30 секунд",
                "impact": "Экономия места и ускорение записи",
            },
        ]

        print("🔧 Доступные задачи оптимизации:")

        for i, task in enumerate(optimization_tasks, 1):
            print(f"\n   {i}. {task['task']}")
            print(f"      📝 {task['description']}")
            print(f"      ⏱️ Время: {task['estimated_time']}")
            print(f"      📈 Эффект: {task['impact']}")

        # Имитация выполнения оптимизации
        print("\n🚀 Выполнение оптимизации...")

        for task in optimization_tasks:
            print(f"   ⏳ Выполняется: {task['task']}...")
            await asyncio.sleep(0.5)  # Имитация времени выполнения
            print(f"   ✅ Завершено: {task['task']}")

        print("\n⚡ Оптимизация завершена успешно!")

        # Результаты оптимизации
        results = {
            "queries_optimized": 15,
            "indexes_rebuilt": 8,
            "space_freed": "12.5 MB",
            "performance_improvement": "25%",
        }

        print("\n📊 Результаты оптимизации:")
        for metric, value in results.items():
            print(f"   {metric.replace('_', ' ').title()}: {value}")

    except Exception as e:
        logger.error(f"Ошибка оптимизации: {e}")


async def database_cli_examples():
    """Примеры использования CLI команд для БД."""
    print("\n💻 Примеры CLI команд для БД")

    cli_commands = [
        {
            "command": "make db-info",
            "description": "Получение информации о базе данных",
            "example_output": "База данных: mango_msg, Размер: 45.2 MB, Таблиц: 8",
        },
        {
            "command": "make db-create",
            "description": "Создание новой базы данных",
            "example_output": "✅ База данных создана успешно",
        },
        {
            "command": "make db-ensure",
            "description": "Проверка/создание БД автоматически",
            "example_output": "✅ База данных готова к использованию",
        },
        {
            "command": "make db-test",
            "description": "Тестирование подключения к БД",
            "example_output": "✅ Подключение к БД успешно",
        },
        {
            "command": "make migrate-safe",
            "description": "Безопасное применение миграций",
            "example_output": "✅ Миграции применены успешно",
        },
        {
            "command": "make migrate-status",
            "description": "Статус миграций",
            "example_output": "Текущая версия: abc123, Ожидающих: 0",
        },
        {
            "command": "make migrate-create MSG='Add user table'",
            "description": "Создание новой миграции",
            "example_output": "Создана миграция: 20241219_add_user_table.py",
        },
        {
            "command": "make migrate-monitor",
            "description": "Мониторинг состояния миграций",
            "example_output": "📊 Детальный отчет о состоянии БД",
        },
    ]

    print("🔧 Доступные CLI команды:")

    for cmd in cli_commands:
        print(f"\n   💻 {cmd['command']}")
        print(f"      📝 {cmd['description']}")
        print(f"      📤 Пример вывода: {cmd['example_output']}")

    print("\n💡 Рекомендуемый порядок для нового проекта:")
    recommended_order = ["make db-ensure", "make migrate-safe", "make db-info", "make migrate-status"]

    for i, cmd in enumerate(recommended_order, 1):
        print(f"   {i}. {cmd}")


async def main():
    """Главная функция с запуском всех примеров."""
    print("🎯 Примеры работы с базой данных и миграциями")
    print("=" * 60)

    try:
        # Основные операции с БД
        await database_creation_example()
        await migration_management_example()
        await migration_backup_example()
        await migration_monitoring_example()

        # CRUD операции
        await crud_operations_example()

        # Мониторинг и оптимизация
        await database_health_check_example()
        await database_optimization_example()

        # CLI команды
        await database_cli_examples()

        print("\n🎉 Все примеры выполнены успешно!")

        print("\n💡 Для работы с реальной БД:")
        print("   1. Настройте переменные окружения (POSTGRES_*)")
        print("   2. Запустите PostgreSQL: docker-compose up -d postgres")
        print("   3. Выполните: make db-ensure")
        print("   4. Примените миграции: make migrate-safe")

        print("\n🔧 Полезные команды:")
        print("   make db-info          # Информация о БД")
        print("   make migrate-status   # Статус миграций")
        print("   make migrate-monitor  # Детальный мониторинг")

        print("\n📚 Документация:")
        print("   docs/DATABASE_AUTO_CREATE.md  # Автосоздание БД")
        print("   docs/ALEMBIC_MIGRATION.md     # Миграции")

    except Exception as e:
        logger.error(f"Ошибка выполнения примеров: {e}")
        raise


if __name__ == "__main__":
    # Запуск примеров
    asyncio.run(main())
