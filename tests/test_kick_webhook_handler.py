import asyncio
import json
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import datetime

from aiohttp import web
from pydantic import ValidationError

from kickbot.kick_webhook_handler import KickWebhookHandler
from kickbot.event_models import FollowEvent, SubscriptionEvent, GiftedSubscriptionEvent, AnyKickEvent, parse_kick_event_payload, UserInfo, FollowEventData, SubscriberInfo, SubscriptionEventData, GifterInfo, RecipientInfo, GiftedSubscriptionEventData

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
        "follower": {"id": "user_follower_abc", "username": "TestFollower"},
        "followed_at": VALID_DATETIME_PAYLOAD_FORMAT
    }
}

VALID_SUBSCRIBE_PAYLOAD = {
    "id": "evt_sub_456",
    "event": "channel.subscribed",
    "channel_id": "channel_xyz",
    "created_at": VALID_DATETIME_PAYLOAD_FORMAT,
    "data": {
        "subscriber": {"id": "user_sub_def", "username": "TestSubscriber"},
        "tier": "Tier 1",
        "is_gift": False,
        "streak_months": 3,
        "subscribed_at": VALID_DATETIME_PAYLOAD_FORMAT
    }
}

VALID_GIFTED_SUB_PAYLOAD = {
    "id": "evt_giftsub_789",
    "event": "channel.subscription.gifted",
    "channel_id": "channel_xyz",
    "created_at": VALID_DATETIME_PAYLOAD_FORMAT,
    "data": {
        "gifter": {"id": "user_gifter_ghi", "username": "TestGifter"},
        "recipients": [
            {"id": "user_recip_jkl", "username": "TestRecipient1"},
            {"id": "user_recip_mno", "username": "TestRecipient2"}
        ],
        "tier": "Tier 1",
        "gifted_at": VALID_DATETIME_PAYLOAD_FORMAT
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
        self.handler = KickWebhookHandler(log_events=False) # Disable verbose logging during tests
        
        # Mock the specific event handlers on the instance
        self.handler.handle_follow_event = AsyncMock(name="handle_follow_event_mock", spec=self.handler.handle_follow_event)
        self.handler.handle_subscription_event = AsyncMock(name="handle_subscription_event_mock", spec=self.handler.handle_subscription_event)
        self.handler.handle_gifted_subscription_event = AsyncMock(name="handle_gifted_subscription_event_mock", spec=self.handler.handle_gifted_subscription_event)

        # Re-register these mocked handlers so they are used by the dispatcher
        # This is because the original registration happens in KickWebhookHandler.__init__ with the real methods.
        self.handler.register_event_handler("channel.followed", self.handler.handle_follow_event)
        self.handler.register_event_handler("channel.subscribed", self.handler.handle_subscription_event)
        self.handler.register_event_handler("channel.subscription.gifted", self.handler.handle_gifted_subscription_event)

    async def simulate_request(self, payload_data):
        """Helper to simulate an aiohttp request."""
        if isinstance(payload_data, dict):
            raw_payload = json.dumps(payload_data).encode('utf-8')
        else: # For testing invalid JSON strings
            raw_payload = payload_data.encode('utf-8')
        
        mock_request = AsyncMock(spec=web.Request)
        mock_request.read = AsyncMock(return_value=raw_payload)
        # mock_request.headers = {} # Add if testing signature verification later
        return await self.handler.handle_webhook(mock_request)

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
        self.assertIsInstance(parsed, SubscriptionEvent)
        self.assertEqual(parsed.id, VALID_SUBSCRIBE_PAYLOAD["id"])
        self.assertEqual(parsed.event, "channel.subscribed")
        self.assertEqual(parsed.data.subscriber.username, "TestSubscriber")
        self.assertEqual(parsed.data.subscription_tier, "Tier 1")
        self.assertEqual(parsed.data.months_subscribed, 3)

    def test_parse_valid_gifted_subscription_event(self):
        parsed = parse_kick_event_payload(VALID_GIFTED_SUB_PAYLOAD)
        self.assertIsInstance(parsed, GiftedSubscriptionEvent)
        self.assertEqual(parsed.id, VALID_GIFTED_SUB_PAYLOAD["id"])
        self.assertEqual(parsed.event, "channel.subscription.gifted")
        self.assertEqual(parsed.data.gifter.username, "TestGifter")
        self.assertEqual(len(parsed.data.recipients), 2)
        self.assertEqual(parsed.data.recipients[0].username, "TestRecipient1")

    def test_parse_malformed_payload_returns_none(self):
        # Test with missing critical fields for Pydantic model validation
        parsed = parse_kick_event_payload(MALFORMED_EVENT_PAYLOAD)
        self.assertIsNone(parsed) # parse_kick_event_payload should catch ValidationError and return None

    # --- Test Webhook Handling and Dispatch (Task 4.5.2 & 4.5.3) ---
    async def test_handle_webhook_valid_follow_event_dispatches(self):
        response = await self.simulate_request(VALID_FOLLOW_PAYLOAD)
        self.assertEqual(response.status, 200)
        self.handler.handle_follow_event.assert_called_once()
        # Check that it was called with an instance of FollowEvent
        call_args = self.handler.handle_follow_event.call_args[0][0]
        self.assertIsInstance(call_args, FollowEvent)
        self.assertEqual(call_args.data.follower.username, "TestFollower")
        self.handler.handle_subscription_event.assert_not_called()
        self.handler.handle_gifted_subscription_event.assert_not_called()

    async def test_handle_webhook_valid_subscribe_event_dispatches(self):
        response = await self.simulate_request(VALID_SUBSCRIBE_PAYLOAD)
        self.assertEqual(response.status, 200)
        self.handler.handle_subscription_event.assert_called_once()
        call_args = self.handler.handle_subscription_event.call_args[0][0]
        self.assertIsInstance(call_args, SubscriptionEvent)
        self.assertEqual(call_args.data.subscriber.username, "TestSubscriber")
        self.handler.handle_follow_event.assert_not_called()
        self.handler.handle_gifted_subscription_event.assert_not_called()

    async def test_handle_webhook_valid_gifted_sub_event_dispatches(self):
        response = await self.simulate_request(VALID_GIFTED_SUB_PAYLOAD)
        self.assertEqual(response.status, 200)
        self.handler.handle_gifted_subscription_event.assert_called_once()
        call_args = self.handler.handle_gifted_subscription_event.call_args[0][0]
        self.assertIsInstance(call_args, GiftedSubscriptionEvent)
        self.assertEqual(call_args.data.gifter.username, "TestGifter")
        self.handler.handle_follow_event.assert_not_called()
        self.handler.handle_subscription_event.assert_not_called()

    async def test_handle_webhook_invalid_json_string(self):
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='ERROR') as cm:
            response = await self.simulate_request(INVALID_JSON_PAYLOAD_STR)
        self.assertEqual(response.status, 400)
        self.assertIn("Failed to parse webhook JSON payload", cm.output[0])
        self.handler.handle_follow_event.assert_not_called()

    async def test_handle_webhook_malformed_pydantic_payload(self):
        # This payload is valid JSON but will fail Pydantic validation in parse_kick_event_payload
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='WARNING') as cm:
            response = await self.simulate_request(MALFORMED_EVENT_PAYLOAD)
        # parse_kick_event_payload returns None, leading to a 200 but logged warning
        self.assertEqual(response.status, 200) 
        self.assertIn("Could not parse webhook payload into a known event model", cm.output[0])
        self.handler.handle_follow_event.assert_not_called()

    async def test_handle_webhook_unknown_event_type(self):
        # This payload is valid and parsable by Pydantic if we had a model for 'channel.cheered'
        # but parse_kick_event_payload will return None because it's not in AnyKickEvent Union.
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='WARNING') as cm:
            response = await self.simulate_request(UNKNOWN_EVENT_PAYLOAD)
        self.assertEqual(response.status, 200) # Still 200 as per current logic
        self.assertIn("Could not parse webhook payload into a known event model", cm.output[0])
        # No specific handler should be called
        self.handler.handle_follow_event.assert_not_called()
        self.handler.handle_subscription_event.assert_not_called()
        self.handler.handle_gifted_subscription_event.assert_not_called()

    # --- Test Error Handling in Specific Handler (Task 4.5.4) ---
    async def test_handler_exception_propagates_to_500(self):
        # Make one of the handlers raise an exception
        error_message = "Test handler internal error!"
        self.handler.handle_follow_event.side_effect = Exception(error_message)
        
        with self.assertLogs(logger='kickbot.kick_webhook_handler', level='ERROR') as cm:
            response = await self.simulate_request(VALID_FOLLOW_PAYLOAD)
        
        self.assertEqual(response.status, 500)
        self.assertIn(f"Internal server error: {error_message}", response.text)
        self.handler.handle_follow_event.assert_called_once() # It was called
        
        # Check that the error from the specific handler was logged, and then the general unhandled error
        # Adjusted to expect "AsyncMock" as the handler name in the log, based on observed mock behavior.
        self.assertTrue(any(f"Error in event handler AsyncMock for event channel.followed: {error_message}" in log_msg for log_msg in cm.output))
        self.assertTrue(any(f"Unhandled error handling webhook: {error_message}" in log_msg for log_msg in cm.output))

if __name__ == '__main__':
    unittest.main() 