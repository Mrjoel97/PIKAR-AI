from app.services.initiative_operational_state import normalize_operational_state


def test_normalize_operational_state_promotes_metadata_to_top_level():
    initiative = normalize_operational_state(
        {
            "id": "init-1",
            "title": "Launch new offer",
            "description": "Ship the first version",
            "phase": "ideation",
            "metadata": {
                "operational_state": {
                    "goal": "Launch new offer",
                    "success_criteria": ["Page live"],
                    "owner_agents": ["executive", "marketing"],
                    "primary_workflow": "Landing Page to Launch",
                    "deliverables": ["landing-page"],
                    "evidence": [{"type": "url", "value": "/landing/test"}],
                    "blockers": [{"status": "open", "message": "Awaiting approval"}],
                    "next_actions": ["Approve launch"],
                    "current_phase": "build",
                    "verification_status": "pending",
                    "trust_summary": {"approval_state": "pending"},
                }
            },
        }
    )

    assert initiative["goal"] == "Launch new offer"
    assert initiative["primary_workflow"] == "Landing Page to Launch"
    assert initiative["current_phase"] == "build"
    assert initiative["verification_status"] == "pending"
    assert initiative["trust_summary"]["approval_state"] == "pending"

