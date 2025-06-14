import os
import sys
import traceback
from typing import Any, TypeVar

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ValidationError
from pydantic_settings import BaseSettings as PydanticBaseSettings

DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")


def running_under_pytest() -> bool:
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


T = TypeVar("T", bound="SafeModel")
S = TypeVar("S", bound="SafeSettings")


class SafeModel(PydanticBaseModel):
    def __init__(__pydantic_self__, **data: Any) -> None:
        try:
            super().__init__(**data)
        except ValidationError as e:
            SafeModel._raise_or_exit(e, model_name=__pydantic_self__.__class__.__name__)

    @classmethod
    def model_validate(cls: type[T], obj: Any, **kwargs) -> T:
        try:
            return super().model_validate(obj, **kwargs)
        except ValidationError as e:
            SafeModel._raise_or_exit(e, model_name=cls.__name__)
            # This line will never be reached due to SystemExit, but needed for type checker
            raise

    @staticmethod
    def _raise_or_exit(e: ValidationError, model_name: str = "Model") -> None:
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
    def __init__(__pydantic_self__, **data: Any) -> None:
        try:
            super().__init__(**data)
        except ValidationError as e:
            SafeModel._raise_or_exit(e, model_name=__pydantic_self__.__class__.__name__)

    @classmethod
    def model_validate(cls: type[S], obj: Any, **kwargs) -> S:
        try:
            return super().model_validate(obj, **kwargs)
        except ValidationError as e:
            SafeModel._raise_or_exit(e, model_name=cls.__name__)
            # This line will never be reached due to SystemExit, but needed for type checker
            raise


# Алиасы
BaseModel = SafeModel
BaseSettings = SafeSettings
