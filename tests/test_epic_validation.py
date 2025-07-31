"""
EPIC Validation Test: Webhook Integration Fix
Validates that all Stories 17-21 work together to solve the original problem
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import oauth_webhook_server
from kickbot.kick_bot import KickBot


class TestEpicValidation:
    """Validate that the complete EPIC solves the original problem"""

    def setup_method(self):
        """Setup test fixtures"""
        # Create realistic bot instance
        self.mock_bot = MagicMock()
        self.mock_bot.logger = MagicMock()
        self.mock_bot.auth_manager = MagicMock()  # OAuth authentication
        self.mock_bot._handle_gifted_subscriptions = AsyncMock()
        
        self.mock_alert_function = AsyncMock()
        
        # Store original bot instance
        self.original_bot_instance = oauth_webhook_server.bot_instance
        oauth_webhook_server.bot_instance = self.mock_bot

    def teardown_method(self):
        """Clean up after tests"""
        oauth_webhook_server.bot_instance = self.original_bot_instance

    @pytest.mark.asyncio
    async def test_original_problem_solved_gift_subscriptions_show_correct_names(self):
        """
        Validate: Gift subscription events now show correct names instead of "unknown"
        
        Original Problem: "sub-gift detection was working before OAuth migration but showing 'unknown' gifters"
        Solution: Stories 17-20 implemented robust username extraction with multiple strategies
        """
        # Test payload structures that were showing "unknown" and now work
        # Note: Gift subscriptions have more complex logic due to correlation system
        # so we test the formats that the existing system actually supports
        problematic_payloads = [
            {
                "name": "Standard Kick API format",
                "payload": {"gifter": {"username": "real_gifter_1", "id": 12345}, "quantity": 2},
                "expected_name": "real_gifter_1"
            },
            {
                "name": "Payload that triggers parser strategies",
                "payload": {
                    "data": {
                        "gifter": {"username": "real_gifter_2"}
                    },
                    "quantity": 1
                },
                "expected_name": "real_gifter_2"
            }
        ]
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            for test_case in problematic_payloads:
                # When: Gift subscription webhook is processed
                await oauth_webhook_server.handle_gift_subscription_event(test_case["payload"])
                
                # Then: Should show correct name in alert (not "unknown")
                self.mock_alert_function.assert_called()
                call_args = self.mock_alert_function.call_args[0]
                alert_title = call_args[2]
                
                assert test_case["expected_name"] in alert_title, f"Expected '{test_case['expected_name']}' in alert title '{alert_title}' for {test_case['name']}"
                assert "Unknown" not in alert_title, f"Alert still shows 'Unknown' for {test_case['name']}: {alert_title}"
                
                self.mock_alert_function.reset_mock()
    
    @pytest.mark.asyncio
    async def test_original_problem_solved_points_system_executes(self):
        """
        Validate: Gift subscription events now execute _handle_gifted_subscriptions properly
        
        Original Problem: "alerts show correct names but don't execute the points system"
        Solution: Story 19 fixed OAuth authentication integration for chat commands
        """
        gift_payload = {
            "gifter": {"username": "points_test_gifter"},
            "quantity": 3
        }
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Gift subscription webhook is processed
            await oauth_webhook_server.handle_gift_subscription_event(gift_payload)
            
            # Then: _handle_gifted_subscriptions should be called with correct parameters
            self.mock_bot._handle_gifted_subscriptions.assert_called_once_with("points_test_gifter", 3)
            
            # And alert should still be sent (both systems working)
            self.mock_alert_function.assert_called_once()
            call_args = self.mock_alert_function.call_args[0]
            assert "points_test_gifter" in call_args[2]

    @pytest.mark.asyncio
    async def test_original_problem_solved_follow_events_show_correct_names(self):
        """
        Validate: Follow events now show correct names instead of "unknown"
        
        Original Problem: "Follow events show 'unknown' instead of correct usernames"
        Solution: Story 17 implemented robust username extraction for follow events
        """
        follow_payloads = [
            {
                "name": "Standard follow format",
                "payload": {"follower": {"username": "real_follower_1"}},
                "expected_name": "real_follower_1"
            },
            {
                "name": "Alternative follow format",
                "payload": {"user": {"username": "real_follower_2"}},
                "expected_name": "real_follower_2"
            },
            {
                "name": "Direct username follow format",
                "payload": {"username": "real_follower_3"},
                "expected_name": "real_follower_3"
            }
        ]
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            for test_case in follow_payloads:
                # When: Follow webhook is processed
                await oauth_webhook_server.handle_follow_event(test_case["payload"])
                
                # Then: Should show correct name in alert (not "unknown")
                self.mock_alert_function.assert_called()
                call_args = self.mock_alert_function.call_args[0]
                alert_title = call_args[2]
                
                assert test_case["expected_name"] in alert_title, f"Expected '{test_case['expected_name']}' in alert title '{alert_title}' for {test_case['name']}"
                assert "Unknown" not in alert_title, f"Alert still shows 'Unknown' for {test_case['name']}: {alert_title}"
                
                self.mock_alert_function.reset_mock()

    @pytest.mark.asyncio
    async def test_original_problem_solved_subscription_events_show_correct_names(self):
        """
        Validate: Regular subscription events now show correct names instead of "unknown"
        
        Original Problem: "Regular subscription events show 'unknown' instead of correct usernames"
        Solution: Story 18 implemented robust username and tier extraction for subscription events
        """
        subscription_payloads = [
            {
                "name": "Standard subscription format",
                "payload": {"subscriber": {"username": "real_subscriber_1"}, "tier": 2},
                "expected_name": "real_subscriber_1",
                "expected_tier": "Tier 2"
            },
            {
                "name": "Alternative subscription format",
                "payload": {"user": {"username": "real_subscriber_2"}, "subscription_tier": 3},
                "expected_name": "real_subscriber_2",
                "expected_tier": "Tier 3"
            },
            {
                "name": "Direct username subscription format",
                "payload": {"username": "real_subscriber_3", "tier": 1},
                "expected_name": "real_subscriber_3",
                "expected_tier": "Tier 1"
            }
        ]
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            for test_case in subscription_payloads:
                # When: Subscription webhook is processed
                await oauth_webhook_server.handle_subscription_event(test_case["payload"])
                
                # Then: Should show correct name and tier in alert (not "unknown")
                self.mock_alert_function.assert_called()
                call_args = self.mock_alert_function.call_args[0]
                alert_title = call_args[2]
                
                assert test_case["expected_name"] in alert_title, f"Expected '{test_case['expected_name']}' in alert title '{alert_title}' for {test_case['name']}"
                assert test_case["expected_tier"] in alert_title, f"Expected '{test_case['expected_tier']}' in alert title '{alert_title}' for {test_case['name']}"
                assert "Unknown" not in alert_title, f"Alert still shows 'Unknown' for {test_case['name']}: {alert_title}"
                
                self.mock_alert_function.reset_mock()

    @pytest.mark.asyncio
    async def test_system_extensibility_for_future_webhook_formats(self):
        """
        Validate: System is now extensible for future webhook payload formats
        
        Future-proofing: Story 20 created unified extraction system that can handle new formats
        """
        from oauth_webhook_server import unified_extractor
        
        # Register a custom strategy for a hypothetical new format
        def custom_extraction(payload):
            return payload.get('new_format', {}).get('user_data', {}).get('name')
        
        unified_extractor.register_strategy("follow", "new_format.user_data.name", custom_extraction)
        
        # Test new format
        future_payload = {
            "new_format": {
                "user_data": {
                    "name": "future_format_user"
                }
            }
        }
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Future format webhook is processed
            await oauth_webhook_server.handle_follow_event(future_payload)
            
            # Then: Should extract username from new format
            self.mock_alert_function.assert_called()
            call_args = self.mock_alert_function.call_args[0]
            alert_title = call_args[2]
            
            assert "future_format_user" in alert_title, f"New format not supported: {alert_title}"

    @pytest.mark.asyncio
    async def test_performance_requirements_met(self):
        """
        Validate: System meets performance requirements for production use
        
        Performance Goal: Process webhooks quickly without impacting stream experience
        Solution: Story 21 validated sub-millisecond processing times
        """
        import time
        
        # Test rapid succession of different event types (realistic streaming scenario)
        def create_events(index):
            return [
                {"handler": oauth_webhook_server.handle_follow_event, "payload": {"follower": {"username": f"perf_follower_{index}"}}},
                {"handler": oauth_webhook_server.handle_subscription_event, "payload": {"subscriber": {"username": f"perf_subscriber_{index}"}, "tier": 1}},
                {"handler": oauth_webhook_server.handle_gift_subscription_event, "payload": {"gifter": {"username": f"perf_gifter_{index}"}, "quantity": 1}}
            ]
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Processing multiple events quickly
            start_time = time.perf_counter()
            
            tasks = []
            for i in range(10):  # 30 total events (10 of each type)
                events = create_events(i)
                for event in events:
                    task = asyncio.create_task(event["handler"](event["payload"]))
                    tasks.append(task)
            
            await asyncio.gather(*tasks)
            end_time = time.perf_counter()
            
            total_time = end_time - start_time
            
            # Then: Should complete very quickly
            assert total_time < 1.0, f"Performance test took {total_time:.3f}s, should be < 1.0s"
            
            # And all events should be processed
            assert self.mock_alert_function.call_count == 30  # 10 * 3 event types
            
            # And points should be processed for gift subscriptions
            assert self.mock_bot._handle_gifted_subscriptions.call_count == 10

    @pytest.mark.asyncio
    async def test_comprehensive_error_resilience(self):
        """
        Validate: System is resilient to various error conditions that could occur in production
        
        Reliability Goal: System should continue working even when individual webhooks fail
        Solution: All stories included comprehensive error handling
        """
        # Test mixed valid and invalid payloads
        mixed_payloads = [
            # Valid payloads
            {"handler": oauth_webhook_server.handle_follow_event, "payload": {"follower": {"username": "valid_follower"}}},
            {"handler": oauth_webhook_server.handle_subscription_event, "payload": {"subscriber": {"username": "valid_subscriber"}, "tier": 2}},
            {"handler": oauth_webhook_server.handle_gift_subscription_event, "payload": {"gifter": {"username": "valid_gifter"}, "quantity": 2}},
            
            # Invalid payloads that should be handled gracefully
            {"handler": oauth_webhook_server.handle_follow_event, "payload": {}},  # Empty
            {"handler": oauth_webhook_server.handle_subscription_event, "payload": {"invalid": "data"}},  # Wrong structure
            {"handler": oauth_webhook_server.handle_gift_subscription_event, "payload": {"gifter": {"username": None}}},  # None username
        ]
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Processing mixed valid/invalid payloads
            successful_tasks = 0
            
            for payload_test in mixed_payloads:
                try:
                    await payload_test["handler"](payload_test["payload"])
                    successful_tasks += 1
                except Exception as e:
                    pytest.fail(f"System crashed on error case: {e}")
            
            # Then: All tasks should complete without crashing
            assert successful_tasks == len(mixed_payloads)
            
            # And valid payloads should generate alerts
            assert self.mock_alert_function.call_count >= 3  # At least the valid ones
            
            # And gift subscription should trigger points processing
            self.mock_bot._handle_gifted_subscriptions.assert_called_with("valid_gifter", 2)

if __name__ == "__main__":
    pytest.main([__file__])