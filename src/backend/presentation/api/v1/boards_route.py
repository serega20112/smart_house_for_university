"""Маршруты сопряжённых плат.

Сопряжение, взятие уже объявленной платы и её удаление — три разные операции, и
каждая живёт в своём сценарии прикладного слоя. Маршрут только переводит тело
запроса в команду: даже признак «подключена сейчас» считает сценарий, потому что
строка таблицы об этом не знает.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from backend.application.use_cases.boards.claim_board import ClaimBoardUseCase
from backend.application.use_cases.boards.list_boards import ListBoardsUseCase
from backend.application.use_cases.boards.list_claims import ListBoardClaimsUseCase
from backend.application.use_cases.boards.pair_board import PairBoardUseCase
from backend.application.use_cases.boards.revoke_board import RevokeBoardUseCase
from backend.domain.identifiers import EspDeviceId
from backend.presentation.api.requests.boards import (
    ClaimBoardBody,
    PairBoardBody,
    claim_command,
    pair_command,
)
from backend.presentation.api.responses.boards import (
    BoardClaimResponse,
    BoardPairedResponse,
    BoardResponse,
    board_of,
    claim_of,
    paired_of,
)
from backend.presentation.security_helpers import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/esp-devices", tags=["esp-devices"])


@router.get("/claims", response_model=list[BoardClaimResponse])
async def list_claims(use_case: FromDishka[ListBoardClaimsUseCase]) -> list[BoardClaimResponse]:
    """Возвращает платы, которые ждут, что их заберут.

    Args:
        use_case: Список открытых предложений.

    Returns:
        list[BoardClaimResponse]: Предложения с токеном, кодом и сроком.
    """
    return [claim_of(claim) for claim in await use_case.execute()]


@router.post("/claims", status_code=status.HTTP_201_CREATED, response_model=BoardResponse)
async def claim_board(
    body: ClaimBoardBody,
    user_id: CurrentUserId,
    use_case: FromDishka[ClaimBoardUseCase],
) -> BoardResponse:
    """Забирает объявленную плату за текущим аккаунтом.

    Этот шаг заменяет ввод ключа сопряжения в прошивку: плата выработала ключ
    сама, интерфейс предлагает его, и нажавший кнопку становится владельцем.

    Args:
        body: Токен предложения и выбранное имя платы.
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Взятие платы.

    Returns:
        BoardResponse: Плата, которая теперь сопряжена.
    """
    board = await use_case.execute(user_id, claim_command(body))
    return board_of(board)


@router.get("", response_model=list[BoardResponse])
async def list_boards(
    user_id: CurrentUserId,
    use_case: FromDishka[ListBoardsUseCase],
) -> list[BoardResponse]:
    """Возвращает платы, сопряжённые с текущим аккаунтом.

    Args:
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Список плат с живой доступностью.

    Returns:
        list[BoardResponse]: Платы аккаунта.
    """
    return [board_of(board) for board in await use_case.execute(user_id)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=BoardPairedResponse)
async def pair_board(
    body: PairBoardBody,
    user_id: CurrentUserId,
    use_case: FromDishka[PairBoardUseCase],
) -> BoardPairedResponse:
    """Сопрягает плату с текущим аккаунтом.

    Ответ несёт ключ сопряжения ровно один раз: именно его плата должна
    предъявлять при звонке.

    Args:
        body: Имя платы и, возможно, выбранный человеком ключ.
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Сопряжение платы.

    Returns:
        BoardPairedResponse: Сопряжённая плата вместе с её ключом.
    """
    return paired_of(await use_case.execute(user_id, pair_command(body)))


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unpair_board(
    device_id: str,
    user_id: CurrentUserId,
    use_case: FromDishka[RevokeBoardUseCase],
) -> None:
    """Убирает плату из текущего аккаунта.

    Args:
        device_id: Идентификатор платы.
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Отзыв платы.

    Returns:
        None.
    """
    await use_case.execute(user_id, EspDeviceId.parse(device_id))
