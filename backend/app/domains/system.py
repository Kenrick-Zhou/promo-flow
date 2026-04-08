"""System management domain types (categories and tags)."""

from __future__ import annotations

from dataclasses import dataclass, field

# ============================================================
# Command Objects
# ============================================================


@dataclass(slots=True)
class CreateCategoryCommand:
    """Command for creating a new category."""

    name: str
    parent_id: int | None = None
    sort_order: int = 0


@dataclass(slots=True)
class UpdateCategoryCommand:
    """Command for updating a category."""

    name: str | None = None
    sort_order: int | None = None


@dataclass(slots=True)
class CreateTagCommand:
    """Command for creating a new tag."""

    name: str
    is_system: bool = True
    sort_order: int = 0


@dataclass(slots=True)
class UpdateTagCommand:
    """Command for updating a tag."""

    name: str | None = None
    is_system: bool | None = None
    sort_order: int | None = None


@dataclass(slots=True)
class ReorderTagsCommand:
    """Command for batch-reordering system tags."""

    items: list[tuple[int, int]]  # list of (tag_id, sort_order)


# ============================================================
# Output Objects
# ============================================================


@dataclass(slots=True)
class CategoryOutput:
    """Single category item output."""

    id: int
    name: str
    parent_id: int | None
    sort_order: int
    created_at: str
    updated_at: str


@dataclass(slots=True)
class CategoryTreeOutput:
    """Category with children for tree display."""

    id: int
    name: str
    parent_id: int | None
    sort_order: int
    children: list[CategoryTreeOutput] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass(slots=True)
class TagOutput:
    """Tag item output."""

    id: int
    name: str
    is_system: bool
    sort_order: int
    created_at: str
