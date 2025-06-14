#!/bin/bash
# Проверка TODO/FIXME комментариев в staged файлах

set -e

# Получаем список staged файлов
staged_files=$(git diff --cached --name-only || true)

if [ -n "$staged_files" ]; then
    # Ищем TODO/FIXME комментарии
    todo_files=$(echo "$staged_files" | xargs grep -l "TODO\|FIXME\|XXX\|HACK" 2>/dev/null || true)
    
    if [ -n "$todo_files" ]; then
        echo "⚠️  WARNING: Found TODO/FIXME comments in staged files:"
        echo "$todo_files"
        echo ""
        echo "Если это намеренно, используйте: SKIP=check-todos git commit"
        exit 1
    else
        echo "✅ Нет TODO/FIXME комментариев в staged файлах"
    fi
else
    echo "✅ Нет staged файлов для проверки"
fi 