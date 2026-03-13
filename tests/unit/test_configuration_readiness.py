from app.routers import configuration as configuration_router


def test_scheduler_readiness_requires_secret(monkeypatch):
    monkeypatch.delenv("SCHEDULER_SECRET", raising=False)

    readiness = configuration_router._scheduler_readiness(object())

    assert readiness.configuration_ready is False
    assert readiness.worker_schedule_tick_enabled is True
    assert readiness.secure_endpoints_enabled is True


def test_scheduler_readiness_reports_ready_to_deploy(monkeypatch):
    monkeypatch.setenv("SCHEDULER_SECRET", "configured-secret")

    readiness = configuration_router._scheduler_readiness(object())

    assert readiness.configuration_ready is True
    assert "ready to be deployed" in readiness.status.lower()
