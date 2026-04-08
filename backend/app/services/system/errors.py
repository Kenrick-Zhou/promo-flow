"""System management domain errors."""

from typing import NoReturn

from fastapi import HTTPException
from starlette import status

# ============================================================
# Exceptions
# ============================================================


class CategoryNotFoundError(Exception):
    def __init__(self, category_id: int | None = None):
        super().__init__("category_not_found")
        self.category_id = category_id


class DuplicateCategoryError(Exception):
    def __init__(self, name: str = ""):
        super().__init__("duplicate_category")
        self.name = name


class CategoryHasChildrenError(Exception):
    def __init__(self):
        super().__init__("category_has_children")


class CategoryHasContentsError(Exception):
    def __init__(self):
        super().__init__("category_has_contents")


class TagNotFoundError(Exception):
    def __init__(self, tag_id: int | None = None):
        super().__init__("tag_not_found")
        self.tag_id = tag_id


class DuplicateTagError(Exception):
    def __init__(self, name: str = ""):
        super().__init__("duplicate_tag")
        self.name = name


class TagInUseError(Exception):
    def __init__(self):
        super().__init__("tag_in_use")


# ============================================================
# HTTP Error Mapping
# ============================================================


def raise_system_error(exc: Exception) -> NoReturn:
    """Map system domain exceptions to HTTP responses."""
    if isinstance(exc, CategoryNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "category_not_found", "message": "类目不存在。"},
        ) from exc

    if isinstance(exc, DuplicateCategoryError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "duplicate_category",
                "message": f"类目名称「{exc.name}」已存在。",
            },
        ) from exc

    if isinstance(exc, CategoryHasChildrenError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "category_has_children",
                "message": "该类目下存在子类目，无法删除。",
            },
        ) from exc

    if isinstance(exc, CategoryHasContentsError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "category_has_contents",
                "message": "该类目下存在素材，无法删除。",
            },
        ) from exc

    if isinstance(exc, TagNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "tag_not_found", "message": "标签不存在。"},
        ) from exc

    if isinstance(exc, DuplicateTagError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "duplicate_tag",
                "message": f"标签「{exc.name}」已存在。",
            },
        ) from exc

    if isinstance(exc, TagInUseError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "tag_in_use",
                "message": "该标签正在使用中，无法删除。",
            },
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error_code": "system_internal_error",
            "message": "系统管理操作发生未知错误。",
        },
    ) from exc
