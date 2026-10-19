"""Free-form command route."""

from __future__ import annotations

from fastapi import APIRouter

from backend.application.dto.command import ProcessUserCommand
from backend.presentation.api.requests import CommandBody
from backend.presentation.api.responses import CommandResponse
from backend.presentation.api.security import AppContainer, CurrentUserId

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("")
async def run_command(
    body: CommandBody, container: AppContainer, user_id: CurrentUserId
) -> CommandResponse:
    """Execute a free-form command through the natural language pipeline.

    The Telegram interface and a future voice interface use the very same use
    case, so the command path never depends on the delivery mechanism.

    Args:
        body: Raw command text.
        container: Assembled dependency graph.
        user_id: Owner resolved from the bearer token.

    Returns:
        CommandResponse: Structured answer.
    """
    result = await container.process_user_command.execute(
        user_id, ProcessUserCommand(text=body.text)
    )
    return CommandResponse.from_result(result)
