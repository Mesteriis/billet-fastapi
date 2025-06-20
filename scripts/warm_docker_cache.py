#!/usr/bin/env python3
"""
Скрипт для прогрева Docker кэша.
Загружает необходимые образы заранее для ускорения тестов.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> bool:
    """Выполняет команду и возвращает True если успешно."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ {' '.join(cmd)} - успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {' '.join(cmd)} - ошибка: {e.stderr}")
        return False


def warm_docker_cache():
    """Прогревает Docker кэш для тестов."""
    print("🔥 Прогрев Docker кэша для тестов...")

    # Образы для предварительной загрузки
    images = [
        "postgres:15-alpine",
        "postgres:latest",
        "testcontainers/ryuk:0.8.1",
        # "redis:7-alpine",  # Если понадобится для Redis тестов
        # "rabbitmq:3-management-alpine",  # Если понадобится для RabbitMQ тестов
    ]

    success_count = 0

    for image in images:
        print(f"📦 Загружаем образ: {image}")
        if run_command(["docker", "pull", image]):
            success_count += 1

    print(f"\n🎯 Прогрев завершен: {success_count}/{len(images)} образов загружено")

    # Дополнительно: создаем и останавливаем контейнер для кэширования слоев
    print("\n🚀 Тестируем запуск PostgreSQL контейнера...")

    try:
        # Запускаем тестовый контейнер
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-d",
                "--name",
                "test-pg-warmup",
                "-e",
                "POSTGRES_PASSWORD=test",
                "-e",
                "POSTGRES_DB=test",
                "-e",
                "POSTGRES_USER=test",
                "postgres:15-alpine",
            ],
            check=True,
            capture_output=True,
        )

        # Ждем немного и останавливаем
        import time

        time.sleep(3)

        subprocess.run(["docker", "stop", "test-pg-warmup"], check=True, capture_output=True)

        print("✅ Тестовый контейнер PostgreSQL успешно запущен и остановлен")

    except subprocess.CalledProcessError as e:
        print(f"⚠️ Не удалось протестировать контейнер: {e}")

    print("\n🎉 Docker кэш готов для быстрых тестов!")


def check_docker():
    """Проверяет доступность Docker."""
    try:
        subprocess.run(["docker", "version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker не найден или не запущен")
        return False


if __name__ == "__main__":
    if not check_docker():
        sys.exit(1)

    warm_docker_cache()
