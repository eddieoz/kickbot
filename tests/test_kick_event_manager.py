'''
Tests for the KickEventManager class.
'''
import pytest
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

# Adjust the import path based on your project structure
from kickbot.kick_event_manager import KickEventManager, KICK_API_BASE_URL
from kickbot.kick_auth_manager import KickAuthManager # Assuming this can be mocked
from kickbot.kick_client import KickClient # Assuming this can be mocked

@pytest.fixture
def mock_auth_manager():
    '''Fixture for a mocked KickAuthManager.'''
    mock = AsyncMock(spec=KickAuthManager)
    mock.get_valid_token = AsyncMock(return_value="test_access_token")
    return mock

@pytest.fixture
def mock_kick_client_session():
    '''Fixture for a mocked aiohttp ClientSession within KickClient.'''
    mock_session = AsyncMock(spec=aiohttp.ClientSession) # If aiohttp is directly used by KEM
    # If KEM uses client.session.get/post/delete, then mock client.session
    return mock_session

@pytest.fixture
def mock_kick_client(mock_kick_client_session):
    '''Fixture for a mocked KickClient.'''
    mock = MagicMock(spec=KickClient)
    # The KickEventManager expects client.session to be an aiohttp.ClientSession like object
    mock.session = mock_kick_client_session 
    return mock

@pytest.fixture
def event_manager(mock_auth_manager, mock_kick_client):
    '''Fixture for a KickEventManager instance with mocked dependencies.'''
    return KickEventManager(auth_manager=mock_auth_manager, client=mock_kick_client, broadcaster_user_id=12345)

# --- Test _get_headers ---  
@pytest.mark.asyncio
async def test_get_headers_success(event_manager, mock_auth_manager):
    '''Test _get_headers successfully retrieves a token and formats headers.'''
    headers = await event_manager._get_headers()
    mock_auth_manager.get_valid_token.assert_awaited_once()
    assert headers["Authorization"] == "Bearer test_access_token"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"

@pytest.mark.asyncio
async def test_get_headers_no_token(event_manager, mock_auth_manager):
    '''Test _get_headers raises an exception if no token is available.'''
    mock_auth_manager.get_valid_token = AsyncMock(return_value=None)
    with pytest.raises(Exception, match="Failed to get valid access token"):
        await event_manager._get_headers()

# --- Test list_subscriptions ---  
@pytest.mark.asyncio
async def test_list_subscriptions_success(event_manager, mock_kick_client):
    '''Test listing subscriptions successfully.'''
    mock_http_response = AsyncMock() 
    mock_http_response.status = 200
    # Ensure mock data includes broadcaster_user_id matching the event_manager's ID
    expected_broadcaster_id = event_manager.broadcaster_user_id
    mock_http_response.json = AsyncMock(return_value={
        "data": [
            {"id": "s1", "broadcaster_user_id": expected_broadcaster_id, "type": "channel.followed"},
            {"id": "s2", "broadcaster_user_id": expected_broadcaster_id, "type": "channel.subscribed"}
        ]
    })
    
    # session.get() should return an async context manager.
    mock_get_context_manager = AsyncMock()
    mock_get_context_manager.__aenter__.return_value = mock_http_response
    mock_get_context_manager.__aexit__ = AsyncMock(return_value=False) # Ensure it's an awaitable mock

    mock_kick_client.session.get.return_value = mock_get_context_manager
    
    subscriptions = await event_manager.list_subscriptions()
    
    assert len(subscriptions) == 2
    assert subscriptions[0]["id"] == "s1"
    assert subscriptions[1]["id"] == "s2"
    assert "s1" in event_manager.active_subscription_ids
    assert "s2" in event_manager.active_subscription_ids

@pytest.mark.asyncio
async def test_list_subscriptions_api_error(event_manager, mock_kick_client):
    '''Test API error when listing subscriptions.'''
    mock_http_response = AsyncMock()
    mock_http_response.status = 500
    mock_http_response.text = AsyncMock(return_value="Server Error")

    mock_kick_client.session.get = AsyncMock(return_value=mock_http_response)

    subscriptions = await event_manager.list_subscriptions()
    assert subscriptions is None
    assert not event_manager.active_subscription_ids # Should not be updated on error

@pytest.mark.asyncio
async def test_list_subscriptions_no_token_propagates(event_manager, mock_auth_manager):
    '''Test list_subscriptions returns None if token acquisition fails.'''
    mock_auth_manager.get_valid_token = AsyncMock(return_value=None)
    # Exception from _get_headers should be caught by list_subscriptions and result in None
    result = await event_manager.list_subscriptions()
    assert result is None

# --- Test subscribe_to_events ---  
@pytest.mark.asyncio
async def test_subscribe_to_events_success(event_manager, mock_kick_client):
    '''Test subscribing to events successfully.'''
    events = [{"name": "channel.subscribed", "version": 1}]
    
    # 1. This will be the ClientResponse object
    mock_http_client_response = AsyncMock()
    mock_http_client_response.status = 200
    mock_http_client_response.json = AsyncMock(return_value={
        "data": [
            {"event": "channel.subscribed", "subscription_id": "new_sub_1", "error": None, "name": "channel.subscribed"}
        ]
    })
    # Make it an async context manager
    mock_http_client_response.__aenter__ = AsyncMock(return_value=mock_http_client_response)
    mock_http_client_response.__aexit__ = AsyncMock(return_value=False)

    # Ensure the event_manager uses this patched session or its client uses the patched session
    # This depends on how event_manager.client.session is structured.
    # For this to work, event_manager.client.session must be a real aiohttp.ClientSession 
    # or the mock_kick_client fixture must be set up such that its .session.post is the patched one.
    # A simpler way if mock_kick_client is already in use by event_manager:
    mock_kick_client.session.post = lambda *args, **kwargs: mock_http_client_response

    success = await event_manager.subscribe_to_events(events)
    
    assert success is True
    mock_kick_client.session.post.assert_awaited_once()

@pytest.mark.asyncio
async def test_subscribe_to_events_partial_success(event_manager, mock_kick_client):
    '''Test subscribing to events with partial success/failure from API.'''
    events = [
        {"name": "channel.subscribed", "version": 1},
        {"name": "channel.followed", "version": 1}
    ]
    mock_http_response = AsyncMock()
    mock_http_response.status = 200 # API itself returns 200, but payload indicates partial failure
    mock_http_response.json = AsyncMock(return_value={
        "data": [
            {"event": "channel.subscribed", "subscription_id": "new_sub_ok", "error": None},
            {"event": "channel.followed", "subscription_id": None, "error": "some_error"}
        ]
    })
    mock_http_client_response = AsyncMock()
    mock_http_client_response.status = 200
    mock_http_client_response.json = AsyncMock(return_value={
        "data": [
            {"event": "channel.subscribed", "subscription_id": "new_sub_ok", "error": None},
            {"event": "channel.followed", "subscription_id": None, "error": "some_error"}
        ]
    })
    mock_http_client_response.__aenter__ = AsyncMock(return_value=mock_http_client_response)
    mock_http_client_response.__aexit__ = AsyncMock(return_value=False)
    mock_kick_client.session.post = lambda *args, **kwargs: mock_http_client_response
    
    success = await event_manager.subscribe_to_events(events)
    
    assert success is True # True because at least one succeeded
    assert "new_sub_ok" in event_manager.active_subscription_ids

@pytest.mark.asyncio
async def test_subscribe_to_events_all_fail_in_payload(event_manager, mock_kick_client):
    '''Test subscribing when API returns 200 but all events in payload failed.'''
    events = [{"name": "channel.subscribed", "version": 1}]
    mock_http_response = AsyncMock()
    mock_http_response.status = 200
    mock_http_response.json = AsyncMock(return_value={
        "data": [
            {"event": "channel.subscribed", "subscription_id": None, "error": "failed_to_subscribe"}
        ]
    })
    mock_http_client_response = AsyncMock()
    mock_http_client_response.status = 200
    mock_http_client_response.json = AsyncMock(return_value={
        "data": [
            {"event": "channel.subscribed", "subscription_id": None, "error": "failed_to_subscribe"}
        ]
    })
    mock_http_client_response.__aenter__ = AsyncMock(return_value=mock_http_client_response)
    mock_http_client_response.__aexit__ = AsyncMock(return_value=False)
    mock_kick_client.session.post = lambda *args, **kwargs: mock_http_client_response
    
    success = await event_manager.subscribe_to_events(events)
    assert success is False
    assert not event_manager.active_subscription_ids

@pytest.mark.asyncio
async def test_subscribe_to_events_no_events_provided(event_manager, mock_kick_client):
    '''Test subscribing with no events provided.'''
    success = await event_manager.subscribe_to_events([])
    assert success is True # Should be true as no operation failed
    mock_kick_client.session.post.assert_not_called()

@pytest.mark.asyncio
async def test_subscribe_to_events_api_error(event_manager, mock_kick_client):
    '''Test API error during subscription.'''
    events = [{"name": "channel.subscribed", "version": 1}]
    mock_http_response = AsyncMock()
    mock_http_response.status = 400
    mock_http_response.text = AsyncMock(return_value="Bad Request")

    mock_http_client_response = AsyncMock()
    mock_http_client_response.status = 400
    mock_http_client_response.text = AsyncMock(return_value="Bad Request")
    mock_http_client_response.__aenter__ = AsyncMock(return_value=mock_http_client_response)
    mock_http_client_response.__aexit__ = AsyncMock(return_value=False)
    mock_kick_client.session.post = lambda *args, **kwargs: mock_http_client_response

    success = await event_manager.subscribe_to_events(events)
    assert success is False
    assert not event_manager.active_subscription_ids

# --- Test _unsubscribe_by_ids ---  
@pytest.mark.asyncio
async def test_unsubscribe_by_ids_success(event_manager, mock_kick_client):
    '''Test unsubscribing by IDs successfully.'''
    event_manager.active_subscription_ids = ["id1", "id2", "id3"]
    ids_to_remove = ["id1", "id3"]
    
    mock_http_response = AsyncMock()
    mock_http_response.status = 204 # No Content for successful DELETE
    
    mock_http_client_response = AsyncMock()
    mock_http_client_response.status = 204 # No Content for successful DELETE
    mock_http_client_response.__aenter__ = AsyncMock(return_value=mock_http_client_response)
    mock_http_client_response.__aexit__ = AsyncMock(return_value=None)
    mock_kick_client.session.delete = lambda *args, **kwargs: mock_http_client_response
    
    success = await event_manager._unsubscribe_by_ids(ids_to_remove)
    
    assert success is True
    mock_kick_client.session.delete.assert_awaited_once()
    args, kwargs = mock_kick_client.session.delete.await_args
    assert args[0] == f"{KICK_API_BASE_URL}/events/subscriptions"
    # Check params carefully, aiohttp expects list of tuples for multiple same-key params
    assert kwargs['params'] == [("id", "id1"), ("id", "id3")]
    assert event_manager.active_subscription_ids == ["id2"]

@pytest.mark.asyncio
async def test_unsubscribe_by_ids_no_ids(event_manager, mock_kick_client):
    '''Test unsubscribing with no IDs provided.'''
    success = await event_manager._unsubscribe_by_ids([])
    assert success is True
    mock_kick_client.session.delete.assert_not_called()

@pytest.mark.asyncio
async def test_unsubscribe_by_ids_api_error(event_manager, mock_kick_client):
    '''Test API error when unsubscribing.'''
    ids_to_remove = ["id1"]
    mock_http_response = AsyncMock()
    mock_http_response.status = 500
    mock_http_response.text = AsyncMock(return_value="Server Error")

    mock_http_client_response = AsyncMock()
    mock_http_client_response.status = 500
    mock_http_client_response.text = AsyncMock(return_value="Server Error")
    mock_http_client_response.__aenter__ = AsyncMock(return_value=mock_http_client_response)
    mock_http_client_response.__aexit__ = AsyncMock(return_value=None)
    mock_kick_client.session.delete = lambda *args, **kwargs: mock_http_client_response

    success = await event_manager._unsubscribe_by_ids(ids_to_remove)
    assert success is False
    assert event_manager.active_subscription_ids == ["id1"] # Should not change on error

# --- Test clear_all_my_broadcaster_subscriptions ---
@pytest.mark.asyncio
async def test_clear_all_my_broadcaster_subscriptions_success(event_manager):
    '''Test clearing all broadcaster subscriptions successfully.'''
    # Mock list_subscriptions to populate active_subscription_ids
    event_manager.list_subscriptions = AsyncMock(return_value=[
        {"id": "s1", "broadcaster_user_id": 12345},
        {"id": "s2", "broadcaster_user_id": 12345}
    ])
    # This will set event_manager.active_subscription_ids to ["s1", "s2"] internally via the mocked list_subscriptions
    
    # Mock _unsubscribe_by_ids to simulate success
    event_manager._unsubscribe_by_ids = AsyncMock(return_value=True)
    
    success = await event_manager.clear_all_my_broadcaster_subscriptions()
    
    assert success is True
    event_manager.list_subscriptions.assert_awaited_once()
    # Check that _unsubscribe_by_ids was called with the IDs found by list_subscriptions
    event_manager._unsubscribe_by_ids.assert_awaited_once_with(["s1", "s2"])

@pytest.mark.asyncio
async def test_clear_all_my_broadcaster_subscriptions_no_subs_found(event_manager):
    '''Test clearing when no subscriptions are found for the broadcaster.'''
    event_manager.list_subscriptions = AsyncMock(return_value=[]) # No subs for this broadcaster
    event_manager._unsubscribe_by_ids = AsyncMock()
    
    success = await event_manager.clear_all_my_broadcaster_subscriptions()
    
    assert success is True
    event_manager.list_subscriptions.assert_awaited_once()
    event_manager._unsubscribe_by_ids.assert_not_awaited() # Should not be called if no IDs

@pytest.mark.asyncio
async def test_clear_all_my_broadcaster_subscriptions_unsubscribe_fails(event_manager):
    '''Test clearing when _unsubscribe_by_ids fails.'''
    event_manager.list_subscriptions = AsyncMock(return_value=[
        {"id": "s1", "broadcaster_user_id": 12345}
    ])
    event_manager._unsubscribe_by_ids = AsyncMock(return_value=False) # Simulate unsubscribe failure
    
    success = await event_manager.clear_all_my_broadcaster_subscriptions()
    
    assert success is False
    event_manager.list_subscriptions.assert_awaited_once()
    event_manager._unsubscribe_by_ids.assert_awaited_once_with(["s1"])

# --- Test resubscribe_to_configured_events ---
@pytest.mark.asyncio
async def test_resubscribe_to_configured_events_all_success(event_manager):
    '''Test resubscribing successfully: clear succeeds, subscribe succeeds.'''
    configured_events = [{"name": "event.new", "version": 1}]
    
    event_manager.clear_all_my_broadcaster_subscriptions = AsyncMock(return_value=True)
    event_manager.subscribe_to_events = AsyncMock(return_value=True)
    
    success = await event_manager.resubscribe_to_configured_events(configured_events)
    
    assert success is True
    event_manager.clear_all_my_broadcaster_subscriptions.assert_awaited_once()
    event_manager.subscribe_to_events.assert_awaited_once_with(configured_events)

@pytest.mark.asyncio
async def test_resubscribe_clear_fails_subscribe_succeeds(event_manager):
    '''Test resubscribing: clear fails, but subscribe still attempts and succeeds.'''
    configured_events = [{"name": "event.new", "version": 1}]
    
    event_manager.clear_all_my_broadcaster_subscriptions = AsyncMock(return_value=False) # Clear fails
    event_manager.subscribe_to_events = AsyncMock(return_value=True) # Subscribe succeeds
    
    success = await event_manager.resubscribe_to_configured_events(configured_events)
    
    assert success is True # Overall considered success if subscribe works
    event_manager.clear_all_my_broadcaster_subscriptions.assert_awaited_once()
    event_manager.subscribe_to_events.assert_awaited_once_with(configured_events)

@pytest.mark.asyncio
async def test_resubscribe_subscribe_fails(event_manager):
    '''Test resubscribing: subscribe fails.'''
    configured_events = [{"name": "event.new", "version": 1}]
    
    event_manager.clear_all_my_broadcaster_subscriptions = AsyncMock(return_value=True) # Clear succeeds
    event_manager.subscribe_to_events = AsyncMock(return_value=False) # Subscribe fails
    
    success = await event_manager.resubscribe_to_configured_events(configured_events)
    
    assert success is False # Overall considered failure if subscribe fails
    event_manager.clear_all_my_broadcaster_subscriptions.assert_awaited_once()
    event_manager.subscribe_to_events.assert_awaited_once_with(configured_events)

@pytest.mark.asyncio
async def test_resubscribe_no_configured_events(event_manager):
    '''Test resubscribing with no configured events after clearing.'''
    event_manager.clear_all_my_broadcaster_subscriptions = AsyncMock(return_value=True)
    event_manager.subscribe_to_events = AsyncMock()
    
    success = await event_manager.resubscribe_to_configured_events([]) # No events
    
    assert success is True # Should be true if clearing was successful
    event_manager.clear_all_my_broadcaster_subscriptions.assert_awaited_once()
    event_manager.subscribe_to_events.assert_not_awaited()

# TODO: Add tests for KickBot integration points if they directly use KickEventManager methods
# For example, test that KickBot.run calls event_manager.resubscribe_to_configured_events
# and KickBot.shutdown calls event_manager.clear_all_my_broadcaster_subscriptions.
# These would typically go in a test_kick_bot.py file.

# Need to import aiohttp for spec if not already done where mock_kick_client_session is defined
# import aiohttp # Already imported at the top for mock_kick_client_session spec