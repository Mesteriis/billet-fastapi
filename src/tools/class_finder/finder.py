import importlib
import logging
import logging.config
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class ClassFinderError(Exception):
    """Базовое исключение для ClassFinder."""


class ModuleImportError(ClassFinderError):
    """Исключение при ошибке импорта модуля."""


class ClassFinder:
    """
    Класс для поиска и динамического импорта Python классов из указанной директории.

    Attributes:
        directory (Path): Директория для поиска Python файлов.
        find_sub_class (Type): Базовый класс для поиска наследников.
        target_file_name (str): Имя файла для фильтрации поиска.
        logger (logging.Logger): Экземпляр логгера для записи сообщений.
    """

    def __init__(
        self,
        directory: Path,
        find_sub_class: type,
        target_file_name: str,
        work_dir: Path | None = None,
        log_level: str = "INFO",
    ):
        """
        Инициализирует ClassFinder с указанными параметрами.

        Args:
            directory: Директория для поиска Python файлов.
            find_sub_class: Базовый класс для поиска наследников.
            target_file_name: Имя файла для фильтрации.
            work_dir: Рабочая директория для добавления в sys.path.
            log_level: Уровень логирования.

        Raises:
            FileNotFoundError: Если указанная директория не существует.
            TypeError: Если параметры имеют неверный тип.
        """
        self._validate_inputs(directory, find_sub_class, target_file_name)

        self.directory = directory
        self.find_sub_class = find_sub_class
        self.target_file_name = target_file_name
        self.work_dir = work_dir
        self.logger = self._setup_logger(log_level)

    def _validate_inputs(self, directory: Path, find_sub_class: type, target_file_name: str) -> None:
        """Валидирует входные параметры."""
        if not isinstance(directory, Path):
            raise TypeError("directory должна быть экземпляром Path")

        if not directory.exists():
            raise FileNotFoundError(f"Директория не найдена: {directory}")

        if not isinstance(find_sub_class, type):
            raise TypeError("find_sub_class должен быть типом")

        if not isinstance(target_file_name, str) or not target_file_name.strip():
            raise TypeError("target_file_name должно быть непустой строкой")

    @contextmanager
    def _sys_path_context(self) -> Generator[None, None, None]:
        """Контекстный менеджер для временного изменения sys.path."""
        import sys

        original_path = sys.path.copy()
        try:
            if self.work_dir:
                sys.path.insert(0, str(self.work_dir))
            yield
        finally:
            sys.path[:] = original_path

    def find_python_files(self) -> list[Path]:
        """
        Рекурсивно находит все Python файлы в указанной директории.

        Returns:
            Список путей к Python файлам, содержащим target_file_name.
        """
        python_files = []
        for file_path in self.directory.rglob("*.py"):
            if self.target_file_name in file_path.stem:
                python_files.append(file_path)
        return python_files

    def find_classes_in_file(self, file_path: Path) -> list[str]:
        """
        Находит все классы в указанном Python файле, наследующиеся от базового класса.

        Args:
            file_path: Путь к Python файлу.

        Returns:
            Список имен классов, наследующихся от указанного базового класса.
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
        """Преобразует путь к файлу в путь модуля."""
        relative_path = file_path.relative_to(self.directory)
        return str(relative_path.with_suffix("")).replace("/", ".")

    def _is_target_class(self, attr: Any) -> bool:
        """Проверяет, является ли атрибут целевым классом."""
        return isinstance(attr, type) and issubclass(attr, self.find_sub_class) and attr is not self.find_sub_class

    def find_all_classes(self) -> dict[Path, list[str]]:
        """
        Находит все классы в Python файлах в указанной директории.

        Returns:
            Словарь с путями файлов как ключами и списками имен классов как значениями.
        """
        python_files = self.find_python_files()
        all_classes = {}

        for file_path in python_files:
            classes = self.find_classes_in_file(file_path)
            if classes:
                all_classes[file_path] = classes

        return all_classes

    def generate_import_statements(self, classes: dict[Path, list[str]]) -> list[tuple[str, str]]:
        """
        Генерирует import statements для классов.

        Args:
            classes: Словарь с путями файлов и списками классов.

        Returns:
            Список кортежей (module_path, class_name).
        """
        import_statements = []
        for file_path, class_list in classes.items():
            module_path = self._get_module_path(file_path)
            for class_name in class_list:
                import_statements.append((module_path, class_name))
        return import_statements

    def dynamic_import(self, import_statements: list[tuple[str, str]]) -> list[str]:
        """
        Динамически импортирует указанные классы.

        Args:
            import_statements: Список кортежей (module_path, class_name).

        Returns:
            Список результатов импорта с сообщениями об успехе или неудаче.
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
        """Запускает процесс поиска классов и динамического импорта."""
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
        """
        Строит import statements для моделей Tortoise ORM.

        Returns:
            Список уникальных путей модулей для импорта.
        """
        classes = self.find_all_classes()
        imports = self.generate_import_statements(classes)

        module_paths = {module_path for module_path, _ in imports}
        return list(module_paths)

    def _setup_logger(self, log_level: str) -> logging.Logger:
        """
        Настраивает логгер для ClassFinder.

        Args:
            log_level: Уровень логирования.

        Returns:
            Настроенный экземпляр логгера.
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
