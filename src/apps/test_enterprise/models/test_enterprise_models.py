"""
TestEnterprise model definition.

This is a generated model stub. Add your fields here.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.base.models import BaseModel


class TestEnterprise(BaseModel):
    """
    TestEnterprise model.

    TODO: Add your fields here
    Example:
        name: Mapped[str] = mapped_column(String(255), nullable=False)
        description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
        price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
        is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    """

    # Add your fields here
    name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        comment="TestEnterprise name"
    )

    def __repr__(self) -> str:
        return f"<TestEnterprise(id={self.id}, name='{self.name}')>"
