"""Маршруты живости и готовности сервиса."""

from __future__ import annotations

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Response, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from backend import __version__
from backend.config import Settings
from backend.infrastructure.system import metrics
from backend.infrastructure.system.logging import get_logger
from backend.presentation.api.responses.common import HealthResponse, ReadyResponse

router = APIRouter(route_class=DishkaRoute, tags=["system"])

log = get_logger("api.health")


@router.get("/health", response_model=HealthResponse)
async def health(settings: FromDishka[Settings]) -> HealthResponse:
    """Возвращает доступность сервиса.

    Args:
        settings: Конфигурация запущенного процесса.

    Returns:
        HealthResponse: Название, версия и признак жизни сервиса.
    """
    return HealthResponse(status="ok", name=settings.app_name, version=__version__)


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """Отдаёт снимок метрик в текстовом формате Prometheus.

    Returns:
        Response: Экспорт реестра метрик для сборщика.
    """
    return Response(
        content=metrics.render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready(
    engine: FromDishka[AsyncEngine],
    redis: FromDishka[Redis],
) -> Response:
    """Проверяет готовность сервиса принимать запросы.

    В отличие от живости, ответ на этот вопрос зависит от внешних систем: без базы
    и Redis сервис формально запущен, но дела делать не может. Отказ любой зависимости
    отдаёт 503, чтобы балансировщик не слал трафик на полуживой процесс.

    Args:
        engine: Движок PostgreSQL, к которому открывается проверка.
        redis: Соединение Redis, которое пингуется.

    Returns:
        Response: Готовность с ответом каждой зависимости и кодом 200 или 503.
    """
    dependencies = {
        "database": await _database_reachable(engine),
        "redis": await _redis_reachable(redis),
    }
    all_ready = all(dependencies.values())
    code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    body = ReadyResponse(status="ready" if all_ready else "unavailable", dependencies=dependencies)
    return Response(status_code=code, content=body.model_dump_json(), media_type="application/json")


async def _database_reachable(engine: AsyncEngine) -> bool:
    """Отвечает, открывается ли соединение с базой и читается ли 1.

    Args:
        engine: Движок PostgreSQL.

    Returns:
        bool: True, когда запрос `SELECT 1` прошёл.
    """
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as error:
        log.warning("readiness.database_unreachable", error=str(error))
        return False
    return True


async def _redis_reachable(redis: Redis) -> bool:
    """Отвечает, отвечает ли Redis на пинг.

    Args:
        redis: Соединение Redis.

    Returns:
        bool: True, когда пинг прошёл.
    """
    try:
        return bool(await redis.ping())
    except Exception as error:
        log.warning("readiness.redis_unreachable", error=str(error))
        return False
