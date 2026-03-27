"""Smoke test: app builder schema tables exist and accept inserts."""
import os
import uuid
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_INTEGRATION") == "1"
    or not os.environ.get("SUPABASE_URL")
    or not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
    reason="Integration tests skipped (SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY not set)"
)


def test_app_projects_insert_and_read():
    """Insert a project, read it back, delete it."""
    from app.services.supabase_client import get_service_client
    client = get_service_client()
    project_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())  # fake user for test

    # Insert
    result = client.table("app_projects").insert({
        "id": project_id,
        "user_id": user_id,
        "title": "Test Bakery Site",
        "status": "draft",
        "stage": "questioning",
    }).execute()
    assert result.data, "Insert returned no data"
    assert result.data[0]["id"] == project_id

    # Read back
    fetched = client.table("app_projects").select("*").eq("id", project_id).single().execute()
    assert fetched.data["title"] == "Test Bakery Site"

    # Insert linked screen
    screen_result = client.table("app_screens").insert({
        "project_id": project_id,
        "user_id": user_id,
        "name": "Home",
        "device_type": "DESKTOP",
    }).execute()
    assert screen_result.data

    # Clean up
    client.table("app_screens").delete().eq("project_id", project_id).execute()
    client.table("app_projects").delete().eq("id", project_id).execute()


def test_screen_variants_foreign_key():
    """screen_variants references app_screens; inserting with invalid screen_id must fail."""
    from app.services.supabase_client import get_service_client
    client = get_service_client()
    with pytest.raises(Exception):
        client.table("screen_variants").insert({
            "screen_id": str(uuid.uuid4()),  # non-existent
            "user_id": str(uuid.uuid4()),
        }).execute()
