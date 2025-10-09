from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from app.schemas.profile import ProfileCreate, ProfileOut

pytestmark = pytest.mark.anyio("asyncio")


def _extract_event_payload(event_spy: list[dict[str, object]]):
    assert event_spy, "Expected at least one Kafka event"
    return event_spy[0]


async def test_create_profile(client: AsyncClient, kafka_event_spy, set_current_user):
    user_id = set_current_user(f"user-{uuid4()}")
    payload = ProfileCreate(role="client", display_name="New Client", email="example@test.com")

    response = await client.post("/profiles", json=payload.model_dump())
    assert response.status_code == status.HTTP_201_CREATED

    data = ProfileOut(**response.json())
    assert data.user_id == user_id
    assert data.display_name == payload.display_name
    assert data.email == payload.email

    event = _extract_event_payload(kafka_event_spy)
    assert event["topic"].endswith("profiles.client.registered.v1")
    assert event["value"]["user_id"] == user_id


async def test_list_profiles(client: AsyncClient, sample_profile):
    response = await client.get("/profiles")
    assert response.status_code == status.HTTP_200_OK

    payload = response.json()
    assert payload["total"] >= 1
    assert any(item["id"] == str(sample_profile.id) for item in payload["items"])


async def test_get_profile(client: AsyncClient, sample_profile):
    response = await client.get(f"/profiles/{sample_profile.id}")
    assert response.status_code == status.HTTP_200_OK

    data = ProfileOut(**response.json())
    assert data.id == sample_profile.id
    assert data.user_id == sample_profile.user_id


async def test_update_profile(client: AsyncClient, sample_profile, set_current_user):
    set_current_user(sample_profile.user_id)
    update_payload = {"display_name": "Updated User"}
    response = await client.put(f"/profiles/{sample_profile.id}", json=update_payload)
    assert response.status_code == status.HTTP_200_OK

    data = ProfileOut(**response.json())
    assert data.display_name == update_payload["display_name"]


async def test_delete_profile(client: AsyncClient, sample_profile, set_current_user):
    set_current_user(sample_profile.user_id)
    response = await client.delete(f"/profiles/{sample_profile.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    follow_up = await client.get(f"/profiles/{sample_profile.id}")
    assert follow_up.status_code == status.HTTP_404_NOT_FOUND

async def test_upload_photo_storage_disabled(client: AsyncClient, sample_profile, set_current_user):
    set_current_user(sample_profile.user_id)
    response = await client.post(
        f"/profiles/{sample_profile.id}/photo",
        files={"file": ("photo.jpg", b"binary-data", "image/jpeg")},
    )
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["detail"] == "Media storage is not configured"


async def test_create_profile_updates_existing_same_user(client: AsyncClient, set_current_user):
    user_id = set_current_user(f"user-{uuid4()}")
    payload1 = ProfileCreate(role="provider", display_name="Walker One", email="walker@example.com")

    resp1 = await client.post("/profiles", json=payload1.model_dump())
    assert resp1.status_code == status.HTTP_201_CREATED
    first_profile = ProfileOut(**resp1.json())

    payload2 = ProfileCreate(role="provider", display_name="Walker Updated", email="walker@example.com", city="Canelones")

    resp2 = await client.post("/profiles", json=payload2.model_dump())
    assert resp2.status_code == status.HTTP_200_OK
    updated_profile = ProfileOut(**resp2.json())

    assert updated_profile.id == first_profile.id
    assert updated_profile.display_name == payload2.display_name
    assert updated_profile.city == payload2.city
    assert updated_profile.user_id == user_id


async def test_create_profile_conflict_on_existing_email_other_user(client: AsyncClient, set_current_user):
    primary_user = set_current_user(f"user-{uuid4()}")
    payload = ProfileCreate(role="provider", display_name="Walker One", email="walker2@example.com")
    resp1 = await client.post("/profiles", json=payload.model_dump())
    assert resp1.status_code == status.HTTP_201_CREATED

    other_user = f"user-{uuid4()}"
    set_current_user(other_user)
    resp2 = await client.post("/profiles", json=payload.model_dump())
    assert resp2.status_code == status.HTTP_409_CONFLICT
    assert resp2.json()["detail"] == "Profile already exists (user_id/email/document)"
