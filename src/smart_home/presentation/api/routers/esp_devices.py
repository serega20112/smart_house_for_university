"""Paired board routes.

Pairing, taking over a board that already announced itself and removing a board
are three different operations and each of them lives in the application layer.
The routes only translate bodies, and the board list is completed with the
connectivity of the live transport, because whether a board is connected is
something a table row can never know.
"""

from __future__ import annotations

from dataclasses import replace

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from smart_home.application.dto import ClaimBoardCommand, PairBoardCommand
from smart_home.application.ports.boards import BoardGateway
from smart_home.application.ports.queries.boards import BoardQueries
from smart_home.application.services.board_onboarding import BoardOnboardingService
from smart_home.domain.identifiers import EspDeviceId
from smart_home.presentation.api.schemas import (
    BoardClaimResponse,
    BoardPairedResponse,
    BoardResponse,
    ClaimBoardBody,
    PairBoardBody,
    board_of,
    claim_of,
)
from smart_home.presentation.api.security import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/esp-devices", tags=["esp-devices"])


@router.get("/claims", response_model=list[BoardClaimResponse])
async def list_claims(queries: FromDishka[BoardQueries]) -> list[BoardClaimResponse]:
    """Return the boards that are waiting to be taken.

    The list is the same for every account: a board announces itself to the
    server, not to a user. What makes it safe is that an offer only exists while
    the board is being held and that the first account to take it wins.

    Args:
        queries: Reads of the boards.

    Returns:
        list[BoardClaimResponse]: Offers with their token, label and expiry.
    """
    return [claim_of(claim) for claim in await queries.list_open_claims()]


@router.post(
    "/claims",
    status_code=status.HTTP_201_CREATED,
    response_model=BoardResponse,
)
async def claim_board(
    body: ClaimBoardBody,
    user_id: CurrentUserId,
    onboarding: FromDishka[BoardOnboardingService],
) -> BoardResponse:
    """Take an announced board for the current account.

    This is the step that replaces typing a pairing key into the firmware: the
    board generated its own key, the interface offers it, and the account that
    presses the button owns it from then on.

    Args:
        body: Token of the offer and the chosen board name.
        user_id: Owner resolved from the bearer token.
        onboarding: Pairing operations of the boards.

    Returns:
        BoardResponse: The board that is now paired.
    """
    board = await onboarding.claim(
        user_id,
        ClaimBoardCommand(claim_token=body.claim_token, name=body.name),
    )
    return board_of(board)


@router.get("", response_model=list[BoardResponse])
async def list_boards(
    user_id: CurrentUserId,
    queries: FromDishka[BoardQueries],
    gateway: FromDishka[BoardGateway],
) -> list[BoardResponse]:
    """Return the boards paired with the current user.

    Args:
        user_id: Owner resolved from the bearer token.
        queries: Reads of the boards.
        gateway: Live transport, asked whether a board is connected.

    Returns:
        list[BoardResponse]: Boards of the user.
    """
    boards = await queries.list_for(user_id)
    return [
        board_of(replace(board, online=gateway.is_connected(user_id, board.id))) for board in boards
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=BoardPairedResponse)
async def pair_board(
    body: PairBoardBody,
    user_id: CurrentUserId,
    onboarding: FromDishka[BoardOnboardingService],
) -> BoardPairedResponse:
    """Pair a board with the current account.

    The answer carries the pairing key exactly once, because it is what the
    board has to present while dialing in.

    Args:
        body: Board name and an optional key chosen by the user.
        user_id: Owner resolved from the bearer token.
        onboarding: Pairing operations of the boards.

    Returns:
        BoardPairedResponse: The paired board including its pairing key.
    """
    paired = await onboarding.pair(
        user_id,
        PairBoardCommand(name=body.name, pairing_key=body.pairing_key),
    )
    return BoardPairedResponse(
        id=str(paired.board.id),
        name=paired.board.name,
        pairing_key=paired.pairing_key,
    )


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unpair_board(
    device_id: str,
    user_id: CurrentUserId,
    onboarding: FromDishka[BoardOnboardingService],
) -> None:
    """Remove a board from the current account.

    Args:
        device_id: Identifier of the board.
        user_id: Owner resolved from the bearer token.
        onboarding: Pairing operations of the boards.

    Returns:
        None.
    """
    await onboarding.revoke(user_id, EspDeviceId.parse(device_id))
