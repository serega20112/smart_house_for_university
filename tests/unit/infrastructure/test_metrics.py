"""Метрики наблюдаемости накапливаются и отдаются в формате Prometheus.

Эти проверки сторожат правило из ТЗ: сбои и команды железу должны попадать в метрику, а
не только в журнал. Здесь проверяется, что запись исхода команды и длительности такта
проявляется в экспорте реестра — иначе алерт по деградации построить было бы не на чём.
"""

from __future__ import annotations

from backend.infrastructure.system import metrics


def test_rendered_metrics_expose_command_and_cycle_families() -> None:
    """После записи команда и такт видны в текстовом экспорте реестра.

    Returns:
        None: Только проверка содержимого экспорта.
    """
    metrics.record_board_command("accepted", 0.12)
    metrics.observe_cycle("automation", 0.5)
    metrics.count_cycle_error("scenario")
    metrics.set_board_sessions(3)

    exported = metrics.render().decode("utf-8")

    assert "smart_home_board_commands_total" in exported
    assert "smart_home_board_command_seconds" in exported
    assert "smart_home_cycle_seconds" in exported
    assert "smart_home_cycle_errors_total" in exported
    assert "smart_home_board_online 3.0" in exported
