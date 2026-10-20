"""State route.

The main screen of the interface shows the whole home at once, and the endpoint
returns it in one piece. The pieces come from the stored configuration and from
the live state of the account, and they are assembled by one use case, so the
numbers on the screen belong close enough together to be trusted.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from smart_home.application.use_cases.home.read_home_snapshot import (
    ReadHomeSnapshotUseCase,
)
from smart_home.presentation.api.schemas import (
    HomeStateResponse,
    ReadingResponse,
    automation_of,
    device_of,
    scenario_of,
)
from smart_home.presentation.api.security import CurrentUserId

router = APIRouter(route_class=DishkaRoute, tags=["state"])


@router.get("/state", response_model=HomeStateResponse)
async def home_state(
    user_id: CurrentUserId, use_case: FromDishka[ReadHomeSnapshotUseCase]
) -> HomeStateResponse:
    """Return the full snapshot shown on the main screen.

    Args:
        user_id: Owner resolved from the bearer token.
        use_case: Reading of the home of one account.

    Returns:
        HomeStateResponse: Snapshot of the home of the current user.
    """
    snapshot = await use_case.execute(user_id)
    return HomeStateResponse(
        board_online=snapshot.board_online,
        automation_suspended=snapshot.automation_suspended,
        reading=ReadingResponse(
            temperature=snapshot.reading.temperature,
            humidity=snapshot.reading.humidity,
        ),
        devices=[device_of(device) for device in snapshot.devices],
        automation=automation_of(snapshot.automation),
        active_scenarios=[scenario_of(scenario) for scenario in snapshot.active_scenarios],
    )
