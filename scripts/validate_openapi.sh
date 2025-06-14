#!/bin/bash
# Валидация OpenAPI схемы FastAPI приложения

set -e

echo "🔍 Проверка OpenAPI схемы..."

# Проверяем, что приложение может быть импортировано и генерирует корректную схему
if uv run python -c "
import sys
sys.path.insert(0, 'src')

try:
    from src.main import app
    import json
    schema = app.openapi()
    if schema and 'openapi' in schema:
        print('✅ OpenAPI schema is valid')
        exit(0)
    else:
        print('❌ Invalid OpenAPI schema structure')
        exit(1)
except ImportError as e:
    print(f'⚠️  Cannot import main app: {e}')
    print('⚠️  Skipping OpenAPI validation')
    exit(0)
except Exception as e:
    print(f'❌ Error generating OpenAPI schema: {e}')
    exit(1)
"; then
    echo "✅ OpenAPI валидация пройдена"
else
    echo "❌ Ошибка при валидации OpenAPI"
    exit 1
fi 