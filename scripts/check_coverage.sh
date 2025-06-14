#!/bin/bash
# Проверка покрытия только для измененных Python файлов

set -e

# Получаем список измененных Python файлов (исключая тесты)
changed_files=$(git diff --cached --name-only --diff-filter=AM | grep -E "\.py$" | grep -v __pycache__ | grep -v test_ || true)

if [ -n "$changed_files" ]; then
    echo "🔍 Проверка покрытия для измененных файлов:"
    echo "$changed_files"
    
    # Запускаем pytest с покрытием только для измененных модулей
    uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80 -q
else
    echo "✅ Нет измененных Python файлов для проверки покрытия"
fi 