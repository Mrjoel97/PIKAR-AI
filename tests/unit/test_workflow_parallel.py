"""Tests for workflow parallel step fixes."""


def test_check_requires_no_requirements():
    from app.workflows.step_executor import _check_requires
    assert _check_requires({}, set()) is True
    assert _check_requires({"name": "step1"}, {"group-a"}) is True


def test_check_requires_met():
    from app.workflows.step_executor import _check_requires
    step = {"requires": "content-batch"}
    assert _check_requires(step, {"content-batch", "other"}) is True


def test_check_requires_not_met():
    from app.workflows.step_executor import _check_requires
    step = {"requires": "content-batch"}
    assert _check_requires(step, {"other"}) is False


def test_check_requires_list():
    from app.workflows.step_executor import _check_requires
    step = {"requires": ["group-a", "group-b"]}
    assert _check_requires(step, {"group-a", "group-b"}) is True
    assert _check_requires(step, {"group-a"}) is False


def test_check_requires_string():
    from app.workflows.step_executor import _check_requires
    step = {"requires": "single-group"}
    assert _check_requires(step, {"single-group"}) is True
