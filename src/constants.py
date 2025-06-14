"""Константы проекта для конфигурации путей."""

from __future__ import annotations

from pathlib import Path

PROJECT_DIR: Path = Path(__file__).resolve().parent

ENV_FILE: Path = PROJECT_DIR / ".env"
# while True:
#     if ENV_FILE.exists():
#         break
#     ENV_FILE = ENV_FILE.parent / ".env"
#     if ENV_FILE.parent == PROJECT_DIR.parent:
#         raise FileNotFoundError(".env file not found in the project directory or its parents.")

APPS_DIR: Path = PROJECT_DIR / "src" / "apps"
