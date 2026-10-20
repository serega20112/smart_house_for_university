"""Free-form command route.

A typed sentence and a spoken one enter the same bus: the sentence is understood,
routed to the handler of its intent and answered by the composer of the
presentation layer. Nothing about a command is decided here apart from the shape
of the answer.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from smart_home.application.services.command_dispatcher import CommandDispatcher
from smart_home.presentation.api.schemas import CommandBody, CommandResponse
from smart_home.presentation.api.security import CurrentUserId

router = APIRouter(route_class=DishkaRoute, tags=["commands"])


@router.post("/commands", response_model=CommandResponse)
async def submit_command(
    body: CommandBody,
    user_id: CurrentUserId,
    dispatcher: FromDishka[CommandDispatcher],
) -> CommandResponse:
    """Understand a sentence and carry out what it asks for.

    Args:
        body: Sentence as typed by the user.
        user_id: Owner resolved from the bearer token.
        dispatcher: Command bus of the application.

    Returns:
        CommandResponse: What carrying the command out produced.

    Raises:
        VoiceUnavailableError: When the understanding pipeline cannot answer.
    """
    reply = await dispatcher.dispatch(user_id, body.text)
    answer = dispatcher.compose(reply)
    return CommandResponse(
        intent=None if reply.intent is None else reply.intent.value,
        answer=answer,
        message=answer,
        details=reply.details,
    )
