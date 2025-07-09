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
    '''Fixture for a mocked aiohttp.ClientSession.'''
    # Create a MagicMock for the session itself, as ClientSession is not awaitable directly
    session_mock = MagicMock(spec=aiohttp.ClientSession)
    
    # Configure common methods like get, post, delete to BE AsyncMock instances
    # so they can be awaited and have await-specific assertions.
    session_mock.get = AsyncMock()
    session_mock.post = AsyncMock()
    session_mock.delete = AsyncMock()
    
    # close() is usually a synchronous method on ClientSession, but if it's called via 'async with',
    # its __aexit__ might be awaited. If it's just called as session.close(), it's not async.
    # For simplicity, if it needs to be awaited, it should also be an AsyncMock.
    # If it's synchronous, MagicMock is fine. Let's assume it might be used in an async context.
    session_mock.close = AsyncMock() 
    return session_mock

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
    # This is the mock for the actual response content (e.g., what response.json() would yield from)
    mock_response_data_container = AsyncMock() 
    mock_response_data_container.status = 200
    expected_broadcaster_id = event_manager.broadcaster_user_id
    mock_response_data_container.json = AsyncMock(return_value={
        "data": [
            {"id": "s1", "broadcaster_user_id": expected_broadcaster_id, "type": "channel.followed"},
            {"id": "s2", "broadcaster_user_id": expected_broadcaster_id, "type": "channel.subscribed"}
        ]
    })
    
    # Get the AsyncMock for session.get() from the fixture
    mock_session_get_method = mock_kick_client.session.get
    
    # Configure this AsyncMock to also act as an async context manager
    # Its __aenter__ should yield the response data container.
    mock_session_get_method.__aenter__ = AsyncMock(return_value=mock_response_data_container)
    mock_session_get_method.__aexit__ = AsyncMock(return_value=False)
    
    # If session.get() itself is awaited (outside async with), it should also logically yield the response data or similar.
    # For async with, the __aenter__ is primary. Let's ensure its direct return (if awaited) is also consistent.
    # However, aiohttp.session.get() returns a _RequestContextManager, not the final response directly when awaited.
    # The _RequestContextManager itself is the context manager. So the above __aenter__/__aexit__ is key.
    # We don't need to set mock_session_get_method.return_value if it's used directly by 'async with'.
    # 'async with' will use __aenter__ and __aexit__ if present on the object returned by the expression. 
    # If the expression itself (session.get()) is awaitable and returns the context manager, that's handled.
    # Here, session.get() *is* the context manager mock.

    subscriptions = await event_manager.list_subscriptions()
    
    assert subscriptions is not None, "list_subscriptions should not return None on success"
    assert len(subscriptions) == 2
    assert subscriptions[0]["id"] == "s1"
    assert subscriptions[1]["id"] == "s2"
    assert "s1" in event_manager.active_subscription_ids
    assert "s2" in event_manager.active_subscription_ids

@pytest.mark.asyncio
async def test_list_subscriptions_api_error(event_manager, mock_kick_client):
    '''Test API error when listing subscriptions.'''
    
    # This is the mock for the actual response content (e.g., aiohttp.ClientResponse content part)
    mock_response_content = AsyncMock()
    mock_response_content.status = 500
    mock_response_content.text = AsyncMock(return_value="Server Error")

    # This is the mock for the async context manager (e.g., aiohttp.ClientResponse itself)
    # It should NOT be an AsyncMock itself, but its __aenter__/__aexit__ should be.
    mock_response_context_manager = MagicMock() # Use MagicMock for the context manager object
    mock_response_context_manager.__aenter__ = AsyncMock(return_value=mock_response_content)
    mock_response_context_manager.__aexit__ = AsyncMock(return_value=False) # Or True, or None depending on desired exit behavior

    # mock_kick_client.session.get is an AsyncMock (from the fixture). 
    # Configure its return_value when it's awaited.
    mock_kick_client.session.get.return_value = mock_response_context_manager

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
    
    # This is the mock for the actual response content (e.g., aiohttp.ClientResponse content part)
    mock_response_content = AsyncMock()
    mock_response_content.status = 200
    mock_response_content.json = AsyncMock(return_value={
        "data": [
            {"event": "channel.subscribed", "subscription_id": "new_sub_1", "error": None, "name": "channel.subscribed"}
        ]
    })

    # This is the mock for the async context manager (e.g., aiohttp.ClientResponse itself)
    # It should not be an AsyncMock itself, but its __aenter__/__aexit__ should be.
    mock_response_context_manager = MagicMock()
    mock_response_context_manager.__aenter__ = AsyncMock(return_value=mock_response_content)
    mock_response_context_manager.__aexit__ = AsyncMock(return_value=False)
    
    # mock_kick_client.session.post is an AsyncMock (from fixture). 
    # When awaited, it returns the mock_response_context_manager.
    mock_kick_client.session.post.return_value = mock_response_context_manager

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
    # This is the mock for the actual response content
    mock_response_content = AsyncMock()
    mock_response_content.status = 200 # API itself returns 200, but payload indicates partial failure
    mock_response_content.json = AsyncMock(return_value={
        "data": [
            {"event": "channel.subscribed", "subscription_id": "new_sub_ok", "error": None},
            {"event": "channel.followed", "subscription_id": None, "error": "some_error"}
        ]
    })

    # This is the mock for the async context manager
    mock_response_context_manager = MagicMock()
    mock_response_context_manager.__aenter__ = AsyncMock(return_value=mock_response_content)
    mock_response_context_manager.__aexit__ = AsyncMock(return_value=False)
    mock_kick_client.session.post.return_value = mock_response_context_manager
    
    success = await event_manager.subscribe_to_events(events)
    
    assert success is True # True because at least one succeeded
    assert "new_sub_ok" in event_manager.active_subscription_ids

@pytest.mark.asyncio
async def test_subscribe_to_events_all_fail_in_payload(event_manager, mock_kick_client):
    '''Test subscribing when API returns 200 but all events in payload failed.'''
    events = [{"name": "channel.subscribed", "version": 1}]
    # This is the mock for the actual response content
    mock_response_content = AsyncMock()
    mock_response_content.status = 200
    mock_response_content.json = AsyncMock(return_value={
        "data": [
            {"event": "channel.subscribed", "subscription_id": None, "error": "failed_to_subscribe"}
        ]
    })
    # This is the mock for the async context manager
    mock_response_context_manager = MagicMock()
    mock_response_context_manager.__aenter__ = AsyncMock(return_value=mock_response_content)
    mock_response_context_manager.__aexit__ = AsyncMock(return_value=False)
    mock_kick_client.session.post.return_value = mock_response_context_manager
    
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
    # This is the mock for the actual response content
    mock_response_content = AsyncMock()
    mock_response_content.status = 400
    mock_response_content.text = AsyncMock(return_value="Bad Request")

    # This is the mock for the async context manager
    mock_response_context_manager = MagicMock()
    mock_response_context_manager.__aenter__ = AsyncMock(return_value=mock_response_content)
    mock_response_context_manager.__aexit__ = AsyncMock(return_value=False)
    mock_kick_client.session.post.return_value = mock_response_context_manager

    success = await event_manager.subscribe_to_events(events)
    assert success is False
    assert not event_manager.active_subscription_ids

# --- Test _unsubscribe_by_ids ---  
@pytest.mark.asyncio
async def test_unsubscribe_by_ids_success(event_manager, mock_kick_client):
    '''Test unsubscribing by IDs successfully.'''
    event_manager.active_subscription_ids = ["id1", "id2", "id3"]
    ids_to_remove = ["id1", "id3"]
    
    # This is the mock for the actual response content
    mock_response_content = AsyncMock()
    mock_response_content.status = 204 # No Content for successful DELETE
    
    # This is the mock for the async context manager
    mock_response_context_manager = MagicMock()
    mock_response_context_manager.__aenter__ = AsyncMock(return_value=mock_response_content)
    mock_response_context_manager.__aexit__ = AsyncMock(return_value=None) # Typically None for __aexit__
    mock_kick_client.session.delete.return_value = mock_response_context_manager # session.delete() is awaitable, returns the context manager
    
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
    # This is the mock for the actual response content
    mock_response_content = AsyncMock()
    mock_response_content.status = 500
    mock_response_content.text = AsyncMock(return_value="Server Error")

    # This is the mock for the async context manager
    mock_response_context_manager = MagicMock()
    mock_response_context_manager.__aenter__ = AsyncMock(return_value=mock_response_content)
    mock_response_context_manager.__aexit__ = AsyncMock(return_value=None)
    mock_kick_client.session.delete.return_value = mock_response_context_manager

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