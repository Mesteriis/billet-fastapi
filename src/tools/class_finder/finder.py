"""Dynamic Python Class Discovery and Import Utilities.

This module provides utilities for discovering and dynamically importing Python classes
from specified directories. It's designed for plugin systems, module discovery,
and dynamic class loading scenarios.

Features:
    - Recursive Python file discovery with filtering
    - Dynamic class discovery based on inheritance patterns
    - Safe module importing with sys.path management
    - Comprehensive error handling and logging
    - Import statement generation for discovered classes
    - Colored console output for import status reporting

Components:
    - ClassFinder: Main class for discovery and import operations
    - ClassFinderError: Base exception for error handling
    - ModuleImportError: Specific exception for import failures

Example:
    Basic class discovery::

        from pathlib import Path
        from tools.class_finder.finder import ClassFinder

        # Find all classes inheriting from BaseModel
        finder = ClassFinder(
            directory=Path("src/models"),
            find_sub_class=BaseModel,
            target_file_name="models"
        )

        # Discover classes
        classes = finder.find_all_classes()
        print(f"Found {len(classes)} model files")

    Dynamic import workflow::

        # Generate import statements
        imports = finder.generate_import_statements(classes)

        # Perform dynamic imports with status reporting
        finder.run()  # Shows colored status output

    Plugin discovery system::

        from tools.class_finder.finder import ClassFinder

        class BasePlugin:
            def execute(self): pass

        # Find all plugins
        plugin_finder = ClassFinder(
            directory=Path("plugins"),
            find_sub_class=BasePlugin,
            target_file_name="plugin"
        )

        # Load plugins dynamically
        plugins = plugin_finder.find_all_classes()
        for plugin_class in plugins:
            # Instantiate and use plugin
            pass

Note:
    The ClassFinder manages sys.path modifications safely using context managers
    to avoid pollution of the Python import system. All operations include
    comprehensive error handling and detailed logging.
"""

import importlib
import logging
import logging.config
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from core.exceptions.core_base import CoreToolsTypeError


class ClassFinderError(Exception):
    """Base exception for ClassFinder operations.

    Raised when general ClassFinder operations fail, such as validation
    errors, configuration issues, or unexpected runtime conditions.

    Example:
        Catching ClassFinder errors::

            try:
                finder = ClassFinder(invalid_params)
            except ClassFinderError as e:
                logger.error(f"ClassFinder setup failed: {e}")
    """


class ModuleImportError(ClassFinderError):
    """Exception raised when module import operations fail.

    Raised specifically when dynamic module imports fail during
    class discovery or validation operations.

    Example:
        Handling import errors::

            try:
                classes = finder.find_classes_in_file(file_path)
            except ModuleImportError as e:
                logger.warning(f"Failed to import module: {e}")
                # Continue with other files
    """


class ClassFinder:
    """Dynamic Python class discovery and import utility.

    Discovers Python classes based on inheritance patterns within specified
    directories. Provides safe dynamic importing with comprehensive error
    handling and detailed status reporting.

    The ClassFinder recursively searches Python files, discovers classes
    that inherit from a specified base class, and can dynamically import
    them with full error reporting and logging.

    Attributes:
        directory (Path): Directory to search for Python files
        find_sub_class (type): Base class to find subclasses of
        target_file_name (str): File name filter for discovery
        work_dir (Path | None): Working directory for sys.path management
        logger (logging.Logger): Logger instance for operation tracking

    Example:
        Basic usage for model discovery::

            from pathlib import Path
            from sqlalchemy import DeclarativeBase

            # Set up class discovery
            finder = ClassFinder(
                directory=Path("src/models"),
                find_sub_class=DeclarativeBase,
                target_file_name="models",
                log_level="INFO"
            )

            # Find all model classes
            model_files = finder.find_all_classes()

            for file_path, class_names in model_files.items():
                print(f"File: {file_path}")
                for class_name in class_names:
                    print(f"  Found model: {class_name}")

        Plugin system integration::

            from abc import ABC, abstractmethod

            class BasePlugin(ABC):
                @abstractmethod
                def execute(self): pass

            # Discover plugins
            plugin_finder = ClassFinder(
                directory=Path("plugins"),
                find_sub_class=BasePlugin,
                target_file_name="plugin"
            )

            # Run discovery with full reporting
            plugin_finder.run()

        Custom working directory::

            # When project structure requires custom Python path
            finder = ClassFinder(
                directory=Path("external/modules"),
                find_sub_class=MyBaseClass,
                target_file_name="handlers",
                work_dir=Path("/custom/python/path"),
                log_level="DEBUG"
            )

    Note:
        The ClassFinder automatically manages sys.path modifications to ensure
        clean imports without affecting the global Python environment.
        All operations include comprehensive logging and error handling.
    """

    def __init__(
        self,
        directory: Path,
        find_sub_class: type,
        target_file_name: str,
        work_dir: Path | None = None,
        log_level: str = "INFO",
    ):
        """Initialize ClassFinder with discovery parameters.

        Args:
            directory (Path): Directory to search for Python files
            find_sub_class (type): Base class to find subclasses of
            target_file_name (str): File name filter for target files
            work_dir (Path | None): Working directory to add to sys.path
            log_level (str): Logging level for operation tracking

        Raises:
            FileNotFoundError: If the specified directory doesn't exist
            TypeError: If parameters have incorrect types
            ClassFinderError: If validation fails

        Example:
            Standard initialization::

                finder = ClassFinder(
                    directory=Path("src/plugins"),
                    find_sub_class=BasePlugin,
                    target_file_name="plugin"
                )

            With custom configuration::

                finder = ClassFinder(
                    directory=Path("external/handlers"),
                    find_sub_class=BaseHandler,
                    target_file_name="handler",
                    work_dir=Path("/custom/modules"),
                    log_level="DEBUG"
                )

            Error handling::

                try:
                    finder = ClassFinder(
                        directory=Path("nonexistent"),
                        find_sub_class=MyClass,
                        target_file_name="target"
                    )
                except (FileNotFoundError, TypeError) as e:
                    print(f"Setup failed: {e}")
        """
        self._validate_inputs(directory, find_sub_class, target_file_name)

        self.directory = directory
        self.find_sub_class = find_sub_class
        self.target_file_name = target_file_name
        self.work_dir = work_dir
        self.logger = self._setup_logger(log_level)

    def _validate_inputs(self, directory: Path, find_sub_class: type, target_file_name: str) -> None:
        """Validate initialization parameters.

        Args:
            directory (Path): Directory path to validate
            find_sub_class (type): Base class type to validate
            target_file_name (str): File name filter to validate

        Raises:
            TypeError: If parameters have incorrect types
            FileNotFoundError: If directory doesn't exist

        Note:
            This method ensures all parameters are valid before proceeding
            with ClassFinder operations to prevent runtime errors.
        """
        if not isinstance(directory, Path):
            raise CoreToolsTypeError("class_finder", "Path", str(type(directory).__name__))

        if not directory.exists():
            raise FileNotFoundError(f"Директория не найдена: {directory}")

        if not isinstance(find_sub_class, type):
            raise CoreToolsTypeError("class_finder", "type", str(type(find_sub_class).__name__))

        if not isinstance(target_file_name, str) or not target_file_name.strip():
            raise CoreToolsTypeError("class_finder", "str", str(type(target_file_name).__name__))

    @contextmanager
    def _sys_path_context(self) -> Generator[None, None, None]:
        """Context manager for safe sys.path modifications.

        Temporarily modifies sys.path to include the working directory,
        then restores the original path after operations complete.

        Yields:
            None: Context for operations requiring modified sys.path

        Example:
            Safe path modification::

                with finder._sys_path_context():
                    # sys.path is temporarily modified
                    module = importlib.import_module("custom.module")
                # sys.path is restored to original state

        Note:
            This ensures that sys.path modifications don't persist
            beyond the intended scope, preventing import pollution.
        """
        import sys

        original_path = sys.path.copy()
        try:
            if self.work_dir:
                sys.path.insert(0, str(self.work_dir))
            yield
        finally:
            sys.path[:] = original_path

    def find_python_files(self) -> list[Path]:
        """Recursively discover Python files matching the target filter.

        Searches the configured directory recursively for Python files
        whose names contain the specified target_file_name filter.

        Returns:
            list[Path]: List of Python file paths matching the filter

        Example:
            Finding model files::

                finder = ClassFinder(
                    directory=Path("src"),
                    find_sub_class=BaseModel,
                    target_file_name="models"
                )

                files = finder.find_python_files()
                print(f"Found {len(files)} Python files:")
                for file_path in files:
                    print(f"  {file_path}")

            Custom filtering::

                # Finds files like: user_handler.py, order_handler.py
                handler_finder = ClassFinder(
                    directory=Path("handlers"),
                    find_sub_class=BaseHandler,
                    target_file_name="handler"
                )

                handler_files = handler_finder.find_python_files()

        Note:
            The search is recursive and includes subdirectories.
            Only files with .py extension are considered.
        """
        python_files = []
        for file_path in self.directory.rglob("*.py"):
            if self.target_file_name in file_path.stem:
                python_files.append(file_path)
        return python_files

    def find_classes_in_file(self, file_path: Path) -> list[str]:
        """Discover classes in a specific Python file.

        Imports the specified Python file and discovers all classes
        that inherit from the configured base class.

        Args:
            file_path (Path): Path to the Python file to analyze

        Returns:
            list[str]: List of class names inheriting from base class

        Example:
            Analyzing a specific file::

                classes = finder.find_classes_in_file(
                    Path("src/models/user_models.py")
                )

                print(f"Found classes: {classes}")
                # Output: ['User', 'UserProfile', 'UserSession']

            Error handling::

                try:
                    classes = finder.find_classes_in_file(file_path)
                    if not classes:
                        print("No matching classes found")
                except ModuleImportError:
                    print(f"Failed to import {file_path}")

        Note:
            Uses safe sys.path context to avoid import pollution.
            Returns empty list if file cannot be imported or contains no matches.
        """
        module_path = self._get_module_path(file_path)

        with self._sys_path_context():
            try:
                module = importlib.import_module(module_path)
            except (ModuleNotFoundError, ImportError) as e:
                self.logger.warning(f"Модуль не найден: {module_path} - {e}")
                return []

        classes = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if self._is_target_class(attr):
                classes.append(attr_name)

        return classes

    def _get_module_path(self, file_path: Path) -> str:
        """Convert file path to Python module path.

        Args:
            file_path (Path): Python file path to convert

        Returns:
            str: Module path suitable for importlib.import_module

        Example:
            Path conversion::

                file_path = Path("src/models/user_models.py")
                module_path = finder._get_module_path(file_path)
                # Returns: "models.user_models"
        """
        relative_path = file_path.relative_to(self.directory)
        return str(relative_path.with_suffix("")).replace("/", ".")

    def _is_target_class(self, attr: Any) -> bool:
        """Check if an attribute is a target class.

        Args:
            attr (Any): Attribute to check

        Returns:
            bool: True if attribute is a subclass of the target base class

        Note:
            Excludes the base class itself from matches to avoid
            including the parent class in discovery results.
        """
        return isinstance(attr, type) and issubclass(attr, self.find_sub_class) and attr is not self.find_sub_class

    def find_all_classes(self) -> dict[Path, list[str]]:
        """Discover all classes in Python files within the directory.

        Performs comprehensive class discovery across all matching Python
        files in the configured directory tree.

        Returns:
            dict[Path, list[str]]: Mapping of file paths to discovered class names

        Example:
            Complete discovery workflow::

                finder = ClassFinder(
                    directory=Path("src/models"),
                    find_sub_class=BaseModel,
                    target_file_name="models"
                )

                all_classes = finder.find_all_classes()

                for file_path, class_names in all_classes.items():
                    print(f"\nFile: {file_path}")
                    for class_name in class_names:
                        print(f"  Class: {class_name}")

            Statistics and filtering::

                all_classes = finder.find_all_classes()

                total_files = len(all_classes)
                total_classes = sum(len(classes) for classes in all_classes.values())

                print(f"Discovery complete:")
                print(f"  Files: {total_files}")
                print(f"  Classes: {total_classes}")

        Note:
            Only returns files that contain at least one matching class.
            Empty files or files with no matches are excluded from results.
        """
        python_files = self.find_python_files()
        all_classes = {}

        for file_path in python_files:
            classes = self.find_classes_in_file(file_path)
            if classes:
                all_classes[file_path] = classes

        return all_classes

    def generate_import_statements(self, classes: dict[Path, list[str]]) -> list[tuple[str, str]]:
        """Generate import statements for discovered classes.

        Creates a list of import statements suitable for dynamic importing
        or code generation based on discovered classes.

        Args:
            classes (dict[Path, list[str]]): Classes discovered by find_all_classes

        Returns:
            list[tuple[str, str]]: List of (module_path, class_name) tuples

        Example:
            Import statement generation::

                classes = finder.find_all_classes()
                imports = finder.generate_import_statements(classes)

                for module_path, class_name in imports:
                    print(f"from {module_path} import {class_name}")

            Code generation::

                imports = finder.generate_import_statements(classes)

                # Generate dynamic import code
                import_code = []
                for module_path, class_name in imports:
                    import_code.append(f"from {module_path} import {class_name}")

                with open("generated_imports.py", "w") as f:
                    f.write("\n".join(import_code))

        Note:
            The generated import statements use absolute imports based
            on the module path structure relative to the search directory.
        """
        import_statements = []
        for file_path, class_list in classes.items():
            module_path = self._get_module_path(file_path)
            for class_name in class_list:
                import_statements.append((module_path, class_name))
        return import_statements

    def dynamic_import(self, import_statements: list[tuple[str, str]]) -> list[str]:
        """Perform dynamic imports with detailed status reporting.

        Executes dynamic imports for all specified classes and generates
        a colored status report showing success/failure for each import.

        Args:
            import_statements (list[tuple[str, str]]): Import statements to execute

        Returns:
            list[str]: Colored status report lines for console output

        Example:
            Dynamic import with reporting::

                classes = finder.find_all_classes()
                imports = finder.generate_import_statements(classes)
                report = finder.dynamic_import(imports)

                for line in report:
                    print(line)  # Colored output

            Validation workflow::

                # Use dynamic_import to validate all discovered classes
                imports = finder.generate_import_statements(classes)
                results = finder.dynamic_import(imports)

                # Check for failures
                failures = [line for line in results if "FAIL" in line]
                if failures:
                    print(f"Found {len(failures)} import failures")

        Note:
            Uses ANSI color codes for terminal output. Green for success,
            red for failures. Safe sys.path context prevents pollution.
        """
        report = []

        with self._sys_path_context():
            for module_path, class_name in import_statements:
                msg = f"  - {module_path}.{class_name}"
                try:
                    module = importlib.import_module(module_path)
                    _ = getattr(module, class_name)
                    report.append(f"\033[32m{msg.ljust(50, '.')}... OK\033[0m")
                except Exception as e:
                    error_msg = (
                        f"\033[31m{msg.ljust(50, '.')}... FAIL\n    {e.__class__.__name__}:\033[0m \033[37m{e}\033[0m"
                    )
                    report.append(error_msg)

        return report

    def run(self) -> None:
        """Execute complete class discovery and import workflow.

        Performs the full workflow: discovery, import generation,
        and dynamic import validation with comprehensive logging
        and colored console output.

        Example:
            Complete workflow execution::

                finder = ClassFinder(
                    directory=Path("src/plugins"),
                    find_sub_class=BasePlugin,
                    target_file_name="plugin",
                    log_level="INFO"
                )

                # Run complete discovery and validation
                finder.run()

            Output example::

                Starting dynamic import...
                  - plugins.user_plugin.UserPlugin........... OK
                  - plugins.order_plugin.OrderPlugin......... OK
                  - plugins.broken_plugin.BrokenPlugin....... FAIL
                    ImportError: No module named 'missing_dependency'
                Dynamic import completed.

        Note:
            This method combines all ClassFinder operations into a single
            workflow suitable for validation scripts, plugin discovery,
            and development tooling.
        """
        classes = self.find_all_classes()

        # Логирование найденных классов
        for file_path, class_list in classes.items():
            self.logger.debug(f"\033[37mФайл: {file_path}\033[0m")
            for class_name in class_list:
                msg = f"  Класс: {class_name}, Наследует от: {self.find_sub_class.__name__}"
                self.logger.debug(msg)

        # Генерация и выполнение импортов
        imports = self.generate_import_statements(classes)
        for module_path, class_name in imports:
            self.logger.debug(f"from {module_path} import {class_name}")

        # Отчет о динамическом импорте
        logger_msg = ["\033[37mНачало динамического импорта...\033[0m"]
        logger_msg.extend(self.dynamic_import(imports))
        logger_msg.append("\033[37mДинамический импорт завершен.\033[0m")
        self.logger.info("\n".join(logger_msg))

    def build_tortoise_imports(self) -> list[str]:
        """Build import statements for Tortoise ORM models.

        Generates unique module paths suitable for Tortoise ORM model
        registration and configuration.

        Returns:
            list[str]: List of unique module paths for import

        Example:
            Tortoise ORM integration::

                model_finder = ClassFinder(
                    directory=Path("src/models"),
                    find_sub_class=Model,  # Tortoise Model base class
                    target_file_name="models"
                )

                module_paths = model_finder.build_tortoise_imports()

                # Configure Tortoise with discovered models
                TORTOISE_ORM = {
                    "connections": {"default": DATABASE_URL},
                    "apps": {
                        "models": {
                            "models": module_paths,
                            "default_connection": "default",
                        }
                    }
                }

        Note:
            Returns only unique module paths to avoid duplicate registrations
            in ORM configurations. Suitable for automated ORM setup.
        """
        classes = self.find_all_classes()
        imports = self.generate_import_statements(classes)

        module_paths = {module_path for module_path, _ in imports}
        return list(module_paths)

    def _setup_logger(self, log_level: str) -> logging.Logger:
        """Setup and configure logger for ClassFinder operations.

        Args:
            log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR)

        Returns:
            logging.Logger: Configured logger instance

        Note:
            Creates a specialized logger for ClassFinder with console output
            and appropriate formatting for discovery operations.
        """
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(levelname)s %(asctime)s %(name)s:\n%(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": log_level,
                },
            },
            "loggers": {
                "DynamicImportLogger": {
                    "handlers": ["console"],
                    "level": log_level,
                    "propagate": False,
                },
            },
        }

        logging.config.dictConfig(logging_config)
        return logging.getLogger("DynamicImportLogger")
