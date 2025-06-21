"""Pydantic Utilities and Safe Model Wrappers.

This module provides enhanced Pydantic models and settings with:
- Rich error formatting in development mode
- Graceful error handling with exit codes
- Debug mode integration with environment variables
- Rich console output for validation errors
- SafeModel and SafeSettings wrappers

Features:
    - Automatic debug mode detection from environment
    - Pytest integration for test environments
    - Rich-formatted validation error display
    - Safe model validation with graceful exits
    - Settings validation with environment variables

Example:
    Basic SafeModel usage::

        from tools.pydantic import SafeModel
        from pydantic import Field

        class UserModel(SafeModel):
            username: str = Field(min_length=3, max_length=50)
            email: str = Field(regex=r'^[^@]+@[^@]+\.[^@]+$')
            age: int = Field(ge=0, le=120)

        # Will show rich error formatting in DEBUG mode
        try:
            user = UserModel(username="ab", email="invalid", age=-1)
        except ValidationError:
            # Errors are nicely formatted with Rich if available
            pass

    SafeSettings for configuration::

        from tools.pydantic import SafeSettings

        class AppSettings(SafeSettings):
            database_url: str
            redis_url: str = "redis://localhost"
            debug: bool = False

            class Config:
                env_file = ".env"

        settings = AppSettings()  # Auto-loads from environment

    Debug mode features::

        import os
        os.environ["DEBUG"] = "true"

        # Now validation errors show:
        # - Rich-formatted tables
        # - Full traceback information
        # - Field-specific error details

Note:
    The module automatically detects pytest environment and DEBUG mode.
    Rich formatting is only available if the 'rich' package is installed.
    In production (DEBUG=false), validation errors cause clean exits.
"""

import os
import sys
import traceback
from typing import Any, TypeVar

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ValidationError
from pydantic_settings import BaseSettings as PydanticBaseSettings

DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
"""bool: Debug mode flag from environment variables.

Automatically detects debug mode from DEBUG environment variable.
Accepts: "true", "1", "yes" (case-insensitive) as true values.
"""


def running_under_pytest() -> bool:
    """Check if code is running under pytest.

    Returns:
        bool: True if pytest is detected in sys.modules

    Example:
        Conditional behavior in tests::

            if running_under_pytest():
                # Special test behavior
                raise ValidationError("Test error")
            else:
                # Production behavior
                sys.exit(1)

    Note:
        Used internally to adjust error handling behavior.
        In pytest, validation errors are raised normally.
    """
    return "pytest" in sys.modules


console: "Console | None"
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_ENABLED = True
    console = Console()
except ImportError:
    RICH_ENABLED = False
    console = None

# Rich availability flags and console instance documentation:
# RICH_ENABLED: bool - Whether Rich library is available for formatting
# console: Console | None - Rich console instance if available

T = TypeVar("T", bound="SafeModel")
"""TypeVar: Type variable for SafeModel subclasses."""

S = TypeVar("S", bound="SafeSettings")
"""TypeVar: Type variable for SafeSettings subclasses."""


class SafeModel(PydanticBaseModel):
    """Enhanced Pydantic BaseModel with rich error formatting and safe validation.

    Extends Pydantic's BaseModel with:
    - Rich console error formatting in debug mode
    - Graceful error handling and system exits
    - Pytest-aware validation error handling
    - Environment-based debug mode detection

    The model automatically detects the runtime environment and adjusts
    error handling behavior accordingly:
    - In pytest: Raises ValidationError normally
    - In debug mode: Shows rich error formatting + raises
    - In production: Clean system exit on validation errors

    Example:
        Creating a model with validation::

            class ProductModel(SafeModel):
                name: str = Field(min_length=1, max_length=100)
                price: float = Field(gt=0)
                category: str = Field(regex=r'^[a-zA-Z_]+$')

        Handling validation errors::

            try:
                product = ProductModel(
                    name="",  # Too short
                    price=-10,  # Must be positive
                    category="123invalid"  # Invalid format
                )
            except ValidationError as e:
                # In DEBUG mode, shows rich table with errors
                # In production, exits cleanly
                pass

        Model validation from external data::

            user_data = {"username": "john", "email": "john@example.com"}
            try:
                user = UserModel.model_validate(user_data)
            except ValidationError:
                # Handled according to environment
                pass

    Attributes:
        All standard Pydantic BaseModel attributes and methods are inherited.

    Methods:
        __init__: Enhanced initialization with error handling
        model_validate: Enhanced validation with error handling
        _raise_or_exit: Internal error handling logic
        _print_validation_errors: Rich error formatting (if available)

    Note:
        Rich formatting requires the 'rich' package to be installed.
        Debug mode is controlled by the DEBUG environment variable.
    """

    def __init__(__pydantic_self__, **data: Any) -> None:
        """Initialize model with enhanced error handling.

        Args:
            **data: Model field data

        Raises:
            ValidationError: In pytest environment
            SystemExit: In production with validation errors

        Example:
            Basic initialization::

                user = UserModel(username="john", email="john@example.com")

            Handling validation errors::

                try:
                    user = UserModel(username="", email="invalid")
                except (ValidationError, SystemExit):
                    # Handle according to environment
                    pass
        """
        try:
            super().__init__(**data)
        except ValidationError as e:
            SafeModel._raise_or_exit(e, model_name=__pydantic_self__.__class__.__name__)

    @classmethod
    def model_validate(cls: type[T], obj: Any, **kwargs) -> T:
        """Enhanced model validation with error handling.

        Args:
            obj: Object to validate (dict, model instance, etc.)
            **kwargs: Additional validation arguments

        Returns:
            T: Validated model instance

        Raises:
            ValidationError: In pytest environment
            SystemExit: In production with validation errors

        Example:
            Validating from dictionary::

                data = {"username": "john", "email": "john@example.com"}
                user = UserModel.model_validate(data)

            Validating from another model::

                source_user = SomeOtherUserModel(...)
                our_user = UserModel.model_validate(source_user)

            With additional validation context::

                user = UserModel.model_validate(
                    data,
                    strict=True,
                    context={"user_id": 123}
                )
        """
        try:
            return super().model_validate(obj, **kwargs)
        except ValidationError as e:
            SafeModel._raise_or_exit(e, model_name=cls.__name__)
            # This line will never be reached due to SystemExit, but needed for type checker
            raise

    @staticmethod
    def _raise_or_exit(e: ValidationError, model_name: str = "Model") -> None:
        """Handle validation errors based on environment.

        Args:
            e (ValidationError): The validation error to handle
            model_name (str): Name of the model for error reporting

        Behavior:
            - In pytest: Re-raises the ValidationError
            - In debug mode: Shows traceback and rich formatting
            - In production: Clean system exit

        Note:
            This method never returns normally in non-pytest environments.
        """
        # Стандартный traceback
        if DEBUG:
            traceback.print_exception(type(e), e, e.__traceback__)
            if RICH_ENABLED and console is not None:
                SafeModel._print_validation_errors(e, model_name)

        if running_under_pytest():
            raise e
        raise SystemExit(1)

    @staticmethod
    def _print_validation_errors(e: ValidationError, model_name: str = "Model") -> None:
        """Print rich-formatted validation errors.

        Args:
            e (ValidationError): The validation error to format
            model_name (str): Name of the model for display

        Example:
            The output shows a formatted table like::

                ❌ Validation Error in UserModel
                ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
                ┃                                   Field                                   Message    ┃
                ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
                │ username                          String should have at least 3 characters     │
                │ email                            Invalid email format                           │
                │ age                              Input should be greater than or equal to 0     │
                └──────────────────────────────────────────────────────────────────────────────────────┘

        Note:
            Only works if Rich is installed and available.
        """
        if not RICH_ENABLED or console is None:
            return

        tb = traceback.extract_tb(e.__traceback__)
        file_info = tb[-1] if tb else None

        table = Table(
            title=f"❌ Validation Error in [bold yellow]{model_name}[/]",
            show_header=True,
            header_style="bold red",
        )
        table.add_column("Field", style="bold")
        table.add_column("Message", style="dim")

        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            msg = err["msg"]
            table.add_row(loc, msg)

        console.print(table)


class SafeSettings(PydanticBaseSettings):
    """Enhanced Pydantic BaseSettings with rich error formatting.

    Extends Pydantic's BaseSettings with the same error handling
    improvements as SafeModel, specifically for configuration settings.

    Automatically loads settings from:
    - Environment variables
    - .env files
    - Default values
    - Constructor arguments

    Example:
        Application settings::

            class DatabaseSettings(SafeSettings):
                host: str = "localhost"
                port: int = 5432
                username: str
                password: str
                database: str

                class Config:
                    env_prefix = "DB_"
                    env_file = ".env"

        Loading from environment::

            # Environment variables: DB_HOST, DB_PORT, etc.
            # Or .env file with same variables
            settings = DatabaseSettings()

        Override with constructor::

            settings = DatabaseSettings(
                host="production-db.example.com",
                port=5433
            )

        Complex configuration::

            class AppSettings(SafeSettings):
                # Database
                database_url: str
                database_pool_size: int = 10

                # Redis
                redis_url: str = "redis://localhost"

                # API
                secret_key: str
                cors_origins: list[str] = []

                class Config:
                    env_file = ".env"
                    env_nested_delimiter = "__"

    Note:
        Same error handling behavior as SafeModel applies here.
        Environment variables take precedence over default values.
    """

    def __init__(__pydantic_self__, **data: Any) -> None:
        """Initialize settings with enhanced error handling.

        Args:
            **data: Override settings data

        Raises:
            ValidationError: In pytest environment
            SystemExit: In production with validation errors

        Example:
            Loading from environment::

                settings = AppSettings()  # Uses env vars and .env

            With overrides::

                settings = AppSettings(debug=True, log_level="DEBUG")
        """
        try:
            super().__init__(**data)
        except ValidationError as e:
            SafeModel._raise_or_exit(e, model_name=__pydantic_self__.__class__.__name__)

    @classmethod
    def model_validate(cls: type[S], obj: Any, **kwargs) -> S:
        """Enhanced settings validation with error handling.

        Args:
            obj: Object to validate
            **kwargs: Additional validation arguments

        Returns:
            S: Validated settings instance

        Raises:
            ValidationError: In pytest environment
            SystemExit: In production with validation errors

        Example:
            From dictionary::

                config_dict = {"database_url": "...", "redis_url": "..."}
                settings = AppSettings.model_validate(config_dict)

            From external source::

                external_config = load_config_from_consul()
                settings = AppSettings.model_validate(external_config)
        """
        try:
            return super().model_validate(obj, **kwargs)
        except ValidationError as e:
            SafeModel._raise_or_exit(e, model_name=cls.__name__)
            # This line will never be reached due to SystemExit, but needed for type checker
            raise


# Алиасы
BaseModel = SafeModel
BaseSettings = SafeSettings
