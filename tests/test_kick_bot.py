'''
Tests for KickBot integration, particularly with KickEventManager.
'''
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

# Adjust import paths as necessary
from kickbot.kick_bot import KickBot
from kickbot.kick_auth_manager import KickAuthManager
from kickbot.kick_event_manager import KickEventManager
from kickbot.kick_webhook_handler import KickWebhookHandler
from kickbot.kick_client import KickClient
# If Settings class is used directly, or if settings are loaded globally and need mocking:
# from utils.TwitchMarkovChain.Settings import Settings as MarkovSettings

# Default settings to be used and potentially overridden in tests
DEFAULT_BOT_SETTINGS = {
    "KickEmail": "test@example.com",
    "KickPass": "password",
    "KICK_CLIENT_ID": "test_client_id", # Used if KickAuthManager doesn't load from .env in test context
    "KICK_CLIENT_SECRET": "test_client_secret", # Same as above
    "KICK_REDIRECT_URL": "http://localhost/callback", # Same as above
    "KICK_OAUTH_SCOPES": ["events:subscribe", "user:read"],
    "KickWebhookEnabled": True,
    "KickWebhookPath": "/kick/testevents",
    "KickWebhookPort": 8888,
    "KickEventsToSubscribe": [
        {"name": "channel.subscribed", "version": 1},
        {"name": "channel.followed", "version": 1}
    ],
    "KickStreamer": "teststreamer", # Needed for set_streamer
    # Markov Chain specific settings (minimal for these tests)
    "Host": "irc.example.com",
    "Port": 6667,
    "Channel": "#teststreamer",
    "Nickname": "testbot",
    "Authentication": "oauth:fakekey",
    "DeniedUsers": [],
    "AllowedUsers": [],
    "Cooldown": 0,
    "KeyLength": 2,
    "MaxSentenceWordAmount": 10,
    "MinSentenceWordAmount": 1,
    "HelpMessageTimer": -1,
    "AutomaticGenerationTimer": -1,
    "WhisperCooldown": False,
    "EnableGenerateCommand": False,
    "SentenceSeparator": " - ",
    "AllowGenerateParams": False,
    "GenerateCommands": ["!g"]
}

@pytest.fixture
def mock_settings_file():
    '''Mocks the open() call for settings.json.'''
    # Use this to provide default or test-specific settings
    mock_file = mock_open(read_data=json.dumps(DEFAULT_BOT_SETTINGS))
    with patch('builtins.open', mock_file) as m:
        yield m

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mocks environment variables for KickAuthManager if it loads from os.environ."""
    monkeypatch.setenv("KICK_CLIENT_ID", "env_client_id")
    monkeypatch.setenv("KICK_CLIENT_SECRET", "env_client_secret")
    monkeypatch.setenv("KICK_REDIRECT_URI", "http://localhost/env_callback")
    monkeypatch.setenv("KICK_SCOPES", "events:subscribe user:read chatroom:read")

@pytest.fixture
async def kick_bot_instance(mock_settings_file, mock_env_vars):
    '''Fixture to create a KickBot instance with most dependencies mocked at a high level.
       Further patching might be needed for specific method calls within dependencies.
    '''
    # Patch dependencies that are instantiated by KickBot or its helpers
    with patch('kickbot.kick_bot.KickClient', spec=KickClient) as MockKickClient, \
         patch('kickbot.kick_bot.KickAuthManager', spec=KickAuthManager) as MockKickAuthManager, \
         patch('kickbot.kick_bot.KickEventManager', spec=KickEventManager) as MockKickEventManager, \
         patch('kickbot.kick_bot.KickWebhookHandler', spec=KickWebhookHandler) as MockKickWebhookHandler, \
         patch('kickbot.kick_bot.get_ws_uri', return_value="ws://localhost:faker") as mock_get_ws, \
         patch('kickbot.kick_bot.websockets.connect', new_callable=AsyncMock) as mock_ws_connect, \
         patch('kickbot.kick_bot.Settings') as MockMarkovSettings, \
         patch('kickbot.kick_bot.Database') as MockMarkovDatabase, \
         patch('kickbot.kick_bot.TwitchWebsocket') as MockTwitchWebsocket, \
         patch('kickbot.kick_bot.LoopingTimer') as MockLoopingTimer: 
        
        # Setup mocks for KickClient
        mock_kc_instance = AsyncMock(spec=KickClient)
        mock_kc_instance.session = AsyncMock(spec=aiohttp.ClientSession) # If session is directly accessed
        MockKickClient.return_value = mock_kc_instance
        
        # Setup mocks for KickAuthManager
        mock_kam_instance = AsyncMock(spec=KickAuthManager)
        mock_kam_instance.get_valid_token = AsyncMock(return_value="test_bot_token")
        MockKickAuthManager.return_value = mock_kam_instance
        
        # Setup mocks for KickEventManager
        mock_kem_instance = AsyncMock(spec=KickEventManager)
        mock_kem_instance.resubscribe_to_configured_events = AsyncMock(return_value=True)
        mock_kem_instance.clear_all_my_broadcaster_subscriptions = AsyncMock(return_value=True)
        MockKickEventManager.return_value = mock_kem_instance
        
        # Setup mocks for KickWebhookHandler
        mock_kwh_instance = AsyncMock(spec=KickWebhookHandler)
        # MockKWH.handle_webhook might be needed if it's directly called/tested
        MockKickWebhookHandler.return_value = mock_kwh_instance

        # Mock for websockets.connect within _poll
        mock_ws_connection = AsyncMock()
        mock_ws_connection.recv = AsyncMock(side_effect=asyncio.TimeoutError) # To make _poll loop without real messages
        mock_ws_connection.close = AsyncMock()
        mock_ws_connect.return_value.__aenter__.return_value = mock_ws_connection # for async with

        bot = KickBot(username=DEFAULT_BOT_SETTINGS["KickEmail"], password=DEFAULT_BOT_SETTINGS["KickPass"])
        
        # Simulate set_streamer call to populate streamer_info needed for EventManager init in run()
        # This part requires get_streamer_info etc. to be patched or self.client to be ready.
        # For this test, let's assume streamer_info is set manually for simplicity for now, or patch get_streamer_info
        with patch('kickbot.kick_bot.get_streamer_info', return_value=None) as mock_get_s_info, \
             patch('kickbot.kick_bot.get_chatroom_settings', return_value=None), \
             patch('kickbot.kick_bot.get_bot_settings', return_value=None):
            
            # Manually set streamer_info as get_streamer_info is complex to mock here without its own tests
            # and KickClient is also mocked. `run` method initializes the real `self.client`.
            # The key is that `self.streamer_info['id']` is available when KEM is initialized in `run`.
            bot.streamer_info = {"id": 98765, "username": "teststreamer"} # Mocked broadcaster ID
            bot.chatroom_id = 112233 # Mocked chatroom ID for _join_chatroom
            # bot.set_streamer(DEFAULT_BOT_SETTINGS["KickStreamer"]) # This would call actual helpers
        
        bot.MockKickClient = MockKickClient
        bot.MockKickAuthManager = MockKickAuthManager
        bot.MockKickEventManager = MockKickEventManager
        bot.MockKickWebhookHandler = MockKickWebhookHandler
        bot.mock_ws_connect = mock_ws_connect
        
        yield bot
        
        # Optional: Add cleanup if bot.run() was called and created tasks that need cancelling
        # This might be complex depending on what bot.run() starts.

import json # for mock_settings_file
import aiohttp # for KickClient session spec

@pytest.mark.asyncio
async def test_kickbot_run_subscribes_to_events(kick_bot_instance):
    '''Test KickBot.run subscribes to events if webhook is enabled.'''
    bot = kick_bot_instance
    bot.webhook_enabled = True # Ensure webhook is enabled for this test case
    bot.kick_events_to_subscribe = DEFAULT_BOT_SETTINGS["KickEventsToSubscribe"]
    
    # Patch _start_webhook_server and _poll to prevent them from fully running
    with patch.object(bot, '_start_webhook_server', new_callable=AsyncMock) as mock_start_webhook, \
         patch.object(bot, '_poll', new_callable=AsyncMock) as mock_poll:
        
        await bot.run()

        # Assertions
        mock_start_webhook.assert_awaited_once()
        
        # Check if KickEventManager was initialized correctly (this happens in run before subscribe call)
        # bot.MockKickEventManager.assert_called_once()
        # The instance mock_kem_instance is what we check methods on
        actual_kem_instance = bot.event_manager # Access the instance created in bot.run
        assert actual_kem_instance is not None
        actual_kem_instance.resubscribe_to_configured_events.assert_awaited_once_with(DEFAULT_BOT_SETTINGS["KickEventsToSubscribe"])
        mock_poll.assert_awaited_once()

@pytest.mark.asyncio
async def test_kickbot_run_no_subscribe_if_webhook_disabled(kick_bot_instance):
    '''Test KickBot.run does NOT subscribe if webhook is disabled.'''
    bot = kick_bot_instance
    bot.webhook_enabled = False # Disable webhook
    bot.kick_events_to_subscribe = DEFAULT_BOT_SETTINGS["KickEventsToSubscribe"]

    with patch.object(bot, '_start_webhook_server', new_callable=AsyncMock) as mock_start_webhook, \
         patch.object(bot, '_poll', new_callable=AsyncMock) as mock_poll:

        await bot.run()
        
        mock_start_webhook.assert_awaited_once() # Should still try to start/check webhook server status
        actual_kem_instance = bot.event_manager
        # Event manager might still be initialized if streamer_info is present,
        # but resubscribe should not be called.
        if actual_kem_instance:
            actual_kem_instance.resubscribe_to_configured_events.assert_not_awaited()
        mock_poll.assert_awaited_once()

@pytest.mark.asyncio
async def test_kickbot_run_no_subscribe_if_no_events_configured(kick_bot_instance):
    '''Test KickBot.run does NOT subscribe if no events are configured.'''
    bot = kick_bot_instance
    bot.webhook_enabled = True
    bot.kick_events_to_subscribe = [] # No events

    with patch.object(bot, '_start_webhook_server', new_callable=AsyncMock) as mock_start_webhook, \
         patch.object(bot, '_poll', new_callable=AsyncMock) as mock_poll:
        await bot.run()
        
        mock_start_webhook.assert_awaited_once()
        actual_kem_instance = bot.event_manager
        if actual_kem_instance:
             actual_kem_instance.resubscribe_to_configured_events.assert_not_awaited()
        mock_poll.assert_awaited_once()

@pytest.mark.asyncio
async def test_kickbot_shutdown_unsubscribes_from_events(kick_bot_instance):
    '''Test KickBot.shutdown unsubscribes from events.'''
    bot = kick_bot_instance
    # Simulate that EventManager was initialized and is active
    # The instance mock_kem_instance is from the fixture's patch
    bot.event_manager = bot.MockKickEventManager.return_value 
    
    # Patch _stop_webhook_server and http_session.close to prevent side effects
    with patch.object(bot, '_stop_webhook_server', new_callable=AsyncMock) as mock_stop_webhook, \
         patch.object(bot, 'http_session', MagicMock()) as mock_session_obj: # if http_session exists
        if bot.http_session: # Ensure it exists before trying to patch close
            mock_session_obj.close = AsyncMock()
        
        # Ensure ws_connection and ws (TwitchWebsocket for Markov) are handled
        bot.ws_connection = AsyncMock()
        bot.ws_connection.closed = False
        bot.ws = AsyncMock()
        bot.ws.stop = MagicMock()

        await bot.shutdown()
        
        # Assertions
        assert bot.event_manager is None # Should be reset after clearing
        bot.MockKickEventManager.return_value.clear_all_my_broadcaster_subscriptions.assert_awaited_once()
        mock_stop_webhook.assert_awaited_once()
        if bot.http_session:
             mock_session_obj.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_kickbot_event_manager_not_init_if_no_streamer_id(kick_bot_instance):
    '''Test KickEventManager is not initialized or used if streamer_id is missing.'''
    bot = kick_bot_instance
    bot.streamer_info = {} # Simulate missing streamer_id
    bot.webhook_enabled = True
    bot.kick_events_to_subscribe = DEFAULT_BOT_SETTINGS["KickEventsToSubscribe"]

    with patch.object(bot, '_start_webhook_server', new_callable=AsyncMock) as mock_start_webhook, \
         patch.object(bot, '_poll', new_callable=AsyncMock) as mock_poll:
        
        await bot.run()
        
        assert bot.event_manager is None
        # Check that MockKickEventManager was not called to create an instance
        bot.MockKickEventManager.assert_not_called()
        mock_poll.assert_awaited_once() 