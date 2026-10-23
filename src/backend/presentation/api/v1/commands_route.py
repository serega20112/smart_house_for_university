"""Маршрут свободной команды.

Написанное предложение уходит в шину: оно понимается, попадает к сценарию своего
намерения и получает ответ составителя фраз прикладного слоя. Кроме формы ответа
здесь ничего о команде не решается.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from backend.application.services.command_dispatcher import CommandDispatcher
from backend.presentation.api.requests.commands import CommandBody
from backend.presentation.api.responses.commands import CommandResponse, command_of
from backend.presentation.messages import CommandReplyComposer
from backend.presentation.security_helpers import CurrentUserId

router = APIRouter(route_class=DishkaRoute, tags=["commands"])


@router.post("/commands", response_model=CommandResponse)
async def submit_command(
    body: CommandBody,
    user_id: CurrentUserId,
    dispatcher: FromDishka[CommandDispatcher],
) -> CommandResponse:
    """Понимает предложение и выполняет то, о нём просят.

    Args:
        body: Предложение таким, каким его ввели.
        user_id: Владелец, разрешённый из bearer-токена.
        dispatcher: Шина команд прикладного слоя.

    Returns:
        CommandResponse: То, что дало выполнение команды.

    Raises:
        CommandNotUnderstoodError: Когда предложение нельзя выполнить как оно есть.
    """
    reply = await dispatcher.dispatch(user_id, body.text)
    return command_of(reply, CommandReplyComposer().for_result(reply))
