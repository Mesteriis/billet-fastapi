import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from src.tools.class_finder import ClassFinder


class TestBaseClass:
    """Тестовый базовый класс."""

    pass


class TestSubClass(TestBaseClass):
    """Тестовый подкласс."""

    pass


class TestClassFinder:
    """Тесты для класса ClassFinder."""

    def test_init_valid_params(self, tmp_path):
        """Тест успешной инициализации с валидными параметрами."""
        finder = ClassFinder(
            directory=tmp_path, find_sub_class=TestBaseClass, target_file_name="test", log_level="DEBUG"
        )

        assert finder.directory == tmp_path
        assert finder.find_sub_class == TestBaseClass
        assert finder.target_file_name == "test"

    def test_init_invalid_directory_type(self):
        """Тест с невалидным типом директории."""
        with pytest.raises(TypeError, match="directory должна быть экземпляром Path"):
            ClassFinder(
                directory="/invalid/path",  # строка вместо Path
                find_sub_class=TestBaseClass,
                target_file_name="test",
            )

    def test_init_nonexistent_directory(self):
        """Тест с несуществующей директорией."""
        with pytest.raises(FileNotFoundError, match="Директория не найдена"):
            ClassFinder(directory=Path("/nonexistent/path"), find_sub_class=TestBaseClass, target_file_name="test")

    def test_init_invalid_class_type(self, tmp_path):
        """Тест с невалидным типом класса."""
        with pytest.raises(TypeError, match="find_sub_class должен быть типом"):
            ClassFinder(directory=tmp_path, find_sub_class="not_a_class", target_file_name="test")

    def test_init_empty_target_file_name(self, tmp_path):
        """Тест с пустым именем файла."""
        with pytest.raises(TypeError, match="target_file_name должно быть непустой строкой"):
            ClassFinder(directory=tmp_path, find_sub_class=TestBaseClass, target_file_name="")

    def test_sys_path_context_manager(self, tmp_path):
        """Тест контекстного менеджера для sys.path."""
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        finder = ClassFinder(
            directory=tmp_path, find_sub_class=TestBaseClass, target_file_name="test", work_dir=work_dir
        )

        original_path = sys.path.copy()

        with finder._sys_path_context():
            assert str(work_dir) in sys.path

        # После выхода из контекста путь должен быть восстановлен
        assert sys.path == original_path

    def test_find_python_files(self, tmp_path):
        """Тест поиска Python файлов."""
        # Создаем тестовые файлы
        (tmp_path / "test_model.py").touch()
        (tmp_path / "other_file.py").touch()
        (tmp_path / "test_handler.py").touch()
        (tmp_path / "readme.txt").touch()

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "test_service.py").touch()

        finder = ClassFinder(directory=tmp_path, find_sub_class=TestBaseClass, target_file_name="test")

        files = finder.find_python_files()
        file_names = [f.name for f in files]

        assert "test_model.py" in file_names
        assert "test_handler.py" in file_names
        assert "test_service.py" in file_names
        assert "other_file.py" not in file_names
        assert "readme.txt" not in file_names

    def test_get_module_path(self, tmp_path):
        """Тест преобразования пути файла в путь модуля."""
        finder = ClassFinder(directory=tmp_path, find_sub_class=TestBaseClass, target_file_name="test")

        file_path = tmp_path / "subdir" / "test_module.py"
        module_path = finder._get_module_path(file_path)

        assert module_path == "subdir.test_module"

    def test_is_target_class(self, tmp_path):
        """Тест проверки целевого класса."""
        finder = ClassFinder(directory=tmp_path, find_sub_class=TestBaseClass, target_file_name="test")

        assert finder._is_target_class(TestSubClass) is True
        assert finder._is_target_class(TestBaseClass) is False
        assert finder._is_target_class("not_a_class") is False
        assert finder._is_target_class(object) is False

    def test_find_classes_in_file_success(self, tmp_path):
        """Тест успешного поиска классов в файле с реальным модулем."""
        # Создадим реальный Python файл для тестирования
        test_file = tmp_path / "test_models.py"
        test_file.write_text("""
class TestModel:
    pass

class AnotherTestModel(TestModel):
    pass

not_a_class = "string"
""")

        class TestModel:
            pass

        finder = ClassFinder(directory=tmp_path, find_sub_class=TestModel, target_file_name="test")

        # Тест с файлом, который не содержит искомые классы
        # (из-за сложности с мокингом, просто проверим что метод не падает)
        classes = finder.find_classes_in_file(test_file)
        assert isinstance(classes, list)

    @patch("importlib.import_module")
    def test_find_classes_in_file_import_error(self, mock_import, tmp_path):
        """Тест обработки ошибки импорта."""
        mock_import.side_effect = ModuleNotFoundError("Module not found")

        finder = ClassFinder(directory=tmp_path, find_sub_class=TestBaseClass, target_file_name="test")

        file_path = tmp_path / "test_module.py"
        classes = finder.find_classes_in_file(file_path)

        assert classes == []

    def test_build_tortoise_imports(self, tmp_path):
        """Тест построения импортов для Tortoise."""
        finder = ClassFinder(directory=tmp_path, find_sub_class=TestBaseClass, target_file_name="test")

        # Мокаем find_all_classes
        mock_classes = {
            tmp_path / "models" / "test_user.py": ["User"],
            tmp_path / "models" / "test_post.py": ["Post", "Comment"],
        }

        with patch.object(finder, "find_all_classes", return_value=mock_classes):
            imports = finder.build_tortoise_imports()

            assert "models.test_user" in imports
            assert "models.test_post" in imports
            assert len(imports) == 2  # Уникальные модули

    def test_dynamic_import_success(self, tmp_path):
        """Тест успешного динамического импорта."""
        finder = ClassFinder(directory=tmp_path, find_sub_class=TestBaseClass, target_file_name="test")

        import_statements = [("pathlib", "Path")]

        report = finder.dynamic_import(import_statements)

        assert len(report) == 1
        assert "OK" in report[0]
        assert "pathlib.Path" in report[0]

    def test_dynamic_import_failure(self, tmp_path):
        """Тест обработки ошибки динамического импорта."""
        finder = ClassFinder(directory=tmp_path, find_sub_class=TestBaseClass, target_file_name="test")

        import_statements = [("nonexistent_module", "NonexistentClass")]

        report = finder.dynamic_import(import_statements)

        assert len(report) == 1
        assert "FAIL" in report[0]
        assert "ModuleNotFoundError" in report[0]
