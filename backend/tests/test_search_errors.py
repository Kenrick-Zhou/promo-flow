import pytest
from fastapi import HTTPException

from app.services.search.errors import raise_search_error


def test_raise_search_error_passthroughs_http_exception() -> None:
    original = HTTPException(
        status_code=404, detail={"error_code": "not_found", "message": "Not found."}
    )

    with pytest.raises(HTTPException) as exc_info:
        raise_search_error(original)

    assert exc_info.value is original


def test_raise_search_error_maps_unknown_exception_to_internal_error() -> None:
    with pytest.raises(HTTPException) as exc_info:
        raise_search_error(RuntimeError("boom"))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == {
        "error_code": "search_internal_error",
        "message": "An unexpected search error occurred.",
    }
