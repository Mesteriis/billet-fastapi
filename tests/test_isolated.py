"""Изолированные тесты без глобальных фикстур."""

import os
import sys

# Добавляем src в sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_simple_import():
    """Тест простого импорта."""
    from core.config import get_settings

    settings = get_settings()
    assert settings.PROJECT_NAME == "Mango Message"
    assert settings.VERSION == "1.0.0"


def test_basic_calculation():
    """Базовый тест вычислений."""
    assert 1 + 1 == 2
    assert 5 * 5 == 25


def test_constants_import():
    """Тест импорта констант."""
    from constants import ENV_FILE, PROJECT_DIR

    assert PROJECT_DIR is not None
    assert ENV_FILE is not None
