"""
Application generators.

This module provides the main AppGenerator class for creating FastAPI applications.
"""

import shutil
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from autogen.utils import generate_model_name


@dataclass
class GenerationConfig:
    """Configuration for application generation."""

    app_name: str = ""
    model_name: str = ""
    table_name: str = ""
    level: str = "BasicCRUD"
    features: Dict[str, bool] = field(default_factory=dict)
    api_config: Dict[str, Any] = field(default_factory=dict)
    testing_config: Dict[str, Any] = field(default_factory=dict)
    database_config: Dict[str, Any] = field(default_factory=dict)
    version: str = "v1"  # Always v1 for now

    @classmethod
    def from_toml_file(cls, config_path: Path, version: str | None = None) -> "GenerationConfig":
        """Load configuration from TOML file."""
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        # Always use v1 (simplified)
        template_version = version or "v1"

        # Extract app config
        app_config = data.get("app", {})

        return cls(
            app_name=app_config.get("name", "unknown"),
            level=app_config.get("level", "BasicCRUD"),
            model_name=generate_model_name(app_config.get("name", "unknown")),
            table_name=data["database"]["table_name"],
            features=data.get("features", {}),
            api_config=data.get("api", {}),
            testing_config=data.get("testing", {}),
            database_config=data.get("database", {}),
            version=template_version,
        )


class AppGenerator:
    """
    Main application generator (v1.0.0 Complete).

    Generates FastAPI applications with different complexity levels:
    - BasicCRUD: Simple CRUD with FastAPI Depends
    - Advanced: + Filtering, search, aggregations, monitoring
    - Enterprise: + Caching, events, monitoring, performance tracking

    Single version approach (v1) with full feature set.
    """

    def __init__(self, template_dir: str = ""):
        """Initialize generator with template directory."""
        self.template_dir = Path(template_dir) if template_dir else self._get_default_template_dir()
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)), autoescape=select_autoescape(["html", "xml"])
        )

    def generate_app(
        self, config: GenerationConfig, dry_run: bool = False, overwrite: bool = False, backup: bool = False
    ) -> Dict[str, Any]:
        """
        Generate complete application.

        Args:
            config: Generation configuration
            dry_run: Only show what would be generated
            overwrite: Overwrite existing files
            backup: Create backup before changes

        Returns:
            Dictionary with generation results
        """
        if dry_run:
            return self._dry_run_generation(config)

        return self._full_generation(config, overwrite, backup)

    def _full_generation(
        self, config: GenerationConfig, overwrite: bool = False, backup: bool = False
    ) -> Dict[str, Any]:
        """Perform full application generation."""
        app_dir = Path(f"src/apps/{config.app_name}")
        results = {
            "status": "success",
            "app_name": config.app_name,
            "level": config.level,
            "version": config.version,
            "files_created": [],
            "files_skipped": [],
            "errors": [],
        }

        try:
            # Create application directory structure
            self._create_directory_structure(app_dir, config.level)

            # Get template context
            template_context = self._build_template_context(config)

            # Generate files based on level (always v1)
            file_mappings = self._get_file_mappings(config.level)

            for template_path, output_path in file_mappings.items():
                try:
                    # Format output path with app name
                    formatted_output = output_path.format(app_name=config.app_name)
                    full_output_path = app_dir / formatted_output

                    # Check if file exists
                    if full_output_path.exists() and not overwrite:
                        results["files_skipped"].append(str(full_output_path))
                        continue

                    # Create backup if requested
                    if backup and full_output_path.exists():
                        backup_path = full_output_path.with_suffix(
                            f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        )
                        shutil.copy2(full_output_path, backup_path)

                    # Render template and write file
                    self._render_template_to_file(template_path, full_output_path, template_context)
                    results["files_created"].append(str(full_output_path))

                except Exception as e:
                    error_msg = f"Failed to generate {output_path}: {str(e)}"
                    results["errors"].append(error_msg)
                    results["status"] = "partial_success" if results["files_created"] else "failed"

        except Exception as e:
            results["status"] = "failed"
            results["errors"].append(f"Generation failed: {str(e)}")

        return results

    def _create_directory_structure(self, app_dir: Path, level: str):
        """Create the application directory structure."""
        directories = [
            "",  # Root app directory
            "models",
            "schemas",
            "repo",
            "services",
            "api",
            "depends",
        ]

        # Add level-specific directories
        if level in ["Advanced", "Enterprise"]:
            directories.extend(["middleware"])

        if level == "Enterprise":
            directories.extend(["cache", "events"])

        # Create all directories
        for dir_name in directories:
            (app_dir / dir_name).mkdir(parents=True, exist_ok=True)

        # Create __init__.py files
        for dir_name in directories:
            if dir_name:  # Skip root directory
                init_file = app_dir / dir_name / "__init__.py"
                if not init_file.exists():
                    init_file.write_text(f"# Auto-generated __init__.py (v1.0.0 Complete)\n")

    def _build_template_context(self, config: GenerationConfig) -> Dict[str, Any]:
        """Build template context for Jinja2 rendering."""
        return {
            "app_name": config.app_name,
            "model_name": config.model_name,
            "level": config.level,
            "version": config.version,
            "table_name": config.table_name,
            "features": config.features,
            "api_config": config.api_config,
            "testing_config": config.testing_config,
            "database_config": config.database_config,
            "timestamp": datetime.now().isoformat(),
        }

    def _get_file_mappings(self, level: str) -> Dict[str, str]:
        """Get mapping of template files to output files for given level (always v1)."""
        level_dir = level.lower().replace("crud", "_crud")  # BasicCRUD -> basic_crud
        version_path = f"v1/{level_dir}"  # Always v1

        base_mappings = {
            f"{version_path}/models.py.j2": "models/{app_name}_models.py",
            f"{version_path}/schemas.py.j2": "schemas/{app_name}_schemas.py",
            f"{version_path}/repository.py.j2": "repo/{app_name}_repo.py",
            f"{version_path}/service.py.j2": "services/{app_name}_service.py",
            f"{version_path}/api.py.j2": "api/{app_name}_routes.py",
            f"{version_path}/exceptions.py.j2": "exceptions.py",
            f"{version_path}/depends.py.j2": "depends/dependencies.py",
            f"{version_path}/__init__.py.j2": "__init__.py",
            f"{version_path}/tests/test_api.py.j2": "tests/test_{app_name}_api.py",
        }

        # Add factories for BasicCRUD
        if level == "BasicCRUD":
            base_mappings[f"{version_path}/tests/factories.py.j2"] = "tests/factories.py"

        # Advanced level files
        if level in ["Advanced", "Enterprise"]:
            base_mappings.update(
                {
                    f"{version_path}/middleware/logging_middleware.py.j2": "middleware/{app_name}_middleware.py",
                    f"{version_path}/middleware/monitoring_middleware.py.j2": "middleware/{app_name}_monitoring_middleware.py",
                    f"{version_path}/health.py.j2": "health.py",
                    f"{version_path}/tests/test_monitoring.py.j2": "tests/test_{app_name}_monitoring.py",
                }
            )

        # Enterprise level files
        if level == "Enterprise":
            base_mappings.update(
                {
                    f"{version_path}/cache_service.py.j2": "services/{app_name}_cache_service.py",
                    f"{version_path}/event_service.py.j2": "services/{app_name}_event_service.py",
                    f"{version_path}/monitoring_service.py.j2": "services/{app_name}_monitoring_service.py",
                    f"{version_path}/health_service.py.j2": "services/{app_name}_health_service.py",
                    f"{version_path}/middleware/performance_middleware.py.j2": "middleware/{app_name}_performance_middleware.py",
                    f"{version_path}/tests/test_cache.py.j2": "tests/test_{app_name}_cache.py",
                    f"{version_path}/tests/test_events.py.j2": "tests/test_{app_name}_events.py",
                    f"{version_path}/tests/test_performance.py.j2": "tests/test_{app_name}_performance.py",
                }
            )

        return base_mappings

    def _render_template_to_file(self, template_path: str, output_path: Path, context: Dict[str, Any]):
        """Render a Jinja2 template to file."""
        template = self.jinja_env.get_template(template_path)
        rendered_content = template.render(**context)

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write rendered content
        output_path.write_text(rendered_content, encoding="utf-8")

    def _dry_run_generation(self, config: GenerationConfig) -> Dict[str, Any]:
        """Show what would be generated without creating files."""
        file_mappings = self._get_file_mappings(config.level)
        files_to_generate = []

        for template_path, output_path in file_mappings.items():
            formatted_output = output_path.format(app_name=config.app_name)
            full_path = f"src/apps/{config.app_name}/{formatted_output}"
            files_to_generate.append(
                {"template": template_path, "output": full_path, "exists": Path(full_path).exists()}
            )

        return {
            "status": "dry_run",
            "app_name": config.app_name,
            "level": config.level,
            "version": config.version,
            "model_name": config.model_name,
            "files_to_generate": files_to_generate,
            "template_dir": str(self.template_dir),
            "features": config.features,
            "api_config": config.api_config,
        }

    def get_version_info(self) -> Dict[str, Any]:
        """Get version metadata from version.toml file."""
        version_file = self.template_dir / "v1" / "version.toml"
        if not version_file.exists():
            return {"error": "Version metadata not found"}

        try:
            with open(version_file, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            return {"error": f"Failed to read version metadata: {e}"}

    def _get_default_template_dir(self) -> Path:
        """Get default template directory."""
        # Look for templates in the autogen package
        current_dir = Path(__file__).parent.parent
        return current_dir / "templates"

    def generate_test_factories(
        self, config: GenerationConfig, dry_run: bool = False, overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Generate test factories for the application.

        Args:
            config: Generation configuration
            dry_run: Only show what would be generated
            overwrite: Overwrite existing files

        Returns:
            Dictionary with generation results
        """
        if dry_run:
            return self._dry_run_test_generation(config)

        return self._generate_test_components(config, overwrite)

    def _generate_test_components(self, config: GenerationConfig, overwrite: bool = False) -> Dict[str, Any]:
        """Generate test factories and fixtures."""
        app_dir = Path(f"src/apps/{config.app_name}")
        results = {
            "status": "success",
            "app_name": config.app_name,
            "factories_created": [],
            "fixtures_created": [],
            "errors": [],
        }

        try:
            # Ensure tests directory exists
            tests_dir = app_dir / "tests"
            tests_dir.mkdir(exist_ok=True)

            # Generate factories
            factory_file = tests_dir / "factories.py"
            if not factory_file.exists() or overwrite:
                factory_content = self._generate_factory_content(config)
                factory_file.write_text(factory_content, encoding="utf-8")
                results["factories_created"].append(str(factory_file))

            # Generate fixtures
            fixtures_file = tests_dir / "fixtures.py"
            if not fixtures_file.exists() or overwrite:
                fixtures_content = self._generate_fixtures_content(config)
                fixtures_file.write_text(fixtures_content, encoding="utf-8")
                results["fixtures_created"].append(str(fixtures_file))

            # Generate conftest.py
            conftest_file = tests_dir / "conftest.py"
            if not conftest_file.exists() or overwrite:
                conftest_content = self._generate_conftest_content(config)
                conftest_file.write_text(conftest_content, encoding="utf-8")
                results["fixtures_created"].append(str(conftest_file))

        except Exception as e:
            results["status"] = "failed"
            results["errors"].append(f"Factory generation failed: {str(e)}")

        return results

    def _generate_factory_content(self, config: GenerationConfig) -> str:
        """Generate factory content based on model."""
        model_name = config.model_name
        app_name = config.app_name

        return f'''"""
Test factories for {model_name}.

Auto-generated by Autogen CLI.
"""

import factory
from async_factory_boy.factory.sqlalchemy import AsyncSQLAlchemyFactory
from tests.factories.base_factories import BaseTestFactory, TestDataGenerator

from src.apps.{app_name}.models.{app_name}_models import {model_name}


class {model_name}Factory(BaseTestFactory):
    """Factory for {model_name} model."""
    
    class Meta:
        model = {model_name}
        sqlalchemy_session_persistence = "commit"

    # Auto-generated fields based on model analysis
    # These should be customized based on your specific model fields
    
    # Example fields - customize based on your model
    # name = factory.Faker("name")
    # email = factory.LazyFunction(TestDataGenerator.unique_email)
    # username = factory.LazyFunction(TestDataGenerator.unique_username)
    # phone = factory.LazyFunction(TestDataGenerator.random_phone)
    # description = factory.LazyFunction(lambda: TestDataGenerator.random_text(100))
    
    @factory.post_generation
    def set_defaults(obj, create, extracted, **kwargs):
        """Set default values after creation."""
        if not create:
            return
            
        # Add any post-generation logic here
        pass


class {model_name}CreateFactory({model_name}Factory):
    """Factory for creating {model_name} with minimal required fields."""
    
    class Meta:
        model = {model_name}
        
    # Override fields for creation scenario
    pass


class {model_name}UpdateFactory(factory.DictFactory):
    """Factory for {model_name} update data."""
    
    # Fields for update operations
    # name = factory.Faker("name")
    pass


# Convenience functions
async def create_{app_name}(**kwargs):
    """Create a {model_name} instance with factory."""
    return await {model_name}Factory.create(**kwargs)


async def build_{app_name}(**kwargs):
    """Build a {model_name} instance without saving."""
    return await {model_name}Factory.build(**kwargs)


async def create_{app_name}_batch(size: int = 5, **kwargs):
    """Create multiple {model_name} instances."""
    return await {model_name}Factory.create_batch(size, **kwargs)
'''

    def _generate_fixtures_content(self, config: GenerationConfig) -> str:
        """Generate fixtures content."""
        model_name = config.model_name
        app_name = config.app_name

        return f'''"""
Test fixtures for {model_name}.

Auto-generated by Autogen CLI.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.base_factories import setup_factory_session
from src.apps.{app_name}.models.{app_name}_models import {model_name}
from .factories import {model_name}Factory, create_{app_name}, create_{app_name}_batch


@pytest_asyncio.fixture
async def {app_name}_factory(db_session: AsyncSession):
    """Fixture providing configured {model_name}Factory."""
    setup_factory_session({model_name}Factory, db_session)
    return {model_name}Factory


@pytest_asyncio.fixture
async def {app_name}_instance(db_session: AsyncSession):
    """Fixture providing a single {model_name} instance."""
    setup_factory_session({model_name}Factory, db_session)
    return await create_{app_name}()


@pytest_asyncio.fixture
async def {app_name}_instances(db_session: AsyncSession):
    """Fixture providing multiple {model_name} instances."""
    setup_factory_session({model_name}Factory, db_session)
    return await create_{app_name}_batch(5)


@pytest_asyncio.fixture
async def {app_name}_data():
    """Fixture providing sample {model_name} data for testing."""
    return {{
        # Add sample data fields based on your model
        # "name": "Test Name",
        # "email": "test@example.com",
        # "username": "testuser",
    }}


@pytest.fixture
def {app_name}_create_data():
    """Fixture providing data for {model_name} creation."""
    return {{
        # Add required fields for creation
        # "name": "New Test Name",
        # "email": "new@example.com",
    }}


@pytest.fixture
def {app_name}_update_data():
    """Fixture providing data for {model_name} updates."""
    return {{
        # Add fields that can be updated
        # "name": "Updated Name",
        # "description": "Updated description",
    }}


@pytest.fixture
def invalid_{app_name}_data():
    """Fixture providing invalid data for error testing."""
    return {{
        # Add invalid data that should trigger validation errors
        # "email": "invalid-email",
        # "name": "",  # Empty required field
    }}
'''

    def _generate_conftest_content(self, config: GenerationConfig) -> str:
        """Generate conftest.py content for the app."""
        app_name = config.app_name

        return f'''"""
Pytest configuration for {app_name} app tests.

Auto-generated by Autogen CLI.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    db_session,
    test_client,
    test_user,
    auth_headers,
)
from tests.factories.base_factories import reset_factories


@pytest_asyncio.fixture(autouse=True)
async def setup_test_environment():
    """Setup test environment for each test."""
    # Reset factories before each test
    await reset_factories()
    
    yield
    
    # Cleanup after each test if needed
    pass


@pytest.fixture
def app_name():
    """Fixture providing app name for tests."""
    return "{app_name}"


# Import fixtures from the main fixtures module
pytest_plugins = [
    "tests.apps.{app_name}.tests.fixtures",
]
'''

    def _dry_run_test_generation(self, config: GenerationConfig) -> Dict[str, Any]:
        """Show what test components would be generated."""
        app_name = config.app_name
        tests_dir = f"src/apps/{app_name}/tests"

        files_to_generate = [
            {
                "file": f"{tests_dir}/factories.py",
                "description": f"Test factories for {config.model_name}",
                "exists": Path(f"{tests_dir}/factories.py").exists(),
            },
            {
                "file": f"{tests_dir}/fixtures.py",
                "description": f"Test fixtures for {config.model_name}",
                "exists": Path(f"{tests_dir}/fixtures.py").exists(),
            },
            {
                "file": f"{tests_dir}/conftest.py",
                "description": f"Pytest configuration for {app_name}",
                "exists": Path(f"{tests_dir}/conftest.py").exists(),
            },
        ]

        return {
            "status": "dry_run",
            "app_name": app_name,
            "model_name": config.model_name,
            "files_to_generate": files_to_generate,
        }
