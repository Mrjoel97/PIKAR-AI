import pytest

from app.agents.tools import high_risk_workflow as tools


@pytest.mark.asyncio
async def test_approve_request_requires_fields():
    res = await tools.approve_request(request_type="", requester="alice")
    assert res["success"] is False
    assert res["status"] == "failed"


@pytest.mark.asyncio
async def test_execute_payroll_requires_approver():
    res = await tools.execute_payroll(pay_period="2026-02", total_amount=1000, currency="usd")
    assert res["success"] is False
    assert res["status"] == "failed"
    assert "approved_by" in res["error"]


@pytest.mark.asyncio
async def test_send_contract_validates_email():
    res = await tools.send_contract(
        recipient_email="not-an-email",
        contract_title="Master Service Agreement",
        contract_body="Terms",
    )
    assert res["success"] is False
    assert res["status"] == "failed"


@pytest.mark.asyncio
async def test_process_payment_validates_amount():
    res = await tools.process_payment(amount=0, currency="usd")
    assert res["success"] is False
    assert res["status"] == "failed"

