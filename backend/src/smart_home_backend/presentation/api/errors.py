"""Mapping of operation statuses onto HTTP responses."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import HTTPException

from smart_home_backend.domain.enums.operation import OperationStatus

STATUS_CODES: dict[OperationStatus, int] = {
    OperationStatus.SUCCESS: HTTPStatus.OK,
    OperationStatus.NOT_FOUND: HTTPStatus.NOT_FOUND,
    OperationStatus.UNAVAILABLE: HTTPStatus.SERVICE_UNAVAILABLE,
    OperationStatus.UNSUPPORTED: HTTPStatus.CONFLICT,
    OperationStatus.CHANNEL_CONFLICT: HTTPStatus.CONFLICT,
    OperationStatus.INVALID_INPUT: HTTPStatus.UNPROCESSABLE_ENTITY,
    OperationStatus.FAILED: HTTPStatus.INTERNAL_SERVER_ERROR,
}


def raise_for_status(status: OperationStatus, detail: str) -> None:
    """Raise an HTTP error unless the operation succeeded.

    Args:
        status: Result class of the operation.
        detail: Human readable reason.

    Returns:
        None.

    Raises:
        HTTPException: When the operation did not succeed.
    """
    code = STATUS_CODES.get(status, HTTPStatus.INTERNAL_SERVER_ERROR)
    if code == HTTPStatus.OK:
        return
    raise HTTPException(status_code=code, detail=detail)
