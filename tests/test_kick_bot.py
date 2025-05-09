'''
Tests for KickBot integration, particularly with KickEventManager.
'''
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pytest_asyncio import fixture as async_fixture
import aiohttp # Ensure aiohttp is imported for spec

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
        {"name": "channel.followed", "version": 1},
        {"name": "channel.subscription.new", "version": 1},
        {"name": "channel.subscription.gifts", "version": 1}
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
    "GenerateCommands": ["!g"],
    "FeatureFlags": {"EnableNewWebhookEventSystem": True, "DisableLegacyGiftEventHandling": False}
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

@async_fixture
async def mock_aiohttp_session():
    mock_session = AsyncMock(spec=aiohttp.ClientSession)
    # If it needs to be used in an 'async with' block, it might need __aenter__ and __aexit__ mocked
    # For now, just providing the mock instance
    yield mock_session
    # Add cleanup if necessary, e.g., await mock_session.close() if it were a real session

@pytest.fixture
def mock_os_path_exists():
    with patch('os.path.exists') as mock_exists:
        yield mock_exists

@pytest.fixture
def mock_builtin_open():
    with patch('builtins.open', new_callable=MagicMock) as mock_open:
        yield mock_open

@pytest.fixture
def MockKickClient():
    return MagicMock(spec=KickClient)

@pytest.fixture
def MockKickAuthManager():
    # ... (content of this fixture, ensure return_value has necessary methods like get_valid_token)
    mock = MagicMock(spec=KickAuthManager)
    mock.return_value.get_valid_token = AsyncMock(return_value="test_token")
    return mock

@pytest.fixture
def MockKickEventManager():
    return MagicMock(spec=KickEventManager)

@pytest.fixture
def MockKickWebhookHandler():
    return MagicMock(spec=KickWebhookHandler)

@async_fixture
async def kick_bot_instance(mock_aiohttp_session, mock_os_path_exists, mock_builtin_open, MockKickClient, MockKickAuthManager, MockKickEventManager, MockKickWebhookHandler):
    '''Fixture to create a KickBot instance with most dependencies mocked at a high level.
       Further patching might be needed for specific method calls within dependencies.
    '''
    # Patch dependencies that are instantiated by KickBot or its helpers
    with patch('kickbot.kick_bot.KickClient', spec=KickClient) as MockKickClient_fixture, \
         patch('kickbot.kick_bot.KickAuthManager', spec=KickAuthManager) as MockKickAuthManager_fixture, \
         patch('kickbot.kick_bot.KickEventManager', spec=KickEventManager) as MockKickEventManager_fixture, \
         patch('kickbot.kick_bot.KickWebhookHandler', spec=KickWebhookHandler) as MockKickWebhookHandler_fixture, \
         patch('kickbot.kick_bot.get_ws_uri', return_value="ws://localhost:faker") as mock_get_ws, \
         patch('kickbot.kick_bot.websockets.connect', new_callable=AsyncMock) as mock_ws_connect, \
         patch('kickbot.kick_bot.Settings') as MockMarkovSettings, \
         patch('kickbot.kick_bot.Database') as MockMarkovDatabase, \
         patch('kickbot.kick_bot.TwitchWebsocket') as MockTwitchWebsocket_fixture, \
         patch('kickbot.kick_bot.LoopingTimer') as MockLoopingTimer: 
        
        # Setup mocks for KickClient
        mock_kc_instance = AsyncMock(spec=KickClient)
        mock_kc_instance.session = AsyncMock(spec=aiohttp.ClientSession) # If session is directly accessed
        MockKickClient_fixture.return_value = mock_kc_instance
        
        # Setup mocks for KickAuthManager
        mock_kam_instance = AsyncMock(spec=KickAuthManager)
        mock_kam_instance.get_valid_token = AsyncMock(return_value="test_bot_token")
        MockKickAuthManager_fixture.return_value = mock_kam_instance
        
        # Setup mocks for KickEventManager
        mock_kem_instance = AsyncMock(spec=KickEventManager)
        mock_kem_instance.resubscribe_to_configured_events = AsyncMock(return_value=True)
        mock_kem_instance.clear_all_my_broadcaster_subscriptions = AsyncMock(return_value=True)
        MockKickEventManager_fixture.return_value = mock_kem_instance
        
        # Setup mocks for KickWebhookHandler
        mock_kwh_instance = AsyncMock(spec=KickWebhookHandler)
        MockKickWebhookHandler_fixture.return_value = mock_kwh_instance

        # Mock for websockets.connect within _poll
        mock_ws_connection = AsyncMock()
        mock_ws_connection.recv = AsyncMock(side_effect=asyncio.TimeoutError) # To make _poll loop without real messages
        mock_ws_connection.close = AsyncMock()
        mock_ws_connect.return_value.__aenter__.return_value = mock_ws_connection # for async with

        bot = KickBot(username=DEFAULT_BOT_SETTINGS["KickEmail"], password=DEFAULT_BOT_SETTINGS["KickPass"])
        bot.set_settings(DEFAULT_BOT_SETTINGS)
        
        # Simulate set_streamer call to populate streamer_info needed for EventManager init in run()
        with patch('kickbot.kick_bot.get_streamer_info', return_value=None) as mock_get_s_info, \
             patch('kickbot.kick_bot.get_chatroom_settings', return_value=None), \
             patch('kickbot.kick_bot.get_bot_settings', return_value=None):
            
            bot.streamer_info = {"id": 98765, "username": "teststreamer"} 
            bot.chatroom_id = 112233 
        
        bot.MockKickClient = MockKickClient_fixture
        bot.MockKickAuthManager = MockKickAuthManager_fixture
        bot.MockKickEventManager = MockKickEventManager_fixture
        bot.MockKickWebhookHandler = MockKickWebhookHandler_fixture
        bot.MockTwitchWebsocket_class_for_test = MockTwitchWebsocket_fixture
        bot.mock_ws_connect = mock_ws_connect
        
        yield bot
        
        # Optional: Add cleanup if bot.run() was called and created tasks that need cancelling
        # This might be complex depending on what bot.run() starts.

import json # for mock_settings_file

@pytest.mark.asyncio
async def test_kickbot_run_subscribes_to_events(kick_bot_instance):
    '''Test KickBot.run subscribes to events if webhook is enabled.'''
    bot = kick_bot_instance
    bot.webhook_enabled = True # Ensure webhook is enabled for this test case
    bot.enable_new_webhook_system = True # Ensure new system is enabled
    # Ensure other settings-derived attributes used in run() before KEM init are present
    bot.disable_legacy_gift_handling = DEFAULT_BOT_SETTINGS["FeatureFlags"]["DisableLegacyGiftEventHandling"]
    bot.webhook_path = DEFAULT_BOT_SETTINGS["KickWebhookPath"]
    bot.webhook_port = DEFAULT_BOT_SETTINGS["KickWebhookPort"]
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
    # No need to set kick_events_to_subscribe if we expect no subscription call

    with patch.object(bot, '_start_webhook_server', new_callable=AsyncMock) as mock_start_webhook, \
         patch.object(bot, '_poll', new_callable=AsyncMock) as mock_poll:

        await bot.run()
        
        mock_start_webhook.assert_not_awaited() # Changed from assert_awaited_once
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
    bot.event_manager = bot.MockKickEventManager.return_value
    
    with patch.object(bot, '_stop_webhook_server', new_callable=AsyncMock) as mock_stop_webhook, \
         patch.object(bot, 'http_session', MagicMock()) as mock_session_obj: 
        if bot.http_session: 
            mock_session_obj.close = AsyncMock()
        
        bot.ws_connection = AsyncMock()
        bot.ws_connection.closed = False
        bot.ws = bot.MockTwitchWebsocket_class_for_test()
        bot.ws.stop = MagicMock()

        await bot.shutdown()
        
        assert bot.event_manager is None 
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

# --- New tests for Feature Flags ---

@pytest.mark.asyncio
@pytest.mark.parametrize("feature_flag_settings", [
    ({"KickWebhookEnabled": True, "FeatureFlags": {"EnableNewWebhookEventSystem": True, "DisableLegacyGiftEventHandling": False}}),
    ({"KickWebhookEnabled": True, "FeatureFlags": {"EnableNewWebhookEventSystem": False, "DisableLegacyGiftEventHandling": False}}),
    ({"KickWebhookEnabled": False, "FeatureFlags": {"EnableNewWebhookEventSystem": True, "DisableLegacyGiftEventHandling": False}}), # Webhook disabled globally
])
async def test_kickbot_run_respects_enable_new_webhook_system_flag(
    feature_flag_settings, mock_env_vars, monkeypatch
):
    '''
    Tests KickBot.run() behavior based on EnableNewWebhookEventSystem feature flag
    and the global KickWebhookEnabled setting.
    '''
    current_test_settings = DEFAULT_BOT_SETTINGS.copy()
    current_test_settings.update(feature_flag_settings)

    # Mock builtins.open to return our specific settings for this test
    mock_file = mock_open(read_data=json.dumps(current_test_settings))
    
    # Patch the global 'settings' variable in kickbot.kick_bot module as it's loaded at import time
    # And also patch builtins.open for the initial load.
    with patch('builtins.open', mock_file), \
         patch('kickbot.kick_bot.settings', current_test_settings):

        # Instantiate KickBot here so it picks up the patched global settings
        # and the mocked open for its internal Settings() call if any.
        bot = KickBot(username=current_test_settings["KickEmail"], password=current_test_settings["KickPass"])
        bot.set_settings(current_test_settings)

        # Apply mocks for dependencies initialized in KickBot or its methods
        with patch('kickbot.kick_bot.KickClient', spec=KickClient) as MockKickClient, \
             patch('kickbot.kick_bot.KickAuthManager', spec=KickAuthManager) as MockKickAuthManager, \
             patch('kickbot.kick_bot.KickEventManager', spec=KickEventManager) as MockKickEventManager, \
             patch('kickbot.kick_bot.KickWebhookHandler', spec=KickWebhookHandler) as MockKickWebhookHandler, \
             patch('kickbot.kick_bot.get_ws_uri', return_value="ws://localhost:faker"), \
             patch('kickbot.kick_bot.websockets.connect', new_callable=AsyncMock), \
             patch('kickbot.kick_bot.Settings') as MockMarkovSettings, \
             patch('kickbot.kick_bot.Database') as MockMarkovDatabase, \
             patch('kickbot.kick_bot.TwitchWebsocket') as MockTwitchWebsocket, \
             patch('kickbot.kick_bot.LoopingTimer'), \
             patch.object(bot, '_start_webhook_server', new_callable=AsyncMock) as mock_bot_start_webhook_method, \
             patch.object(bot, '_poll', new_callable=AsyncMock) as mock_poll:

            # Setup mock instances
            mock_kam_instance = AsyncMock(spec=KickAuthManager)
            mock_kam_instance.get_valid_token = AsyncMock(return_value="test_bot_token")
            MockKickAuthManager.return_value = mock_kam_instance

            mock_kem_instance = AsyncMock(spec=KickEventManager)
            MockKickEventManager.return_value = mock_kem_instance
            
            # Simulate parts of bot setup that happen before/during run()
            bot.streamer_info = {"id": 98765, "username": current_test_settings["KickStreamer"]}
            bot.chatroom_id = 112233 
            # The bot's set_settings method will be called during __init__ due to Settings(self)
            # which should load webhook_enabled and kick_events_to_subscribe from current_test_settings.
            # If FeatureFlags are not picked up by set_settings, that's a bug to fix in KickBot.

            await bot.run()

            should_run_new_system = current_test_settings["FeatureFlags"]["EnableNewWebhookEventSystem"] and \
                                  current_test_settings["KickWebhookEnabled"]

            if should_run_new_system:
                MockKickWebhookHandler.assert_called_once()
                mock_bot_start_webhook_method.assert_awaited_once()
                MockKickEventManager.assert_called_once_with(
                    auth_manager=bot.auth_manager, 
                    client=bot.client, # Expect KickClient instance
                    broadcaster_user_id=bot.streamer_info['id']
                )
                mock_kem_instance.resubscribe_to_configured_events.assert_awaited_once_with(
                     bot.kick_events_to_subscribe # This should be loaded by set_settings
                )
            else:
                # If KickWebhookEnabled is false, KWH constructor is not called in run.
                if not current_test_settings["KickWebhookEnabled"]:
                    MockKickWebhookHandler.assert_not_called()
                # else KWH might be constructed but not started
                
                mock_bot_start_webhook_method.assert_not_awaited()
                
                # KEM might be initialized if streamer_info is present but resubscribe shouldn't be called
                # A stricter check: If the new system is disabled, KEM should ideally not be functional for subscriptions.
                if bot.event_manager: # if KEM instance was created
                    mock_kem_instance.resubscribe_to_configured_events.assert_not_awaited()
                
                # If the new system is entirely off, event_manager might not even be created.
                # This depends on how the KickBot code will be structured.
                # For now, we focus on resubscribe not being called.

            mock_poll.assert_awaited_once() 