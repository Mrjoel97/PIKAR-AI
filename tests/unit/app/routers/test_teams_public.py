from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.teams_public import router


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_get_invite_details_returns_public_metadata():
    expected = {
        "id": "invite-1",
        "workspaceName": "My Workspace",
        "role": "editor",
        "invitedEmail": "teammate@example.com",
        "inviterName": "Founder",
        "expiresAt": "2026-04-17T12:00:00+00:00",
        "isActive": True,
    }

    with patch("app.routers.teams_public.WorkspaceService") as service_cls:
        service_cls.return_value.get_invite_details = AsyncMock(return_value=expected)

        with _build_client() as client:
            response = client.get("/teams/invites/details", params={"token": "token-123"})

    assert response.status_code == 200
    assert response.json() == expected


def test_get_invite_details_maps_expired_invite_to_410():
    with patch("app.routers.teams_public.WorkspaceService") as service_cls:
        service_cls.return_value.get_invite_details = AsyncMock(
            side_effect=ValueError("This invitation has expired.")
        )

        with _build_client() as client:
            response = client.get("/teams/invites/details", params={"token": "token-123"})

    assert response.status_code == 410
    assert response.json()["detail"] == "This invitation has expired."
