from __future__ import annotations

from pydantic import BaseModel, Field

from app.domains.system import (
    CategoryOutput,
    CategoryTreeOutput,
    CreateCategoryCommand,
    CreateTagCommand,
    TagOutput,
    UpdateCategoryCommand,
    UpdateTagCommand,
)

# ============================================================
# Category Schemas
# ============================================================


class CategoryCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    parent_id: int | None = None
    sort_order: int = 0

    def to_domain(self) -> CreateCategoryCommand:
        return CreateCategoryCommand(
            name=self.name,
            parent_id=self.parent_id,
            sort_order=self.sort_order,
        )


class CategoryUpdateIn(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    sort_order: int | None = None

    def to_domain(self) -> UpdateCategoryCommand:
        return UpdateCategoryCommand(
            name=self.name,
            sort_order=self.sort_order,
        )


class CategoryOut(BaseModel):
    id: int
    name: str
    parent_id: int | None
    sort_order: int
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, output: CategoryOutput) -> CategoryOut:
        return cls(
            id=output.id,
            name=output.name,
            parent_id=output.parent_id,
            sort_order=output.sort_order,
            created_at=output.created_at,
            updated_at=output.updated_at,
        )


class CategoryTreeOut(BaseModel):
    id: int
    name: str
    parent_id: int | None
    sort_order: int
    children: list[CategoryTreeOut] = []
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_domain(cls, output: CategoryTreeOutput) -> CategoryTreeOut:
        return cls(
            id=output.id,
            name=output.name,
            parent_id=output.parent_id,
            sort_order=output.sort_order,
            children=[cls.from_domain(c) for c in output.children],
            created_at=output.created_at,
            updated_at=output.updated_at,
        )


# ============================================================
# Tag Schemas
# ============================================================


class TagCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    is_system: bool = True

    def to_domain(self) -> CreateTagCommand:
        return CreateTagCommand(
            name=self.name,
            is_system=self.is_system,
        )


class TagUpdateIn(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    is_system: bool | None = None

    def to_domain(self) -> UpdateTagCommand:
        return UpdateTagCommand(
            name=self.name,
            is_system=self.is_system,
        )


class TagOut(BaseModel):
    id: int
    name: str
    is_system: bool
    created_at: str

    @classmethod
    def from_domain(cls, output: TagOutput) -> TagOut:
        return cls(
            id=output.id,
            name=output.name,
            is_system=output.is_system,
            created_at=output.created_at,
        )
