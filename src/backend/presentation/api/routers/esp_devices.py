"""Paired board routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.application.dto.user import (
    ClaimEspDeviceCommand,
    PairEspDeviceCommand,
)
from backend.application.use_cases.esp_device import ClaimNotFoundError
from backend.domain.entities.user import (
    AlreadyClaimedError,
    ExpiredClaimError,
    InvalidBoardNameError,
    InvalidPairingKeyError,
)
from backend.domain.enums.operation import OperationStatus
from backend.presentation.api.errors import raise_for_status
from backend.presentation.api.messages import (
    board_claimed_message,
    board_paired_message,
    board_unpaired_message,
    claim_expired_message,
    claim_taken_message,
    created_message,
    not_found_message,
)
from backend.presentation.api.requests import ClaimEspDeviceBody, PairEspDeviceBody
from backend.presentation.api.responses import (
    ClaimResponse,
    EspDeviceResponse,
    OperationResponse,
)
from backend.presentation.api.security import AppContainer, CurrentUserId

router = APIRouter(prefix="/esp-devices", tags=["esp-devices"])


@router.get("/claims")
async def list_claims(container: AppContainer, user_id: CurrentUserId) -> list[dict]:
    """Return the boards that are waiting to be taken.

    The list is the same for every account: a board announces itself to the
    server, not to a user. What makes it safe is that an offer only exists while
    the board is being held and that the first account to take it wins.

    Args:
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        list[dict]: Offers with their token, label and expiry.
    """
    return [claim.to_payload() for claim in await container.list_esp_claims.execute()]


@router.post("/claims")
async def claim_board(
    body: ClaimEspDeviceBody, container: AppContainer, user_id: CurrentUserId
) -> OperationResponse:
    """Take an announced board for the current account.

    This is the step that replaces typing a pairing key into the firmware: the
    board generated its own key, the interface offers it, and the account that
    presses the button owns it from then on.

    Args:
        body: Token of the offer and the chosen board name.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        OperationResponse: The board that is now paired.

    Raises:
        HTTPException: When the token is unknown, over or already taken, or the
            name is malformed.
    """
    try:
        board = await container.claim_esp_device.execute(
            user_id,
            ClaimEspDeviceCommand(claim_token=body.claim_token, name=body.name),
        )
    except ClaimNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, not_found_message("Плата", body.claim_token)
        ) from exc
    except ExpiredClaimError as exc:
        raise HTTPException(status.HTTP_410_GONE, claim_expired_message()) from exc
    except AlreadyClaimedError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, claim_taken_message()) from exc
    except InvalidBoardNameError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Некорректное имя платы") from exc
    return OperationResponse(
        status=OperationStatus.SUCCESS.value,
        message=board_claimed_message(body.name),
        data=ClaimResponse.from_device(board).model_dump(),
    )


@router.get("")
async def list_boards(user_id: CurrentUserId, container: AppContainer) -> list[EspDeviceResponse]:
    """Return the boards paired with the current user.

    Args:
        user_id: Owner resolved from the bearer token.
        container: Assembled dependency graph.

    Returns:
        list[EspDeviceResponse]: Boards of the user.
    """
    boards = await container.list_esp_devices.execute(user_id)
    online = container.esp_connection
    return [EspDeviceResponse.from_board(board, online.is_online(user_id)) for board in boards]


@router.post("")
async def pair_board(
    body: PairEspDeviceBody, user_id: CurrentUserId, container: AppContainer
) -> OperationResponse:
    """Pair a board with the current account.

    The answer carries the pairing key exactly once, because it is what the
    board has to present while dialing in.

    Args:
        body: Board name and an optional key chosen by the user.
        user_id: Owner resolved from the bearer token.
        container: Assembled dependency graph.

    Returns:
        OperationResponse: The paired board including its pairing key.

    Raises:
        HTTPException: When the name or the provided key is malformed.
    """
    try:
        result, board = await container.pair_esp_device.execute(
            user_id,
            PairEspDeviceCommand(name=body.name, pairing_key=body.pairing_key),
        )
    except (InvalidBoardNameError, InvalidPairingKeyError) as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Некорректное имя платы или ключ сопряжения",
        ) from exc
    raise_for_status(result, created_message("Плата", body.name))
    return OperationResponse(
        status=result.value,
        message=board_paired_message(),
        data=EspDeviceResponse.from_board(board, False, reveal_key=True).model_dump(),
    )


@router.delete("/{device_id}")
async def unpair_board(
    device_id: int, user_id: CurrentUserId, container: AppContainer
) -> OperationResponse:
    """Remove a board from the current account.

    Args:
        device_id: Identifier of the board.
        user_id: Owner resolved from the bearer token.
        container: Assembled dependency graph.

    Returns:
        OperationResponse: Result of the removal.

    Raises:
        HTTPException: When the board does not belong to the user.
    """
    result = await container.revoke_esp_device.execute(user_id, device_id)
    if result is OperationStatus.NOT_FOUND:
        raise HTTPException(status.HTTP_404_NOT_FOUND, not_found_message("Плата", device_id))
    raise_for_status(result, board_unpaired_message(device_id))
    return OperationResponse(status=result.value, message=board_unpaired_message(device_id))
