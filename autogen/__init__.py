"""
Autogen - Enterprise-grade FastAPI application generator.

This package provides tools for creating FastAPI applications with different levels:
- BasicCRUD: Simple CRUD operations with FastAPI Depends DI
- Advanced: + Advanced filtering, search, aggregations with auto-registration DI
- Enterprise: + Caching, bulk operations, events, Unit of Work, full DI container

Features:
- 🎯 Typer-based CLI with rich UI and interactive mode
- 🛡️ Version control for templates with safe migration strategies
- 🔧 Bulletproof custom template validation
- 📊 Automatic integration with logging, monitoring, and telemetry
- ⚡ Production-ready async-first DI container
"""

__version__ = "0.1.0"
__author__ = "Alexander Mescheryakov"

from .cli.main import app as cli_app
from .core.generators import AppGenerator
from .core.validators import TemplateValidator
from .utils import (
    generate_model_name,
    get_app_config,
    snake_case_to_camel_case,
    snake_case_to_pascal_case,
    update_pyproject_config,
    validate_app_name,
)

__all__ = [
    "cli_app",
    "AppGenerator",
    "TemplateValidator",
    "get_app_config",
    "update_pyproject_config",
    "validate_app_name",
    "generate_model_name",
    "snake_case_to_pascal_case",
    "snake_case_to_camel_case",
]
