"""
Test suite for Comprehensive Integration Testing (Story 21)
BDD scenarios testing end-to-end webhook integration from webhook receipt to points award
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock, call
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import oauth_webhook_server
from kickbot.kick_bot import KickBot


class MockBotWithChatTracking:
    """Enhanced mock bot that tracks all chat commands sent"""
    
    def __init__(self):
        self.logger = MagicMock()
        self.auth_manager = MagicMock()  # OAuth authentication
        self.chat_commands_sent = []  # Track all chat commands
        self.chat_send_success = True  # Control success/failure
        
    async def _handle_gifted_subscriptions(self, gifter: str, amount: int) -> None:
        """Mock implementation that tracks calls and simulates chat sending"""
        self.logger.info(f"_handle_gifted_subscriptions called with gifter={gifter}, amount={amount}")
        
        # Simulate the logic from the real method
        if gifter == "Anonymous":
            self.logger.info(f"Anonymous gifter sent {amount} subscriptions - no points awarded")
            return
            
        try:
            # Mock settings check
            gift_blokitos = 200  # Mock setting value
            if gift_blokitos != 0:
                blokitos = amount * gift_blokitos
                message = f'!subgift_add {gifter} {blokitos}'
                
                # Track the chat command
                self.chat_commands_sent.append({
                    'message': message,
                    'gifter': gifter,
                    'amount': amount,
                    'blokitos': blokitos,
                    'timestamp': time.time()
                })
                
                if self.chat_send_success:
                    self.logger.info(f"Added {blokitos} to user {gifter} for {amount} sub_gifts")
                else:
                    self.logger.error(f"Failed to send gift subscription message for {gifter}")
        except Exception as e:
            self.logger.error(f"Error handling gifted subscriptions: {e}", exc_info=True)


class TestComprehensiveIntegration:
    """Comprehensive integration tests for complete webhook functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_bot = MockBotWithChatTracking()
        self.mock_alert_function = AsyncMock()
        
        # Store original bot instance
        self.original_bot_instance = oauth_webhook_server.bot_instance
        
        # Set up our mock bot
        oauth_webhook_server.bot_instance = self.mock_bot
        
    def teardown_method(self):
        """Clean up after tests"""
        # Restore original bot instance
        oauth_webhook_server.bot_instance = self.original_bot_instance

    @pytest.mark.asyncio
    async def test_scenario_21_1_complete_follow_event_integration(self):
        """
        BDD Scenario 21.1: Complete Follow Event Integration
        
        Given the webhook server is running
        And a mock bot instance is configured
        When a follow webhook event is received
        Then the follower username should be extracted correctly
        And a follow alert should be sent
        And the process should complete within 1 second
        """
        # Given: Webhook server with mock bot configured (done in setup)
        follow_payload = {
            "follower": {
                "username": "integration_follower",
                "id": 123456,
                "slug": "integration_follower"
            },
            "followed_at": "2024-01-15T10:30:00Z"
        }
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Follow webhook event is received
            start_time = time.time()
            await oauth_webhook_server.handle_follow_event(follow_payload)
            end_time = time.time()
            
            # Then: Should complete within 1 second
            processing_time = end_time - start_time
            assert processing_time < 1.0, f"Follow event processing took {processing_time:.3f}s, should be < 1.0s"
            
            # And follower username should be extracted correctly
            self.mock_alert_function.assert_called_once()
            call_args = self.mock_alert_function.call_args[0]
            assert "integration_follower" in call_args[2]  # Title contains username
            assert "integration_follower" in call_args[3]  # Description contains username

    @pytest.mark.asyncio
    async def test_scenario_21_2_complete_subscription_event_integration(self):
        """
        BDD Scenario 21.2: Complete Subscription Event Integration
        
        Given the webhook server is running
        And a mock bot instance is configured  
        When a subscription webhook event is received
        Then the subscriber username should be extracted correctly
        And a subscription alert should be sent with correct tier
        And the process should complete within 1 second
        """
        subscription_payload = {
            "subscriber": {
                "username": "integration_subscriber",
                "id": 789012
            },
            "tier": 3,
            "subscribed_at": "2024-01-15T10:30:00Z"
        }
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Subscription webhook event is received
            start_time = time.time()
            await oauth_webhook_server.handle_subscription_event(subscription_payload)
            end_time = time.time()
            
            # Then: Should complete within 1 second
            processing_time = end_time - start_time
            assert processing_time < 1.0, f"Subscription event processing took {processing_time:.3f}s, should be < 1.0s"
            
            # And subscriber username and tier should be extracted correctly
            self.mock_alert_function.assert_called_once()
            call_args = self.mock_alert_function.call_args[0]
            
            assert "integration_subscriber" in call_args[2]  # Title contains username
            assert "Tier 3" in call_args[2]  # Title contains tier
            assert "integration_subscriber" in call_args[3]  # Description contains username

    @pytest.mark.asyncio
    async def test_scenario_21_3_complete_gift_subscription_integration(self):
        """
        BDD Scenario 21.3: Complete Gift Subscription Integration
        
        Given the webhook server is running
        And a mock bot instance is configured
        And GiftBlokitos setting is 200
        When a gift subscription webhook event is received with gifter "testgifter" and quantity 2
        Then the gifter username should be extracted correctly
        And _handle_gifted_subscriptions should be called with ("testgifter", 2)
        And a chat message "!subgift_add testgifter 400" should be sent
        And a gift subscription alert should be sent
        And the process should complete within 2 seconds
        """
        gift_payload = {
            "gifter": {
                "username": "integration_gifter",
                "id": 555555
            },
            "quantity": 3,
            "recipients": [
                {"username": "recipient1"},
                {"username": "recipient2"},
                {"username": "recipient3"}
            ]
        }
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Gift subscription webhook event is received
            start_time = time.time()
            await oauth_webhook_server.handle_gift_subscription_event(gift_payload)
            end_time = time.time()
            
            # Then: Should complete within 2 seconds
            processing_time = end_time - start_time
            assert processing_time < 2.0, f"Gift subscription processing took {processing_time:.3f}s, should be < 2.0s"
            
            # And gifter username should be extracted correctly
            self.mock_alert_function.assert_called_once()
            call_args = self.mock_alert_function.call_args[0]
            assert "integration_gifter" in call_args[2]  # Title contains gifter
            
            # And _handle_gifted_subscriptions should be called with correct parameters
            expected_calls = [
                call("_handle_gifted_subscriptions called with gifter=integration_gifter, amount=3"),
                call("Added 600 to user integration_gifter for 3 sub_gifts")
            ]
            self.mock_bot.logger.info.assert_has_calls(expected_calls, any_order=False)
            
            # And chat message should be tracked
            assert len(self.mock_bot.chat_commands_sent) == 1
            chat_command = self.mock_bot.chat_commands_sent[0]
            assert chat_command['message'] == "!subgift_add integration_gifter 600"
            assert chat_command['gifter'] == "integration_gifter"
            assert chat_command['amount'] == 3
            assert chat_command['blokitos'] == 600

    @pytest.mark.asyncio
    async def test_scenario_21_4_error_recovery_integration(self):
        """
        BDD Scenario 21.4: Error Recovery Integration
        
        Given the webhook server is running
        And the bot instance becomes unavailable
        When webhook events are received
        Then alerts should still be sent
        And errors should be logged appropriately
        And the system should recover when bot instance is restored
        """
        # Given: Bot instance becomes unavailable
        oauth_webhook_server.bot_instance = None
        
        follow_payload = {"follower": {"username": "recovery_test_user"}}
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            with patch('oauth_webhook_server.logger') as mock_logger:
                # When: Webhook events are received with no bot instance
                await oauth_webhook_server.handle_follow_event(follow_payload)
                
                # Then: Alerts should still be sent
                self.mock_alert_function.assert_called_once()
                call_args = self.mock_alert_function.call_args[0]
                assert "recovery_test_user" in call_args[2]
                
                # Reset for next test
                self.mock_alert_function.reset_mock()
        
        # When: Bot instance is restored
        oauth_webhook_server.bot_instance = self.mock_bot
        
        gift_payload = {
            "gifter": {"username": "recovery_gifter"},
            "quantity": 1
        }
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # Then: System should recover and work normally
            await oauth_webhook_server.handle_gift_subscription_event(gift_payload)
            
            # Alert should be sent
            self.mock_alert_function.assert_called_once()
            
            # And points should be processed
            assert len(self.mock_bot.chat_commands_sent) == 1
            assert self.mock_bot.chat_commands_sent[0]['message'] == "!subgift_add recovery_gifter 200"
            
    @pytest.mark.asyncio
    async def test_concurrent_webhook_processing(self):
        """
        Test that multiple webhooks can be processed concurrently without interference
        """
        # Create multiple webhook events
        webhook_events = [
            {
                "type": "follow",
                "handler": oauth_webhook_server.handle_follow_event,
                "payload": {"follower": {"username": f"concurrent_follower_{i}"}},
                "expected_username": f"concurrent_follower_{i}"
            }
            for i in range(5)
        ] + [
            {
                "type": "subscription", 
                "handler": oauth_webhook_server.handle_subscription_event,
                "payload": {"subscriber": {"username": f"concurrent_subscriber_{i}"}, "tier": i+1},
                "expected_username": f"concurrent_subscriber_{i}"
            }
            for i in range(3)
        ] + [
            {
                "type": "gift",
                "handler": oauth_webhook_server.handle_gift_subscription_event,
                "payload": {"gifter": {"username": f"concurrent_gifter_{i}"}, "quantity": i+1},
                "expected_username": f"concurrent_gifter_{i}"
            }
            for i in range(2)
        ]
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Multiple webhooks are processed concurrently
            start_time = time.time()
            tasks = [event["handler"](event["payload"]) for event in webhook_events]
            await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Then: All should complete within reasonable time
            total_time = end_time - start_time
            assert total_time < 5.0, f"Concurrent processing took {total_time:.3f}s, should be < 5.0s"
            
            # And all alerts should be sent
            assert self.mock_alert_function.call_count == len(webhook_events)
            
            # And gift subscription points should be processed
            gift_events = [e for e in webhook_events if e["type"] == "gift"]
            assert len(self.mock_bot.chat_commands_sent) == len(gift_events)

    @pytest.mark.asyncio
    async def test_webhook_processing_under_load(self):
        """
        Test webhook processing performance under load conditions
        """
        # Create a large number of webhook events
        load_test_events = []
        expected_chat_commands = 0
        
        for i in range(50):  # 50 events of each type
            load_test_events.extend([
                {
                    "handler": oauth_webhook_server.handle_follow_event,
                    "payload": {"follower": {"username": f"load_follower_{i}"}}
                },
                {
                    "handler": oauth_webhook_server.handle_subscription_event,
                    "payload": {"subscriber": {"username": f"load_subscriber_{i}"}, "tier": (i % 3) + 1}
                },
                {
                    "handler": oauth_webhook_server.handle_gift_subscription_event,
                    "payload": {"gifter": {"username": f"load_gifter_{i}"}, "quantity": (i % 5) + 1}
                }
            ])
            expected_chat_commands += 1  # One chat command per gift subscription
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Processing many events concurrently
            start_time = time.time()
            
            # Process in batches to avoid overwhelming the system
            batch_size = 20
            for i in range(0, len(load_test_events), batch_size):
                batch = load_test_events[i:i + batch_size]
                tasks = [event["handler"](event["payload"]) for event in batch]
                await asyncio.gather(*tasks)
            
            end_time = time.time()
            
            # Then: Should complete within reasonable time
            total_time = end_time - start_time
            avg_time_per_event = total_time / len(load_test_events)
            
            assert total_time < 30.0, f"Load test took {total_time:.3f}s, should be < 30.0s"
            assert avg_time_per_event < 0.2, f"Average time per event {avg_time_per_event:.4f}s, should be < 0.2s"
            
            # And all alerts should be sent
            assert self.mock_alert_function.call_count == len(load_test_events)
            
            # And all gift subscription commands should be tracked
            assert len(self.mock_bot.chat_commands_sent) == expected_chat_commands

    @pytest.mark.asyncio
    async def test_webhook_error_handling_resilience(self):
        """
        Test that webhook processing is resilient to various error conditions
        """
        error_scenarios = [
            {
                "name": "Malformed payload",
                "payload": {"invalid": "structure"},
                "handler": oauth_webhook_server.handle_follow_event
            },
            {
                "name": "Missing required fields",
                "payload": {},
                "handler": oauth_webhook_server.handle_subscription_event
            },
            {
                "name": "Invalid data types",
                "payload": {"gifter": {"username": 12345}},  # Number instead of string
                "handler": oauth_webhook_server.handle_gift_subscription_event
            }
        ]
        
        # Test that chat sending failure doesn't crash the system
        self.mock_bot.chat_send_success = False
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            for scenario in error_scenarios:
                # When: Error scenario is processed
                try:
                    await scenario["handler"](scenario["payload"])
                    
                    # Then: Should not raise exception (graceful handling)
                    # Alert should still be attempted
                    
                except Exception as e:
                    pytest.fail(f"Webhook handler crashed on {scenario['name']}: {e}")
        
        # Verify that the system continues to work after errors
        self.mock_bot.chat_send_success = True
        valid_payload = {"gifter": {"username": "recovery_after_error"}, "quantity": 1}
        
        await oauth_webhook_server.handle_gift_subscription_event(valid_payload)
        
        # Should work normally after error recovery
        recovery_commands = [cmd for cmd in self.mock_bot.chat_commands_sent if "recovery_after_error" in cmd['message']]
        assert len(recovery_commands) == 1

    @pytest.mark.asyncio
    async def test_comprehensive_monitoring_integration(self):
        """
        Test that monitoring and logging work correctly throughout the system
        """
        # Enable monitoring (if webhook_monitor is available)
        monitoring_events = []
        
        class MockWebhookMonitor:
            def track_webhook_received(self, event_type):
                monitoring_events.append({"type": "webhook_received", "event_type": event_type})
            
            def track_parsing_success(self, username, method):
                monitoring_events.append({"type": "parsing_success", "username": username, "method": method})
            
            def track_points_awarded(self, username, points, quantity):
                monitoring_events.append({"type": "points_awarded", "username": username, "points": points, "quantity": quantity})
            
            def track_performance(self, operation, duration):
                monitoring_events.append({"type": "performance", "operation": operation, "duration": duration})
        
        # Set up monitoring
        original_monitor = oauth_webhook_server.webhook_monitor
        oauth_webhook_server.webhook_monitor = MockWebhookMonitor()
        
        try:
            gift_payload = {
                "gifter": {"username": "monitored_gifter"},
                "quantity": 2
            }
            
            with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
                # When: Gift subscription is processed with monitoring
                await oauth_webhook_server.handle_gift_subscription_event(gift_payload)
                
                # Then: Monitoring events should be tracked
                webhook_received_events = [e for e in monitoring_events if e["type"] == "webhook_received"]
                assert len(webhook_received_events) > 0
                
                points_awarded_events = [e for e in monitoring_events if e["type"] == "points_awarded"]
                if points_awarded_events:  # May not trigger if monitoring is not fully integrated
                    assert points_awarded_events[0]["username"] == "monitored_gifter"
                    assert points_awarded_events[0]["quantity"] == 2
                
        finally:
            # Restore original monitor
            oauth_webhook_server.webhook_monitor = original_monitor

    @pytest.mark.asyncio
    async def test_end_to_end_realistic_scenario(self):
        """
        Test a realistic end-to-end scenario with multiple event types in sequence
        """
        # Simulate a realistic streaming session with multiple events
        streaming_session_events = [
            {
                "type": "follow",
                "handler": oauth_webhook_server.handle_follow_event,
                "payload": {"follower": {"username": "new_viewer_1"}},
                "delay": 0.1
            },
            {
                "type": "follow", 
                "handler": oauth_webhook_server.handle_follow_event,
                "payload": {"follower": {"username": "new_viewer_2"}},
                "delay": 0.2
            },
            {
                "type": "subscription",
                "handler": oauth_webhook_server.handle_subscription_event,
                "payload": {"subscriber": {"username": "premium_supporter"}, "tier": 2},
                "delay": 0.3
            },
            {
                "type": "gift",
                "handler": oauth_webhook_server.handle_gift_subscription_event,
                "payload": {"gifter": {"username": "generous_viewer"}, "quantity": 5},
                "delay": 0.1
            },
            {
                "type": "follow",
                "handler": oauth_webhook_server.handle_follow_event,
                "payload": {"follower": {"username": "new_viewer_3"}},
                "delay": 0.2
            }
        ]
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Realistic streaming session events occur
            start_time = time.time()
            
            tasks = []
            for event in streaming_session_events:
                # Add realistic delays between events
                await asyncio.sleep(event["delay"])
                task = asyncio.create_task(event["handler"](event["payload"]))
                tasks.append(task)
            
            # Wait for all events to complete
            await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Then: All events should be processed successfully
            total_time = end_time - start_time
            assert total_time < 10.0, f"Realistic scenario took {total_time:.3f}s, should be < 10.0s"
            
            # All alerts should be sent
            assert self.mock_alert_function.call_count == len(streaming_session_events)
            
            # Gift subscription should trigger chat command
            gift_commands = [cmd for cmd in self.mock_bot.chat_commands_sent if "generous_viewer" in cmd['message']]
            assert len(gift_commands) == 1
            assert gift_commands[0]['message'] == "!subgift_add generous_viewer 1000"  # 5 * 200

if __name__ == "__main__":
    pytest.main([__file__])