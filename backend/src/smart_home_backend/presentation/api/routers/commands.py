"""Free-form command route."""

from __future__ import annotations

from fastapi import APIRouter, Request

from smart_home_backend.application.dto.command import ProcessUserCommand
from smart_home_backend.presentation.api.requests import CommandBody
from smart_home_backend.presentation.api.responses import CommandResponse
from smart_home_backend.presentation.dependencies import get_container

router = APIRouter(prefix="/commands", tags=["commands"])


@router.post("")
async def run_command(body: CommandBody, request: Request) -> CommandResponse:
    """Execute a free-form command through the natural language pipeline.

    The Telegram interface and a future voice interface use the very same use
    case, so the command path never depends on the delivery mechanism.

    Args:
        body: Raw command text.
        request: Incoming request carrying the dependency container.

    Returns:
        CommandResponse: Structured answer.
    """
    container = get_container(request)
    result = await container.process_user_command.execute(ProcessUserCommand(text=body.text))
    return CommandResponse.from_result(result)
