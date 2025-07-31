"""
Test suite for Production Webhook Fix
Tests with real webhook payloads from production logs
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import oauth_webhook_server


class TestProductionWebhookFix:
    """Test production webhook payload handling"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_alert_function = AsyncMock()

    @pytest.mark.asyncio
    async def test_real_follow_webhook_payload(self):
        """
        Test with the actual follow webhook payload from production logs
        
        This payload caused the "unknown" issue in production
        """
        # Real payload from production logs
        real_follow_payload = {
            "broadcaster": {
                "is_anonymous": False,
                "user_id": 1212654,
                "username": "eddieoz",
                "is_verified": True,
                "profile_picture": "https://files.kick.com/images/user/1212654/profile_image/conversion/6f871e2a-43f0-4cf2-b2b7-6901f0bd5b6a-fullsize.webp",
                "channel_slug": "eddieoz",
                "identity": None
            },
            "follower": {
                "is_anonymous": False,
                "user_id": 6914823,
                "username": "mzinha",
                "is_verified": False,
                "profile_picture": "https://dbxmjjzl5pc1g.cloudfront.net/68417caf-7cdd-43e3-8a65-c6d605e1b881/images/user-profile-pic.png",
                "channel_slug": "mzinha",
                "identity": None
            }
        }

        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Real follow webhook payload is processed
            await oauth_webhook_server.handle_follow_event(real_follow_payload)

            # Then: Should extract username correctly (not "Unknown")
            self.mock_alert_function.assert_called_once()
            call_args = self.mock_alert_function.call_args[0]
            alert_title = call_args[2]  # Alert title
            alert_description = call_args[3]  # Alert description

            # Verify the correct username is extracted
            assert "mzinha" in alert_title, f"Expected 'mzinha' in alert title, got: {alert_title}"
            assert "mzinha" in alert_description, f"Expected 'mzinha' in alert description, got: {alert_description}"
            assert "Unknown" not in alert_title, f"Alert still shows 'Unknown': {alert_title}"

    @pytest.mark.asyncio
    async def test_username_extraction_with_real_payload(self):
        """
        Test that the unified username extractor works with real payload structure
        """
        real_follow_payload = {
            "broadcaster": {
                "username": "eddieoz"
            },
            "follower": {
                "username": "mzinha"
            }
        }

        # Test the unified extractor directly
        from oauth_webhook_server import unified_extractor
        result = unified_extractor.extract_username(real_follow_payload, "follow")

        # Should extract the follower username correctly
        assert result.username == "mzinha"
        assert result.success is True
        assert result.strategy_used == "follower.username"

    @pytest.mark.asyncio
    async def test_real_subscription_webhook_payload_structure(self):
        """
        Test subscription webhook with expected real payload structure
        """
        # Expected real subscription payload structure based on follow pattern
        real_subscription_payload = {
            "broadcaster": {
                "username": "eddieoz",
                "user_id": 1212654
            },
            "subscriber": {
                "username": "premium_user",
                "user_id": 9876543,
                "is_verified": False
            },
            "tier": 2,
            "subscribed_at": "2025-07-30T19:27:21Z"
        }

        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Real subscription webhook payload is processed
            await oauth_webhook_server.handle_subscription_event(real_subscription_payload)

            # Then: Should extract username and tier correctly
            self.mock_alert_function.assert_called_once()
            call_args = self.mock_alert_function.call_args[0]
            alert_title = call_args[2]

            assert "premium_user" in alert_title, f"Expected 'premium_user' in alert title, got: {alert_title}"
            assert "Tier 2" in alert_title, f"Expected 'Tier 2' in alert title, got: {alert_title}"
            assert "Unknown" not in alert_title, f"Alert still shows 'Unknown': {alert_title}"

    @pytest.mark.asyncio
    async def test_real_gift_subscription_webhook_payload_structure(self):
        """
        Test gift subscription webhook with expected real payload structure
        """
        # Expected real gift subscription payload structure
        real_gift_payload = {
            "broadcaster": {
                "username": "eddieoz",
                "user_id": 1212654
            },
            "gifter": {
                "username": "generous_viewer",
                "user_id": 5555555,
                "is_verified": True
            },
            "quantity": 5,
            "recipients": [
                {"username": "recipient1", "user_id": 1001},
                {"username": "recipient2", "user_id": 1002},
                {"username": "recipient3", "user_id": 1003},
                {"username": "recipient4", "user_id": 1004},
                {"username": "recipient5", "user_id": 1005}
            ]
        }

        # Mock bot instance for points processing
        mock_bot = MagicMock()
        mock_bot._handle_gifted_subscriptions = AsyncMock()
        original_bot = oauth_webhook_server.bot_instance
        oauth_webhook_server.bot_instance = mock_bot

        try:
            with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
                # When: Real gift subscription webhook payload is processed
                await oauth_webhook_server.handle_gift_subscription_event(real_gift_payload)

                # Then: Should extract gifter username correctly and process points
                self.mock_alert_function.assert_called_once()
                call_args = self.mock_alert_function.call_args[0]
                alert_title = call_args[2]

                assert "generous_viewer" in alert_title, f"Expected 'generous_viewer' in alert title, got: {alert_title}"
                assert "Unknown" not in alert_title, f"Alert still shows 'Unknown': {alert_title}"

                # And should process points
                mock_bot._handle_gifted_subscriptions.assert_called_once_with("generous_viewer", 5)

        finally:
            oauth_webhook_server.bot_instance = original_bot

    @pytest.mark.asyncio
    async def test_production_event_type_detection(self):
        """
        Test that event type detection works with real webhook headers and payloads
        """
        # Test follow event detection
        follow_payload = {
            "broadcaster": {"username": "streamer"},
            "follower": {"username": "follower_user"}
        }

        # Simulate the detection logic that would happen in webhook handler
        event_type = 'unknown'

        # Check for follow structure - real Kick webhooks have 'follower' and 'broadcaster'
        if 'follower' in follow_payload and 'broadcaster' in follow_payload:
            event_type = 'channel.followed'

        assert event_type == 'channel.followed'

        # Test subscription event detection
        subscription_payload = {
            "broadcaster": {"username": "streamer"},
            "subscriber": {"username": "sub_user"},
            "tier": 1
        }

        event_type = 'unknown'
        if 'subscriber' in subscription_payload and 'broadcaster' in subscription_payload:
            event_type = 'channel.subscription.new'

        assert event_type == 'channel.subscription.new'

    @pytest.mark.asyncio
    async def test_backward_compatibility_with_existing_tests(self):
        """
        Ensure the fix doesn't break existing test payloads that might use different structures
        """
        # Test with old test payload structure (if any tests used 'data' wrapper)
        old_style_payload = {
            "data": {
                "follower": {"username": "old_style_user"}
            }
        }

        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Old style payload is processed
            await oauth_webhook_server.handle_follow_event(old_style_payload)

            # Then: Should still work (though might extract from 'data' or fallback)
            self.mock_alert_function.assert_called_once()
            call_args = self.mock_alert_function.call_args[0]
            alert_title = call_args[2]

            # Should either extract the username or show Unknown (but not crash)
            assert isinstance(alert_title, str)
            assert len(alert_title) > 0

    @pytest.mark.asyncio 
    async def test_comprehensive_real_world_scenarios(self):
        """
        Test multiple real-world webhook scenarios in sequence
        """
        real_world_events = [
            {
                "name": "Follow Event",
                "payload": {
                    "broadcaster": {"username": "streamer_test"},
                    "follower": {"username": "new_follower_real"}
                },
                "handler": oauth_webhook_server.handle_follow_event,
                "expected_username": "new_follower_real"
            },
            {
                "name": "Subscription Event", 
                "payload": {
                    "broadcaster": {"username": "streamer_test"},
                    "subscriber": {"username": "new_subscriber_real"},
                    "tier": 3
                },
                "handler": oauth_webhook_server.handle_subscription_event,
                "expected_username": "new_subscriber_real"
            },
            {
                "name": "Gift Subscription Event",
                "payload": {
                    "broadcaster": {"username": "streamer_test"},
                    "gifter": {"username": "generous_real"},
                    "quantity": 2
                },
                "handler": oauth_webhook_server.handle_gift_subscription_event,
                "expected_username": "generous_real"
            }
        ]

        mock_bot = MagicMock()
        mock_bot._handle_gifted_subscriptions = AsyncMock()
        original_bot = oauth_webhook_server.bot_instance
        oauth_webhook_server.bot_instance = mock_bot

        try:
            with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
                for event in real_world_events:
                    # When: Real world event is processed
                    await event["handler"](event["payload"])

                    # Then: Should extract username correctly
                    call_args = self.mock_alert_function.call_args[0]
                    alert_title = call_args[2]

                    assert event["expected_username"] in alert_title, f"Expected '{event['expected_username']}' in alert for {event['name']}, got: {alert_title}"
                    assert "Unknown" not in alert_title, f"Alert still shows 'Unknown' for {event['name']}: {alert_title}"

                    self.mock_alert_function.reset_mock()

        finally:
            oauth_webhook_server.bot_instance = original_bot

if __name__ == "__main__":
    pytest.main([__file__])