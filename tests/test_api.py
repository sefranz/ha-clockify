"""Basic tests for the Clockify API client."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.clockify.api import ClockifyApiClient


@pytest.fixture
def mock_session():
    session = MagicMock()
    return session


@pytest.fixture
def client(mock_session):
    return ClockifyApiClient(mock_session, "test-api-key")


def _mock_response(data, status=200):
    resp = AsyncMock()
    resp.status = status
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value=data)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


@pytest.mark.asyncio
async def test_get_user(client, mock_session):
    user_data = {"id": "user123", "name": "Test User"}
    mock_session.request = MagicMock(return_value=_mock_response(user_data))

    result = await client.get_user()
    assert result == user_data
    mock_session.request.assert_called_once()
    call_args = mock_session.request.call_args
    assert call_args[0] == ("GET", "https://api.clockify.me/api/v1/user")


@pytest.mark.asyncio
async def test_get_workspaces(client, mock_session):
    workspaces = [{"id": "ws1", "name": "My Workspace"}]
    mock_session.request = MagicMock(return_value=_mock_response(workspaces))

    result = await client.get_workspaces()
    assert result == workspaces


@pytest.mark.asyncio
async def test_get_running_entry_none(client, mock_session):
    mock_session.request = MagicMock(return_value=_mock_response([]))

    result = await client.get_running_entry("ws1", "user1")
    assert result is None


@pytest.mark.asyncio
async def test_get_running_entry_found(client, mock_session):
    entry = {"id": "entry1", "description": "Working"}
    mock_session.request = MagicMock(return_value=_mock_response([entry]))

    result = await client.get_running_entry("ws1", "user1")
    assert result == entry


@pytest.mark.asyncio
async def test_start_entry(client, mock_session):
    created = {"id": "new-entry"}
    mock_session.request = MagicMock(return_value=_mock_response(created))

    result = await client.start_entry("ws1", project_id="proj1", description="Test")
    assert result == created
    call_args = mock_session.request.call_args
    assert call_args[0][0] == "POST"
    payload = call_args[1]["json"]
    assert payload["projectId"] == "proj1"
    assert payload["description"] == "Test"


@pytest.mark.asyncio
async def test_stop_entry(client, mock_session):
    stopped = {"id": "entry1", "timeInterval": {"end": "2024-01-01T12:00:00Z"}}
    mock_session.request = MagicMock(return_value=_mock_response(stopped))

    result = await client.stop_entry("ws1", "user1")
    assert result == stopped
    call_args = mock_session.request.call_args
    assert call_args[0][0] == "PATCH"
