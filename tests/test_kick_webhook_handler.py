import asyncio
import json
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import datetime

from aiohttp import web
from pydantic import ValidationError

from kickbot.kick_webhook_handler import KickWebhookHandler
from kickbot.event_models import FollowEvent, SubscriptionEvent, GiftedSubscriptionEvent, AnyKickEvent, parse_kick_event_payload, UserInfo, FollowEventData, SubscriberInfo, SubscriptionEventData, GifterInfo, RecipientInfo, GiftedSubscriptionEventData, FollowerInfo, SubscriptionEventKick, SubscriptionRenewalEvent

# Predefined valid UTC datetime object for consistent testing
VALID_TIMESTAMP_STR = "2024-03-10T10:00:00Z"
VALID_DATETIME = datetime.datetime.strptime(VALID_TIMESTAMP_STR, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
VALID_DATETIME_PAYLOAD_FORMAT = VALID_DATETIME.isoformat() # Pydantic might output with +00:00

# Example Payloads based on Pydantic Models
# These will be used to simulate incoming webhook data

VALID_FOLLOW_PAYLOAD = {
    "id": "evt_follow_123",
    "event": "channel.followed",
    "channel_id": "channel_xyz",
    "created_at": VALID_DATETIME_PAYLOAD_FORMAT,
    "data": {
        "follower": {"user_id": 123456, "username": "TestFollower"},
        "followed_at": VALID_DATETIME_PAYLOAD_FORMAT
    }
}

VALID_SUBSCRIBE_PAYLOAD = {
    "id": "evt_sub_456",
    "event": "channel.subscription.new",
    "channel_id": "channel_xyz",
    "created_at": VALID_DATETIME_PAYLOAD_FORMAT,
    "data": {
        "subscriber": {"user_id": 789012, "username": "TestSubscriber"},
        "tier": "Tier 1",
        "duration": 3,
        "created_at": VALID_DATETIME_PAYLOAD_FORMAT,
        "expires_at": "2024-04-10T10:00:00Z"
    }
}

VALID_GIFTED_SUB_PAYLOAD = {
    "id": "evt_giftsub_789",
    "event": "channel.subscription.gifts",
    "channel_id": "channel_xyz",
    "created_at": VALID_DATETIME_PAYLOAD_FORMAT,
    "data": {
        "gifter": {"user_id": 345678, "username": "TestGifter"},
        "recipients": [
            {"user_id": 901234, "username": "TestRecipient1"},
            {"user_id": 567890, "username": "TestRecipient2"}
        ],
        "tier": "Tier 1",
        "created_at": VALID_DATETIME_PAYLOAD_FORMAT,
        "expires_at": "2024-04-10T10:00:00Z"
    }
}

VALID_RENEWAL_PAYLOAD = {
    "id": "evt_renewal_abc",
    "event": "channel.subscription.renewal",
    "channel_id": "channel_xyz",
    "created_at": VALID_DATETIME_PAYLOAD_FORMAT, # Event creation time
    "data": {
        "subscriber": {"user_id": 111213, "username": "LoyalRenewer"},
        "tier": "Tier 2", # Corrected from subscription_tier to use the alias expected by Pydantic model
        "duration": 12, # Cumulative months
        "created_at": VALID_DATETIME_PAYLOAD_FORMAT, # Subscription period start
        "expires_at": "2025-03-10T10:00:00Z"  # Subscription period end
    }
}

INVALID_JSON_PAYLOAD_STR = "{\"event\": \"not_json\""
MALFORMED_EVENT_PAYLOAD = {"id": "malformed_evt_000"} # Missing 'event' type and 'data'
UNKNOWN_EVENT_PAYLOAD = {
    "id": "evt_unknown_001",
    "event": "channel.cheered", # An event type we don't explicitly handle yet
    "channel_id": "channel_xyz",
    "created_at": VALID_DATETIME_PAYLOAD_FORMAT,
    "data": {"message": "Hello!"}
}

class TestKickWebhookHandler(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        # Create a mock KickBot instance
        self.mock_kick_bot = MagicMock()
        self.mock_kick_bot.send_text = AsyncMock() # Common method used by handlers

        # Default instantiation for tests that don't care about flags or want them enabled.
        self.handler = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, # Provide the mock bot
            log_events=False, # Disable verbose logging during most tests
            enable_new_webhook_system=True,
            disable_legacy_gift_handling=False
        )
        
        # Store references to the actual handler methods for tests that might want to mock them specifically.
        # For testing conditional logic WITHIN handlers, we use the real methods.
        self.real_handle_follow_event = self.handler.handle_follow_event
        self.real_handle_subscription_event = self.handler.handle_subscription_event
        self.real_handle_gifted_subscription_event = self.handler.handle_gifted_subscription_event
        self.real_handle_subscription_renewal_event = self.handler.handle_subscription_renewal_event # Added for renewal

        # For tests checking dispatch logic, we still mock the handlers to verify they are called.
        # These will be set on a new handler instance if a test needs this behavior.
        self.mock_follow_handler = AsyncMock(name="mock_follow_event_handler")
        self.mock_subscription_handler = AsyncMock(name="mock_subscription_event_handler")
        self.mock_gifted_subscription_handler = AsyncMock(name="mock_gifted_subscription_event_handler")
        self.mock_renewal_handler = AsyncMock(name="mock_subscription_renewal_event_handler") # Added for renewal

    async def simulate_request(self, payload_data, handler_instance=None):
        """Helper to simulate an aiohttp request."""
        current_handler = handler_instance if handler_instance else self.handler

        if isinstance(payload_data, dict):
            raw_payload = json.dumps(payload_data).encode('utf-8')
        else: # For testing invalid JSON strings
            raw_payload = payload_data.encode('utf-8')
        
        mock_request = AsyncMock(spec=web.Request)
        mock_request.read = AsyncMock(return_value=raw_payload)
        # mock_request.headers = {} # Add if testing signature verification later
        return await current_handler.handle_webhook(mock_request)

    # --- Test Event Parsing (Task 4.5.1) ---
    def test_parse_valid_follow_event(self):
        parsed = parse_kick_event_payload(VALID_FOLLOW_PAYLOAD)
        self.assertIsInstance(parsed, FollowEvent)
        self.assertEqual(parsed.id, VALID_FOLLOW_PAYLOAD["id"])
        self.assertEqual(parsed.event, "channel.followed")
        self.assertEqual(parsed.channel_id, VALID_FOLLOW_PAYLOAD["channel_id"])
        # self.assertEqual(parsed.created_at, VALID_DATETIME) # Pydantic might parse to timezone-aware
        self.assertIsInstance(parsed.data, FollowEventData)
        self.assertEqual(parsed.data.follower.username, "TestFollower")
        # self.assertEqual(parsed.data.followed_at, VALID_DATETIME)

    def test_parse_valid_subscription_event(self):
        parsed = parse_kick_event_payload(VALID_SUBSCRIBE_PAYLOAD)
        self.assertIsInstance(parsed, SubscriptionEventKick)
        self.assertEqual(parsed.id, VALID_SUBSCRIBE_PAYLOAD["id"])
        self.assertEqual(parsed.event, "channel.subscription.new")
        self.assertEqual(parsed.data.subscriber.username, "TestSubscriber")
        self.assertEqual(parsed.data.subscription_tier, "Tier 1")
        self.assertEqual(parsed.data.months_subscribed, 3)
        self.assertFalse(parsed.is_gift)

    def test_parse_valid_gifted_subscription_event(self):
        parsed = parse_kick_event_payload(VALID_GIFTED_SUB_PAYLOAD)
        self.assertIsInstance(parsed, GiftedSubscriptionEvent)
        self.assertEqual(parsed.id, VALID_GIFTED_SUB_PAYLOAD["id"])
        self.assertEqual(parsed.event, "channel.subscription.gifts")
        self.assertEqual(parsed.data.gifter.username, "TestGifter")
        self.assertEqual(len(parsed.data.giftees), 2)
        self.assertEqual(parsed.data.giftees[0].username, "TestRecipient1")

    def test_parse_valid_renewal_event(self):
        parsed = parse_kick_event_payload(VALID_RENEWAL_PAYLOAD)
        self.assertIsInstance(parsed, SubscriptionRenewalEvent)
        self.assertEqual(parsed.id, VALID_RENEWAL_PAYLOAD["id"])
        self.assertEqual(parsed.event, "channel.subscription.renewal")
        self.assertEqual(parsed.data.subscriber.username, "LoyalRenewer")
        self.assertEqual(parsed.data.months_subscribed, 12)
        self.assertEqual(parsed.data.subscription_tier, "Tier 2")

    def test_parse_malformed_payload_returns_none(self):
        # Test with missing critical fields for Pydantic model validation
        parsed = parse_kick_event_payload(MALFORMED_EVENT_PAYLOAD)
        self.assertIsNone(parsed) # parse_kick_event_payload should catch ValidationError and return None

    # --- Test Webhook Handling and Dispatch (Task 4.5.2 & 4.5.3) ---
    async def test_handle_webhook_valid_follow_event_dispatches(self):
        # For this test, we want to ensure the dispatcher calls the right mock
        handler_with_mocks = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, # Provide the mock bot
            log_events=False,
            enable_new_webhook_system=True,
            disable_legacy_gift_handling=False
        )
        handler_with_mocks.register_event_handler("channel.followed", self.mock_follow_handler)
        handler_with_mocks.register_event_handler("channel.subscription.new", self.mock_subscription_handler)
        handler_with_mocks.register_event_handler("channel.subscription.gifts", self.mock_gifted_subscription_handler)
        handler_with_mocks.register_event_handler("channel.subscription.renewal", self.mock_renewal_handler) # Added for renewal

        response = await self.simulate_request(VALID_FOLLOW_PAYLOAD, handler_instance=handler_with_mocks)
        self.assertEqual(response.status, 200)
        self.mock_follow_handler.assert_called_once()
        # Check that it was called with an instance of FollowEvent
        call_args = self.mock_follow_handler.call_args[0][0]
        self.assertIsInstance(call_args, FollowEvent)
        self.assertEqual(call_args.data.follower.username, "TestFollower")
        self.mock_subscription_handler.assert_not_called()
        self.mock_gifted_subscription_handler.assert_not_called()
        self.mock_renewal_handler.assert_not_called() # Added for renewal

    async def test_handle_webhook_valid_subscribe_event_dispatches(self):
        handler_with_mocks = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, # Provide the mock bot
            log_events=False,
            enable_new_webhook_system=True,
            disable_legacy_gift_handling=False
        )
        handler_with_mocks.register_event_handler("channel.followed", self.mock_follow_handler)
        handler_with_mocks.register_event_handler("channel.subscription.new", self.mock_subscription_handler)
        handler_with_mocks.register_event_handler("channel.subscription.gifts", self.mock_gifted_subscription_handler)
        handler_with_mocks.register_event_handler("channel.subscription.renewal", self.mock_renewal_handler) # Added for renewal

        response = await self.simulate_request(VALID_SUBSCRIBE_PAYLOAD, handler_instance=handler_with_mocks)
        self.assertEqual(response.status, 200)
        self.mock_subscription_handler.assert_called_once()
        call_args = self.mock_subscription_handler.call_args[0][0]
        self.assertIsInstance(call_args, SubscriptionEventKick)
        self.assertEqual(call_args.data.subscriber.username, "TestSubscriber")
        self.mock_follow_handler.assert_not_called()
        self.mock_gifted_subscription_handler.assert_not_called()
        self.mock_renewal_handler.assert_not_called() # Added for renewal

    async def test_handle_webhook_valid_gifted_sub_event_dispatches(self):
        handler_with_mocks = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, # Provide the mock bot
            log_events=False,
            enable_new_webhook_system=True,
            disable_legacy_gift_handling=False
        )
        handler_with_mocks.register_event_handler("channel.followed", self.mock_follow_handler)
        handler_with_mocks.register_event_handler("channel.subscription.new", self.mock_subscription_handler)
        handler_with_mocks.register_event_handler("channel.subscription.gifts", self.mock_gifted_subscription_handler)
        handler_with_mocks.register_event_handler("channel.subscription.renewal", self.mock_renewal_handler) # Added for renewal

        response = await self.simulate_request(VALID_GIFTED_SUB_PAYLOAD, handler_instance=handler_with_mocks)
        self.assertEqual(response.status, 200)
        self.mock_gifted_subscription_handler.assert_called_once()
        call_args = self.mock_gifted_subscription_handler.call_args[0][0]
        self.assertIsInstance(call_args, GiftedSubscriptionEvent)
        self.assertEqual(call_args.data.gifter.username, "TestGifter")
        self.mock_follow_handler.assert_not_called()
        self.mock_subscription_handler.assert_not_called()
        self.mock_renewal_handler.assert_not_called() # Added for renewal

    async def test_handle_webhook_valid_renewal_event_dispatches(self):
        handler_with_mocks = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, 
            log_events=False,
            enable_new_webhook_system=True,
            disable_legacy_gift_handling=False
            # Not passing renewal_actions here, so defaults will be used by the handler if called
        )
        handler_with_mocks.register_event_handler("channel.followed", self.mock_follow_handler)
        handler_with_mocks.register_event_handler("channel.subscription.new", self.mock_subscription_handler)
        handler_with_mocks.register_event_handler("channel.subscription.gifts", self.mock_gifted_subscription_handler)
        handler_with_mocks.register_event_handler("channel.subscription.renewal", self.mock_renewal_handler)

        response = await self.simulate_request(VALID_RENEWAL_PAYLOAD, handler_instance=handler_with_mocks)
        self.assertEqual(response.status, 200)
        self.mock_renewal_handler.assert_called_once()
        call_args = self.mock_renewal_handler.call_args[0][0]
        self.assertIsInstance(call_args, SubscriptionRenewalEvent)
        self.assertEqual(call_args.data.subscriber.username, "LoyalRenewer")
        self.mock_follow_handler.assert_not_called()
        self.mock_subscription_handler.assert_not_called()
        self.mock_gifted_subscription_handler.assert_not_called()

    async def test_handle_webhook_invalid_json_string(self):
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='ERROR') as cm:
            response = await self.simulate_request(INVALID_JSON_PAYLOAD_STR)
        self.assertEqual(response.status, 400)
        self.assertIn("Failed to parse webhook JSON payload", cm.output[0])
        # self.handler.handle_follow_event.assert_not_called() # This would refer to the mock if setUp was not changed
        self.mock_follow_handler.assert_not_called()
        self.mock_subscription_handler.assert_not_called()
        self.mock_gifted_subscription_handler.assert_not_called()
        self.mock_renewal_handler.assert_not_called() # Added for renewal

    async def test_handle_webhook_malformed_pydantic_payload(self):
        # This payload is valid JSON but will fail Pydantic validation in parse_kick_event_payload
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='WARNING') as cm:
            response = await self.simulate_request(MALFORMED_EVENT_PAYLOAD)
        # parse_kick_event_payload returns None, leading to a 200 but logged warning
        self.assertEqual(response.status, 200) 
        self.assertIn("Could not parse webhook payload into a known event model", cm.output[0])
        # self.handler.handle_follow_event.assert_not_called()

    async def test_handle_webhook_unknown_event_type(self):
        # This payload is valid and parsable by Pydantic if we had a model for 'channel.cheered'
        # but parse_kick_event_payload will return None because it's not in AnyKickEvent Union.
        handler_with_mocks = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, # Provide the mock bot
            log_events=False,
            enable_new_webhook_system=True,
            disable_legacy_gift_handling=False
        )
        handler_with_mocks.register_event_handler("channel.followed", self.mock_follow_handler)
        handler_with_mocks.register_event_handler("channel.subscription.new", self.mock_subscription_handler)
        handler_with_mocks.register_event_handler("channel.subscription.gifts", self.mock_gifted_subscription_handler)
        handler_with_mocks.register_event_handler("channel.subscription.renewal", self.mock_renewal_handler)

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='WARNING') as cm:
            response = await self.simulate_request(UNKNOWN_EVENT_PAYLOAD, handler_instance=handler_with_mocks)
        self.assertEqual(response.status, 200) # Still 200 as per current logic
        self.assertIn("Could not parse webhook payload into a known event model", cm.output[0])
        # No specific handler should be called
        self.mock_follow_handler.assert_not_called()
        self.mock_subscription_handler.assert_not_called()
        self.mock_gifted_subscription_handler.assert_not_called()
        self.mock_renewal_handler.assert_not_called() # Added for renewal

    # --- Test Error Handling in Specific Handler (Task 4.5.4) ---
    async def test_handler_exception_propagates_to_500(self):
        # Make one of the handlers raise an exception
        handler_with_erroring_mock = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, # Provide the mock bot
            log_events=False,
            enable_new_webhook_system=True,
            disable_legacy_gift_handling=False
        )
        error_message = "Test handler internal error!"
        
        # Create a new mock for this specific test that will raise an error
        erroring_follow_handler_mock = AsyncMock(name="erroring_follow_handler_mock", side_effect=Exception(error_message))
        handler_with_erroring_mock.register_event_handler("channel.followed", erroring_follow_handler_mock)
        # Ensure other handlers are also mocked to avoid side effects if dispatch is wrong
        handler_with_erroring_mock.register_event_handler("channel.subscription.new", self.mock_subscription_handler)
        handler_with_erroring_mock.register_event_handler("channel.subscription.gifts", self.mock_gifted_subscription_handler)
        handler_with_erroring_mock.register_event_handler("channel.subscription.renewal", self.mock_renewal_handler)

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='ERROR') as cm:
            response = await self.simulate_request(VALID_FOLLOW_PAYLOAD, handler_instance=handler_with_erroring_mock)
        
        self.assertEqual(response.status, 500)
        self.assertIn(f"Internal server error: {error_message}", response.text)
        erroring_follow_handler_mock.assert_called_once() # It was called
        
        # Check that the error from the specific handler was logged, and then the general unhandled error
        event_id = VALID_FOLLOW_PAYLOAD["id"]
        expected_log_message = f"Error in event handler {erroring_follow_handler_mock.name} for event channel.followed ({event_id}): {error_message}"
        self.assertTrue(any(expected_log_message in log_msg for log_msg in cm.output))

    # --- Tests for Conditional Logic based on Feature Flags ---
    async def test_handle_follow_event_new_system_disabled(self):
        """Test handle_follow_event skips detailed logging if new system is disabled."""
        # Use a handler instance with the new system disabled
        handler_sys_disabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, # Provide the mock bot
            log_events=True, # Enable general event logging to capture the "Skipping" message
            enable_new_webhook_system=False, 
            disable_legacy_gift_handling=False
        )
        # Ensure the real handler is called, not a mock
        # handler_sys_disabled.register_event_handler("channel.followed", handler_sys_disabled.handle_follow_event) # already done in init

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            response = await self.simulate_request(VALID_FOLLOW_PAYLOAD, handler_instance=handler_sys_disabled)
        
        self.assertEqual(response.status, 200)
        self.assertTrue(any(f"New webhook system disabled. Skipping detailed processing for FollowEvent: {VALID_FOLLOW_PAYLOAD['id']}" in log for log in cm.output))
        self.assertFalse(any(f"FOLLOWER: {VALID_FOLLOW_PAYLOAD['data']['follower']['username']}" in log for log in cm.output))

    async def test_handle_follow_event_new_system_enabled(self):
        """Test handle_follow_event logs details if new system is enabled."""
        # Use a handler instance with the new system enabled (default from setUp is fine, but be explicit for clarity)
        handler_sys_enabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, # Provide the mock bot
            log_events=True, 
            enable_new_webhook_system=True, 
            disable_legacy_gift_handling=False
        )

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            response = await self.simulate_request(VALID_FOLLOW_PAYLOAD, handler_instance=handler_sys_enabled)

        self.assertEqual(response.status, 200)
        self.assertFalse(any(f"New webhook system disabled. Skipping detailed processing" in log for log in cm.output))
        self.assertTrue(any(f"FOLLOWER: {VALID_FOLLOW_PAYLOAD['data']['follower']['username']}" in log for log in cm.output))

    async def test_handle_gifted_subscription_event_legacy_disabled(self):
        """Test gifted sub handler logs correctly when legacy handling is disabled."""
        handler_gifts_legacy_off = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, # Provide the mock bot
            log_events=True, 
            enable_new_webhook_system=True, 
            disable_legacy_gift_handling=True
        )
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            response = await self.simulate_request(VALID_GIFTED_SUB_PAYLOAD, handler_instance=handler_gifts_legacy_off)
        
        self.assertEqual(response.status, 200)
        self.assertTrue(any(f"GIFTER: {VALID_GIFTED_SUB_PAYLOAD['data']['gifter']['username']}" in log for log in cm.output)) # Detailed log
        self.assertTrue(any(f"Legacy gift handling is disabled. This GiftedSubscriptionEvent (ID: {VALID_GIFTED_SUB_PAYLOAD['id']}) is being processed solely by the new system." in log for log in cm.output))

    async def test_handle_gifted_subscription_event_legacy_enabled(self):
        """Test gifted sub handler logs correctly when legacy handling is enabled."""
        handler_gifts_legacy_on = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, # Provide the mock bot
            log_events=True, 
            enable_new_webhook_system=True, 
            disable_legacy_gift_handling=False # Default, but explicit
        )
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            response = await self.simulate_request(VALID_GIFTED_SUB_PAYLOAD, handler_instance=handler_gifts_legacy_on)
        
        self.assertEqual(response.status, 200)
        self.assertTrue(any(f"GIFTER: {VALID_GIFTED_SUB_PAYLOAD['data']['gifter']['username']}" in log for log in cm.output)) # Detailed log
        self.assertTrue(any(f"Legacy gift handling may still be active. This GiftedSubscriptionEvent (ID: {VALID_GIFTED_SUB_PAYLOAD['id']}) is processed by new system; ensure no double actions." in log for log in cm.output))

    async def test_handle_follow_event_new_system_disabled_does_not_send_message(self):
        """Test that no message is sent if the new webhook system is disabled."""
        mock_bot = MagicMock()
        mock_bot.send_text = AsyncMock()

        handler = KickWebhookHandler(
            kick_bot_instance=mock_bot,
            log_events=False,
            enable_new_webhook_system=False, # System disabled
            disable_legacy_gift_handling=False,
            handle_follow_event_actions={"SendChatMessage": True} # Action enabled
        )

        sample_event_data = FollowEventData(
            follower=FollowerInfo(id="user123", username="TestFollower"),
            followed_at=VALID_DATETIME
        )
        sample_follow_event = FollowEvent(
            id="evt_test_follow",
            event="channel.followed",
            channel_id="channel_xyz",
            created_at=VALID_DATETIME,
            data=sample_event_data
        )

        await handler.handle_follow_event(sample_follow_event)
        mock_bot.send_text.assert_not_called()

    async def test_handle_follow_event_action_disabled_does_not_send_message(self):
        """Test that no message is sent if the SendChatMessage action is disabled."""
        mock_bot = MagicMock()
        mock_bot.send_text = AsyncMock()

        handler = KickWebhookHandler(
            kick_bot_instance=mock_bot,
            log_events=False,
            enable_new_webhook_system=True, # System enabled
            disable_legacy_gift_handling=False,
            handle_follow_event_actions={"SendChatMessage": False} # Action disabled
        )
        
        sample_event_data = FollowEventData(
            follower=FollowerInfo(id="user123", username="TestFollower"),
            followed_at=VALID_DATETIME
        )
        sample_follow_event = FollowEvent(
            id="evt_test_follow",
            event="channel.followed",
            channel_id="channel_xyz",
            created_at=VALID_DATETIME,
            data=sample_event_data
        )

        await handler.handle_follow_event(sample_follow_event)
        mock_bot.send_text.assert_not_called()

    async def test_handle_follow_event_sends_message_when_all_enabled(self):
        """Test that a message is sent when the system and action are enabled."""
        mock_bot = MagicMock()
        mock_bot.send_text = AsyncMock()

        handler = KickWebhookHandler(
            kick_bot_instance=mock_bot,
            log_events=False,
            enable_new_webhook_system=True, # System enabled
            disable_legacy_gift_handling=False,
            handle_follow_event_actions={"SendChatMessage": True} # Action enabled
        )
        
        follower_username = "TestFollower123"
        sample_event_data = FollowEventData(
            follower=FollowerInfo(id="user123", username=follower_username),
            followed_at=VALID_DATETIME
        )
        sample_follow_event = FollowEvent(
            id="evt_test_follow_enabled",
            event="channel.followed",
            channel_id="channel_xyz",
            created_at=VALID_DATETIME,
            data=sample_event_data
        )

        await handler.handle_follow_event(sample_follow_event)
        
        expected_message = f"Thanks for following, {follower_username}!"
        mock_bot.send_text.assert_called_once_with(expected_message)

    async def test_handle_follow_event_default_send_message_true(self):
        """Test that message sends if HandleFollowEventActions is None (defaulting to True)."""
        mock_bot = MagicMock()
        mock_bot.send_text = AsyncMock()

        handler = KickWebhookHandler(
            kick_bot_instance=mock_bot,
            log_events=False,
            enable_new_webhook_system=True, # System enabled
            disable_legacy_gift_handling=False,
            handle_follow_event_actions=None # Config not provided, should default
        )
        
        follower_username = "DefaultFollower"
        sample_event_data = FollowEventData(
            follower=FollowerInfo(id="user789", username=follower_username),
            followed_at=VALID_DATETIME
        )
        sample_follow_event = FollowEvent(
            id="evt_test_follow_default",
            event="channel.followed",
            channel_id="channel_abc",
            created_at=VALID_DATETIME,
            data=sample_event_data
        )

        await handler.handle_follow_event(sample_follow_event)
        
        expected_message = f"Thanks for following, {follower_username}!"
        mock_bot.send_text.assert_called_once_with(expected_message)

    async def test_handle_follow_event_invalid_config_defaults_and_sends_message(self):
        # Test that if HandleFollowEventActions is provided but SendChatMessage is not a bool, it defaults to True,
        # a warning is logged, and the message is still sent.
        
        parsed_event = parse_kick_event_payload(VALID_FOLLOW_PAYLOAD)
        self.assertIsInstance(parsed_event, FollowEvent)

        # The warning is logged during __init__
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='WARNING') as warn_cm:
            handler_with_specific_config = KickWebhookHandler(
                kick_bot_instance=self.mock_kick_bot,
                log_events=False,
                enable_new_webhook_system=True, # System is ENABLED for this test
                handle_follow_event_actions={"SendChatMessage": "not_a_bool"} # Invalid config
            )
        
        # Check that the specific warning was logged
        self.assertIn(
            "Invalid or missing 'SendChatMessage' in handle_follow_event_actions. Defaulting to True.", 
            [r.getMessage() for r in warn_cm.records][0] # warn_cm should now have the warning
        )

        # Now check that the event handler still sends the message due to the default
        # No need for assertLogs here if we are only checking mock_kick_bot.send_text
        await handler_with_specific_config.handle_follow_event(parsed_event)
        self.mock_kick_bot.send_text.assert_called_once_with(f"Thanks for following, {VALID_FOLLOW_PAYLOAD['data']['follower']['username']}!")

    # --- Tests for handle_subscription_event (User Story 6.2) ---

    async def test_handle_subscription_event_new_system_disabled(self):
        """Test that no actions are taken if enable_new_webhook_system is False."""
        handler_disabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=False, # System disabled
            handle_subscription_event_actions={"SendChatMessage": True, "AwardPoints": True, "PointsToAward": 100}
        )
        parsed_event = parse_kick_event_payload(VALID_SUBSCRIBE_PAYLOAD)
        self.assertIsInstance(parsed_event, SubscriptionEventKick)

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_disabled.handle_subscription_event(parsed_event)
        
        self.mock_kick_bot.send_text.assert_not_called()
        # Check logs for system disabled message and no award points message
        self.assertIn(f"New webhook system disabled. Skipping detailed processing for SubscriptionEvent: {VALID_SUBSCRIBE_PAYLOAD['id']}", cm.output[0])
        self.assertNotIn("AWARD_POINTS_PLACEHOLDER", ''.join(cm.output))

    async def test_handle_subscription_event_all_actions_enabled(self):
        """Test chat message and points logging when all flags are true."""
        handler_enabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_subscription_event_actions={"SendChatMessage": True, "AwardPoints": True, "PointsToAward": 150}
        )
        parsed_event = parse_kick_event_payload(VALID_SUBSCRIBE_PAYLOAD)
        self.assertIsInstance(parsed_event, SubscriptionEventKick)

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_enabled.handle_subscription_event(parsed_event)

        expected_message = f"Welcome to the sub club, {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['username']}! Thanks for subscribing."
        self.mock_kick_bot.send_text.assert_called_once_with(expected_message)
        
        # Check for points logging
        self.assertIn(
            f"AWARD_POINTS_PLACEHOLDER: Would award 150 points to {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['username']} (ID: {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['id']}) for new subscription.",
            ''.join(cm.output)
        )

    async def test_handle_subscription_event_chat_disabled_points_enabled(self):
        """Test only points logging when chat is disabled."""
        handler_chat_disabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_subscription_event_actions={"SendChatMessage": False, "AwardPoints": True, "PointsToAward": 50}
        )
        parsed_event = parse_kick_event_payload(VALID_SUBSCRIBE_PAYLOAD)
        self.assertIsInstance(parsed_event, SubscriptionEventKick)

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_chat_disabled.handle_subscription_event(parsed_event)

        self.mock_kick_bot.send_text.assert_not_called()
        self.assertIn(f"'SendChatMessage' for new subscription event is disabled. Skipping message for {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['username']}.", ''.join(cm.output))
        self.assertIn(
            f"AWARD_POINTS_PLACEHOLDER: Would award 50 points to {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['username']} (ID: {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['id']}) for new subscription.",
            ''.join(cm.output)
        )

    async def test_handle_subscription_event_chat_enabled_points_disabled(self):
        """Test only chat message when points are disabled."""
        handler_points_disabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_subscription_event_actions={"SendChatMessage": True, "AwardPoints": False, "PointsToAward": 100}
        )
        parsed_event = parse_kick_event_payload(VALID_SUBSCRIBE_PAYLOAD)
        self.assertIsInstance(parsed_event, SubscriptionEventKick)

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_points_disabled.handle_subscription_event(parsed_event)

        expected_message = f"Welcome to the sub club, {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['username']}! Thanks for subscribing."
        self.mock_kick_bot.send_text.assert_called_once_with(expected_message)
        self.assertIn(f"'AwardPoints' for new subscription event is disabled. Skipping points for {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['username']}.", ''.join(cm.output))
        self.assertNotIn("AWARD_POINTS_PLACEHOLDER", ''.join(cm.output))

    async def test_handle_subscription_event_all_actions_disabled_by_flags(self):
        """Test no actions (chat/points) if specific flags are false, even if system is enabled."""
        handler_actions_disabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_subscription_event_actions={"SendChatMessage": False, "AwardPoints": False, "PointsToAward": 100}
        )
        parsed_event = parse_kick_event_payload(VALID_SUBSCRIBE_PAYLOAD)
        self.assertIsInstance(parsed_event, SubscriptionEventKick)

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_actions_disabled.handle_subscription_event(parsed_event)

        self.mock_kick_bot.send_text.assert_not_called()
        self.assertIn("'SendChatMessage' for new subscription event is disabled.", ''.join(cm.output))
        self.assertIn("'AwardPoints' for new subscription event is disabled.", ''.join(cm.output))
        self.assertNotIn("AWARD_POINTS_PLACEHOLDER", ''.join(cm.output))

    async def test_handle_subscription_event_default_configs_used(self):
        """Test that default configurations are used if handle_subscription_event_actions is None or empty."""
        handler_default_config = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_subscription_event_actions=None # Testing default behavior
        )
        parsed_event = parse_kick_event_payload(VALID_SUBSCRIBE_PAYLOAD)
        self.assertIsInstance(parsed_event, SubscriptionEventKick)
        
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_default_config.handle_subscription_event(parsed_event)

        # Defaults are: SendChatMessage=True, AwardPoints=True, PointsToAward=100
        expected_message = f"Welcome to the sub club, {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['username']}! Thanks for subscribing."
        self.mock_kick_bot.send_text.assert_called_once_with(expected_message)
        self.assertIn(
            f"AWARD_POINTS_PLACEHOLDER: Would award 100 points to {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['username']} (ID: {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['id']}) for new subscription.",
            ''.join(cm.output)
        )

    async def test_handle_subscription_event_invalid_action_config_uses_defaults(self):
        """Test that invalid parts of handle_subscription_event_actions fall back to defaults."""
        parsed_event = parse_kick_event_payload(VALID_SUBSCRIBE_PAYLOAD)
        self.assertIsInstance(parsed_event, SubscriptionEventKick)

        # Check warnings for bad config during __init__
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='WARNING') as warn_cm:
            handler_invalid_config = KickWebhookHandler(
                kick_bot_instance=self.mock_kick_bot,
                log_events=False,
                enable_new_webhook_system=True,
                handle_subscription_event_actions={
                    "SendChatMessage": "not_a_bool", 
                    "AwardPoints": "another_bad_value", 
                    "PointsToAward": "one_hundred" 
                }
            )
        
        # Check that warnings were logged for each invalid config item
        warning_logs = '\n'.join(warn_cm.output) # Use newline for multi-line matching
        self.assertIn("Invalid or missing 'SendChatMessage' in handle_subscription_event_actions. Using default.", warning_logs)
        self.assertIn("Invalid or missing 'AwardPoints' in handle_subscription_event_actions. Using default.", warning_logs)
        self.assertIn("Invalid or missing 'PointsToAward' in handle_subscription_event_actions. Using default.", warning_logs)

        # Check info for actions taken by handle_subscription_event
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as info_cm:
            await handler_invalid_config.handle_subscription_event(parsed_event)
        
        # Check that default actions were taken (True, True, 100)
        info_logs = '\n'.join(info_cm.output)
        expected_message = f"Welcome to the sub club, {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['username']}! Thanks for subscribing."
        self.mock_kick_bot.send_text.assert_called_once_with(expected_message)
        self.assertIn(
            f"AWARD_POINTS_PLACEHOLDER: Would award 100 points to {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['username']} (ID: {VALID_SUBSCRIBE_PAYLOAD['data']['subscriber']['id']}) for new subscription.",
            info_logs
        )

    # --- Tests for handle_gifted_subscription_event (User Story 6.3) ---

    async def test_handle_gifted_sub_event_new_system_disabled(self):
        """Test no actions for gifted subs if enable_new_webhook_system is False."""
        handler_disabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=False, # System disabled
            handle_gifted_subscription_event_actions={
                "SendThankYouChatMessage": True, "AwardPointsToGifter": True, "PointsToGifterPerSub": 50,
                "AwardPointsToRecipients": True, "PointsToRecipient": 25
            }
        )
        parsed_event = parse_kick_event_payload(VALID_GIFTED_SUB_PAYLOAD)
        self.assertIsInstance(parsed_event, GiftedSubscriptionEvent)

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_disabled.handle_gifted_subscription_event(parsed_event)
        
        self.mock_kick_bot.send_text.assert_not_called()
        self.assertIn(f"New webhook system disabled. Skipping detailed processing for GiftedSubscriptionEvent: {VALID_GIFTED_SUB_PAYLOAD['id']}", cm.output[0])
        self.assertNotIn("AWARD_POINTS_PLACEHOLDER", ''.join(cm.output))

    async def test_handle_gifted_sub_event_all_actions_enabled_single_gift(self):
        """Test all actions for a single gifted sub when flags are true."""
        single_gift_payload = VALID_GIFTED_SUB_PAYLOAD.copy()
        single_gift_payload["data"] = single_gift_payload["data"].copy()
        single_gift_payload["data"]["recipients"] = [VALID_GIFTED_SUB_PAYLOAD["data"]["recipients"][0]] # Single recipient
        
        handler_enabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_gifted_subscription_event_actions={
                "SendThankYouChatMessage": True, "AwardPointsToGifter": True, "PointsToGifterPerSub": 70,
                "AwardPointsToRecipients": True, "PointsToRecipient": 30
            }
        )
        parsed_event = parse_kick_event_payload(single_gift_payload)
        self.assertIsInstance(parsed_event, GiftedSubscriptionEvent)
        gifter_username = single_gift_payload["data"]["gifter"]["username"]
        gifter_id = single_gift_payload["data"]["gifter"]["id"]
        recipient_username = single_gift_payload["data"]["recipients"][0]["username"]
        recipient_id = single_gift_payload["data"]["recipients"][0]["id"]

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_enabled.handle_gifted_subscription_event(parsed_event)

        expected_message = f"Huge thanks to {gifter_username} for gifting a sub to {recipient_username}! Welcome to the club!"
        self.mock_kick_bot.send_text.assert_called_once_with(expected_message)
        
        log_content = ''.join(cm.output)
        self.assertIn(f"AWARD_POINTS_PLACEHOLDER: Would award 70 points (70 per sub * 1 subs) to gifter {gifter_username} (ID: {gifter_id}).", log_content)
        self.assertIn(f"AWARD_POINTS_PLACEHOLDER: Would award 30 points to recipient {recipient_username} (ID: {recipient_id}) from gifted sub.", log_content)

    async def test_handle_gifted_sub_event_all_actions_enabled_multiple_gifts(self):
        """Test all actions for multiple gifted subs when flags are true."""
        handler_enabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_gifted_subscription_event_actions={
                "SendThankYouChatMessage": True, "AwardPointsToGifter": True, "PointsToGifterPerSub": 60,
                "AwardPointsToRecipients": True, "PointsToRecipient": 35
            }
        )
        parsed_event = parse_kick_event_payload(VALID_GIFTED_SUB_PAYLOAD) # Uses 2 recipients by default
        self.assertIsInstance(parsed_event, GiftedSubscriptionEvent)
        gifter_username = VALID_GIFTED_SUB_PAYLOAD["data"]["gifter"]["username"]
        gifter_id = VALID_GIFTED_SUB_PAYLOAD["data"]["gifter"]["id"]
        recipients_data = VALID_GIFTED_SUB_PAYLOAD["data"]["recipients"]
        recipient_usernames_str = f"{recipients_data[0]['username']}, {recipients_data[1]['username']}"

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_enabled.handle_gifted_subscription_event(parsed_event)

        expected_message = f"Wow! {gifter_username} just gifted 2 subs to the community! Thanks so much! Welcome {recipient_usernames_str}!"
        self.mock_kick_bot.send_text.assert_called_once_with(expected_message)
        
        log_content = ''.join(cm.output)
        self.assertIn(f"AWARD_POINTS_PLACEHOLDER: Would award 120 points (60 per sub * 2 subs) to gifter {gifter_username} (ID: {gifter_id}).", log_content)
        self.assertIn(f"AWARD_POINTS_PLACEHOLDER: Would award 35 points to recipient {recipients_data[0]['username']} (ID: {recipients_data[0]['id']}) from gifted sub.", log_content)
        self.assertIn(f"AWARD_POINTS_PLACEHOLDER: Would award 35 points to recipient {recipients_data[1]['username']} (ID: {recipients_data[1]['id']}) from gifted sub.", log_content)

    async def test_handle_gifted_sub_event_chat_disabled(self):
        """Test only points logging when chat message for gifted subs is disabled."""
        handler_chat_disabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_gifted_subscription_event_actions={
                "SendThankYouChatMessage": False, "AwardPointsToGifter": True, "PointsToGifterPerSub": 50,
                "AwardPointsToRecipients": True, "PointsToRecipient": 25
            }
        )
        parsed_event = parse_kick_event_payload(VALID_GIFTED_SUB_PAYLOAD)
        self.assertIsInstance(parsed_event, GiftedSubscriptionEvent)
        gifter_username = VALID_GIFTED_SUB_PAYLOAD["data"]["gifter"]["username"]

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_chat_disabled.handle_gifted_subscription_event(parsed_event)

        self.mock_kick_bot.send_text.assert_not_called()
        log_content = ''.join(cm.output)
        self.assertIn(f"'SendThankYouChatMessage' for gifted subs is disabled. Skipping message for gifter {gifter_username}.", log_content)
        self.assertIn("AWARD_POINTS_PLACEHOLDER: Would award 100 points", log_content) # Gifter: 50*2
        self.assertIn("AWARD_POINTS_PLACEHOLDER: Would award 25 points to recipient", log_content) # Recipients

    async def test_handle_gifted_sub_event_gifter_points_disabled(self):
        """Test chat and recipient points when gifter points are disabled."""
        handler_gifter_pts_disabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_gifted_subscription_event_actions={
                "SendThankYouChatMessage": True, "AwardPointsToGifter": False, "PointsToGifterPerSub": 50,
                "AwardPointsToRecipients": True, "PointsToRecipient": 25
            }
        )
        parsed_event = parse_kick_event_payload(VALID_GIFTED_SUB_PAYLOAD)
        self.assertIsInstance(parsed_event, GiftedSubscriptionEvent)
        gifter_username = VALID_GIFTED_SUB_PAYLOAD["data"]["gifter"]["username"]

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_gifter_pts_disabled.handle_gifted_subscription_event(parsed_event)

        self.mock_kick_bot.send_text.assert_called_once() # Chat message should be sent
        log_content = ''.join(cm.output)
        self.assertIn(f"'AwardPointsToGifter' for gifted subs is disabled. Skipping points for gifter {gifter_username}.", log_content)
        self.assertNotIn("AWARD_POINTS_PLACEHOLDER: Would award 100 points", log_content) # Gifter points shouldn't be there
        self.assertIn("AWARD_POINTS_PLACEHOLDER: Would award 25 points to recipient", log_content) # Recipients

    async def test_handle_gifted_sub_event_recipient_points_disabled(self):
        """Test chat and gifter points when recipient points are disabled."""
        handler_recip_pts_disabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_gifted_subscription_event_actions={
                "SendThankYouChatMessage": True, "AwardPointsToGifter": True, "PointsToGifterPerSub": 50,
                "AwardPointsToRecipients": False, "PointsToRecipient": 25
            }
        )
        parsed_event = parse_kick_event_payload(VALID_GIFTED_SUB_PAYLOAD)
        self.assertIsInstance(parsed_event, GiftedSubscriptionEvent)

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_recip_pts_disabled.handle_gifted_subscription_event(parsed_event)

        self.mock_kick_bot.send_text.assert_called_once() # Chat message should be sent
        log_content = ''.join(cm.output)
        self.assertIn(f"'AwardPointsToRecipients' for gifted subs is disabled. Skipping points for recipients.", log_content)
        self.assertIn("AWARD_POINTS_PLACEHOLDER: Would award 100 points", log_content) # Gifter points
        self.assertNotIn(f"AWARD_POINTS_PLACEHOLDER: Would award 25 points to recipient {VALID_GIFTED_SUB_PAYLOAD['data']['recipients'][0]['username']}", log_content) # Recipient points shouldn't be there

    async def test_handle_gifted_sub_event_anonymous_gifter(self):
        """Test behavior with an anonymous gifter."""
        anon_gift_payload = VALID_GIFTED_SUB_PAYLOAD.copy()
        anon_gift_payload["data"] = anon_gift_payload["data"].copy()
        anon_gift_payload["data"]["gifter"] = None # Anonymous gifter

        handler_anon = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_gifted_subscription_event_actions={
                "SendThankYouChatMessage": True, "AwardPointsToGifter": True, "PointsToGifterPerSub": 50,
                "AwardPointsToRecipients": True, "PointsToRecipient": 25
            }
        )
        parsed_event = parse_kick_event_payload(anon_gift_payload)
        self.assertIsInstance(parsed_event, GiftedSubscriptionEvent)
        recipients_data = anon_gift_payload["data"]["recipients"]
        recipient_usernames_str = f"{recipients_data[0]['username']}, {recipients_data[1]['username']}"

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_anon.handle_gifted_subscription_event(parsed_event)

        expected_message = f"Wow! Anonymous just gifted 2 subs to the community! Thanks so much! Welcome {recipient_usernames_str}!"
        self.mock_kick_bot.send_text.assert_called_once_with(expected_message)
        log_content = ''.join(cm.output)
        self.assertIn("Cannot award points to gifter as they are Anonymous.", log_content)
        self.assertNotIn("AWARD_POINTS_PLACEHOLDER: Would award 100 points (50 per sub * 2 subs) to gifter Anonymous", log_content)
        self.assertIn(f"AWARD_POINTS_PLACEHOLDER: Would award 25 points to recipient {recipients_data[0]['username']}", log_content)

    async def test_handle_gifted_sub_event_default_configs_used(self):
        """Test default behavior if handle_gifted_subscription_event_actions is None."""
        handler_default = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_gifted_subscription_event_actions=None # Test defaults
        )
        parsed_event = parse_kick_event_payload(VALID_GIFTED_SUB_PAYLOAD)
        self.assertIsInstance(parsed_event, GiftedSubscriptionEvent)
        gifter_username = VALID_GIFTED_SUB_PAYLOAD["data"]["gifter"]["username"]
        gifter_id = VALID_GIFTED_SUB_PAYLOAD["data"]["gifter"]["id"]
        recipients_data = VALID_GIFTED_SUB_PAYLOAD["data"]["recipients"]

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_default.handle_gifted_subscription_event(parsed_event)
        
        self.mock_kick_bot.send_text.assert_called_once() # Default is True for chat
        log_content = ''.join(cm.output)
        # Default: PtsGifter=50, PtsRecip=25
        self.assertIn(f"AWARD_POINTS_PLACEHOLDER: Would award 100 points (50 per sub * 2 subs) to gifter {gifter_username} (ID: {gifter_id}).", log_content)
        self.assertIn(f"AWARD_POINTS_PLACEHOLDER: Would award 25 points to recipient {recipients_data[0]['username']}", log_content)

    async def test_handle_gifted_sub_event_invalid_config_uses_defaults(self):
        # Test that if HandleGiftedSubscriptionEventActions is provided but keys are invalid, it defaults
        handler_with_specific_config = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_gifted_subscription_event_actions={
                "SendThankYouChatMessage": "not_a_bool",
                "AwardPointsToGifter": "false_text",
                "PointsToGifterPerSub": "fifty", 
                "AwardPointsToRecipients": [],
                "PointsToRecipient": {}}
        )
        parsed_event = parse_kick_event_payload(VALID_GIFTED_SUB_PAYLOAD)
        self.assertIsInstance(parsed_event, GiftedSubscriptionEvent)

        # When SendThankYouChatMessage defaults to True, and there are multiple gifts,
        # the message format is specific.
        gifter_username = parsed_event.data.gifter.username
        num_gifted = len(parsed_event.data.giftees)
        recipient_usernames = [g.username for g in parsed_event.data.giftees]
        expected_thank_you_message = f"Wow! {gifter_username} just gifted {num_gifted} subs to the community! Thanks so much! Welcome {', '.join(recipient_usernames)}!"
        
        # Check warnings for bad config are logged during __init__
        # This assertLogs should wrap the handler instantiation if checking __init__ warnings.
        # For this test, we primarily care that the *actions* default correctly.
        # The warnings for __init__ are covered by other tests or can be added if needed.

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_with_specific_config.handle_gifted_subscription_event(parsed_event)
        
        self.mock_kick_bot.send_text.assert_any_call(expected_thank_you_message)
        
        info_logs = "\n".join(cm.output)
        # Default points: Gifter=50 per sub, Recipient=25
        # Check gifter points log
        expected_gifter_points_log = (
            f"AWARD_POINTS_PLACEHOLDER: Would award {50 * num_gifted} points "
            f"(50 per sub * {num_gifted} subs) "
            f"to gifter {gifter_username} (ID: {parsed_event.data.gifter.id})."
        )
        self.assertIn(expected_gifter_points_log, info_logs)

        # Check recipient points log
        for recipient_info in parsed_event.data.giftees:
            expected_recipient_points_log = (
                f"AWARD_POINTS_PLACEHOLDER: Would award {25} points "
                f"to recipient {recipient_info.username} (ID: {recipient_info.id}) from gifted sub."
            )
            self.assertIn(expected_recipient_points_log, info_logs)
        
        self.assertTrue(handler_with_specific_config.send_thank_you_chat_message_for_gifted_sub)
        self.assertTrue(handler_with_specific_config.award_points_to_gifter_for_gifted_sub)
        self.assertEqual(handler_with_specific_config.points_to_gifter_per_sub_for_gifted_sub, 50)
        self.assertTrue(handler_with_specific_config.award_points_to_recipients_for_gifted_sub)
        self.assertEqual(handler_with_specific_config.points_to_recipient_for_gifted_sub, 25)

    # --- Tests for handle_subscription_renewal_event (User Story 6.4) --- 

    async def test_handle_renewal_event_new_system_disabled(self):
        """Test no actions for renewal if enable_new_webhook_system is False."""
        handler_disabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=False, # System disabled
            handle_subscription_renewal_event_actions={
                "SendChatMessage": True, "AwardPoints": True, "PointsToAward": 100
            }
        )
        parsed_event = parse_kick_event_payload(VALID_RENEWAL_PAYLOAD)
        self.assertIsInstance(parsed_event, SubscriptionRenewalEvent)

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_disabled.handle_subscription_renewal_event(parsed_event)
        
        self.mock_kick_bot.send_text.assert_not_called()
        self.assertIn(f"New webhook system disabled. Skipping detailed processing for SubscriptionRenewalEvent: {parsed_event.id}", "\n".join(cm.output))
        self.assertNotIn("Placeholder: Awarded", "\n".join(cm.output))

    async def test_handle_renewal_event_all_actions_enabled(self):
        """Test all actions occur if new system and flags are True."""
        handler_enabled = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_subscription_renewal_event_actions={
                "SendChatMessage": True, "AwardPoints": True, "PointsToAward": 150
            }
        )
        parsed_event = parse_kick_event_payload(VALID_RENEWAL_PAYLOAD)
        self.assertIsInstance(parsed_event, SubscriptionRenewalEvent)

        expected_message = f"Thanks {parsed_event.data.subscriber.username} for renewing your Tier {parsed_event.data.subscription_tier} sub for {parsed_event.data.months_subscribed} months!"

        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_enabled.handle_subscription_renewal_event(parsed_event)
        
        self.mock_kick_bot.send_text.assert_called_once_with(expected_message)
        self.assertIn(f"Placeholder: Awarded 150 points to {parsed_event.data.subscriber.username}", "\n".join(cm.output))

    async def test_handle_renewal_event_chat_disabled_points_enabled(self):
        handler = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, log_events=False, enable_new_webhook_system=True,
            handle_subscription_renewal_event_actions={"SendChatMessage": False, "AwardPoints": True, "PointsToAward": 50}
        )
        parsed_event = parse_kick_event_payload(VALID_RENEWAL_PAYLOAD)
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler.handle_subscription_renewal_event(parsed_event)
        self.mock_kick_bot.send_text.assert_not_called()
        self.assertIn(f"Placeholder: Awarded 50 points to {parsed_event.data.subscriber.username}", "\n".join(cm.output))
        self.assertIn("'SendChatMessage' for subscription renewal event is disabled.", "\n".join(cm.output))

    async def test_handle_renewal_event_chat_enabled_points_disabled(self):
        handler = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, log_events=False, enable_new_webhook_system=True,
            handle_subscription_renewal_event_actions={"SendChatMessage": True, "AwardPoints": False, "PointsToAward": 100}
        )
        parsed_event = parse_kick_event_payload(VALID_RENEWAL_PAYLOAD)
        expected_message = f"Thanks {parsed_event.data.subscriber.username} for renewing your Tier {parsed_event.data.subscription_tier} sub for {parsed_event.data.months_subscribed} months!"
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler.handle_subscription_renewal_event(parsed_event)
        self.mock_kick_bot.send_text.assert_called_once_with(expected_message)
        self.assertNotIn("Placeholder: Awarded", "\n".join(cm.output))
        self.assertIn("'AwardPoints' for subscription renewal event is disabled.", "\n".join(cm.output))

    async def test_handle_renewal_event_all_actions_disabled_by_flags(self):
        handler = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, log_events=False, enable_new_webhook_system=True,
            handle_subscription_renewal_event_actions={"SendChatMessage": False, "AwardPoints": False, "PointsToAward": 0}
        )
        parsed_event = parse_kick_event_payload(VALID_RENEWAL_PAYLOAD)
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler.handle_subscription_renewal_event(parsed_event)
        self.mock_kick_bot.send_text.assert_not_called()
        self.assertNotIn("Placeholder: Awarded", "\n".join(cm.output))
        self.assertIn("'SendChatMessage' for subscription renewal event is disabled.", "\n".join(cm.output))
        self.assertIn("'AwardPoints' for subscription renewal event is disabled.", "\n".join(cm.output))

    async def test_handle_renewal_event_default_configs_used(self):
        """Test that default actions occur if handle_subscription_renewal_event_actions is not provided."""
        handler_default = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True
            # No handle_subscription_renewal_event_actions provided, so defaults (True, True, 100) should apply
        )
        parsed_event = parse_kick_event_payload(VALID_RENEWAL_PAYLOAD)
        expected_message = f"Thanks {parsed_event.data.subscriber.username} for renewing your Tier {parsed_event.data.subscription_tier} sub for {parsed_event.data.months_subscribed} months!"
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_default.handle_subscription_renewal_event(parsed_event)
        self.mock_kick_bot.send_text.assert_called_once_with(expected_message)
        self.assertIn(f"Placeholder: Awarded 100 points to {parsed_event.data.subscriber.username}", "\n".join(cm.output))
        self.assertTrue(handler_default.send_chat_message_for_renewal_sub)
        self.assertTrue(handler_default.award_points_for_renewal_sub)
        self.assertEqual(handler_default.points_to_award_for_renewal_sub, 100)

    async def test_handle_renewal_event_invalid_action_config_uses_defaults(self):
        """Test that if renewal_actions is provided but keys are invalid, it defaults."""
        handler_invalid_config = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot,
            log_events=False,
            enable_new_webhook_system=True,
            handle_subscription_renewal_event_actions={
                "SendChatMessage": "not_a_bool", 
                "AwardPoints": [], 
                "PointsToAward": "one_hundred"
            }
        )
        parsed_event = parse_kick_event_payload(VALID_RENEWAL_PAYLOAD)
        expected_message = f"Thanks {parsed_event.data.subscriber.username} for renewing your Tier {parsed_event.data.subscription_tier} sub for {parsed_event.data.months_subscribed} months!"
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='INFO') as cm:
            await handler_invalid_config.handle_subscription_renewal_event(parsed_event)
        
        self.mock_kick_bot.send_text.assert_called_once_with(expected_message) # Default: True
        self.assertIn(f"Placeholder: Awarded 100 points to {parsed_event.data.subscriber.username}", "\n".join(cm.output)) # Default: True, 100 points

        # Check that the handler's attributes reflect the defaults
        self.assertTrue(handler_invalid_config.send_chat_message_for_renewal_sub)
        self.assertTrue(handler_invalid_config.award_points_for_renewal_sub)
        self.assertEqual(handler_invalid_config.points_to_award_for_renewal_sub, 100)


if __name__ == '__main__':
    unittest.main() 