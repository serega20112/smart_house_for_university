"""Маршруты сценариев.

Сценарий — обещание, данное человеком собственному дому, поэтому интерфейс его
только ставит, перечисляет и отменяет. Всё, что происходит после, относится к
фоновым циклам системы.
"""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

from backend.application.use_cases.scenarios.cancel_scenario import CancelScenarioUseCase
from backend.application.use_cases.scenarios.list_scenarios import ListScenariosUseCase
from backend.application.use_cases.scenarios.schedule_scenario import ScheduleScenarioUseCase
from backend.domain.identifiers import ScenarioId
from backend.presentation.api.requests.scenarios import ScenarioCreateBody, schedule_command
from backend.presentation.api.responses.scenarios import ScenarioResponse, scenario_of
from backend.presentation.security_helpers import CurrentUserId

router = APIRouter(route_class=DishkaRoute, prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioResponse])
async def list_scenarios(
    user_id: CurrentUserId, use_case: FromDishka[ListScenariosUseCase]
) -> list[ScenarioResponse]:
    """Возвращает все сценарии текущего аккаунта.

    Args:
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Список сценариев.

    Returns:
        list[ScenarioResponse]: Сценарии аккаунта.
    """
    return [scenario_of(scenario) for scenario in await use_case.execute(user_id)]


@router.post("", response_model=ScenarioResponse)
async def schedule_scenario(
    body: ScenarioCreateBody,
    user_id: CurrentUserId,
    use_case: FromDishka[ScheduleScenarioUseCase],
) -> ScenarioResponse:
    """Ставит сценарий, который ждёт своего момента.

    Args:
        body: Отложенное действие, которое попросил человек.
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Постановка сценария.

    Returns:
        ScenarioResponse: Сохранённый сценарий.
    """
    scenario = await use_case.execute(user_id, schedule_command(body))
    return scenario_of(scenario)


@router.delete("/{scenario_id}", response_model=ScenarioResponse)
async def cancel_scenario(
    scenario_id: str,
    user_id: CurrentUserId,
    use_case: FromDishka[CancelScenarioUseCase],
) -> ScenarioResponse:
    """Отдаёт сценарий.

    Args:
        scenario_id: Идентификатор сценария.
        user_id: Владелец, разрешённый из bearer-токена.
        use_case: Отмена сценария.

    Returns:
        ScenarioResponse: Отменённый сценарий.
    """
    scenario = await use_case.execute(user_id, ScenarioId.parse(scenario_id))
    return scenario_of(scenario)
