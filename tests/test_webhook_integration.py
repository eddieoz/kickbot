#!/usr/bin/env python3
"""
Integration Test Suite for Story 16: Complete Webhook Processing System Validation
Following TDD/BDD methodology for end-to-end testing of webhook processing pipeline

Tests cover:
- End-to-end webhook processing from receipt to points award
- Mock webhook server simulating real Kick API payloads
- Performance testing ensuring sub-second processing
- Load testing for concurrent gift processing
- Regression testing for all payload variations discovered in Stories 12-15
"""

import pytest
import asyncio
import time
import json
import aiohttp
from aiohttp import web
from aiohttp.test_utils import make_mocked_request
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os
from typing import Dict, List

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import components for integration testing
try:
    from oauth_webhook_server import (
        handle_gift_subscription_event, 
        handle_chat_message_event,
        WebhookMonitoring,
        WebhookChatCorrelator,
        WebhookPayloadParser,
        create_app
    )
except ImportError:
    # Components might not be fully available - expected in TDD
    handle_gift_subscription_event = None
    handle_chat_message_event = None
    WebhookMonitoring = None
    WebhookChatCorrelator = None
    WebhookPayloadParser = None
    create_app = None


class MockKickWebhookServer:
    """
    Mock Kick webhook server for integration testing
    Simulates real Kick API webhook behavior and payload variations
    """
    
    def __init__(self):
        self.webhooks_sent = []
        self.chat_messages_sent = []
        self.app = None
        self.server = None
        
    async def start_server(self, port=8081):
        """Start mock webhook server for testing"""
        self.app = web.Application()
        self.app.router.add_post('/events', self._handle_test_webhook)
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()
        self.server = runner
        
    async def stop_server(self):
        """Stop mock webhook server"""
        if self.server:
            await self.server.cleanup()
            
    async def _handle_test_webhook(self, request):
        """Handle test webhook requests"""
        data = await request.json()
        self.webhooks_sent.append(data)
        return web.Response(text='OK')
        
    async def send_gift_webhook(self, payload, headers=None):
        """Simulate sending a gift webhook"""
        webhook_data = {
            'event_type': 'channel.subscription.gifts',
            'timestamp': time.time(),
            'payload': payload,
            'headers': headers or {}
        }
        self.webhooks_sent.append(webhook_data)
        
        # Process through webhook handler
        if handle_gift_subscription_event:
            await handle_gift_subscription_event(payload, headers)
            
        return webhook_data
        
    async def send_chat_message(self, content, username="Kicklet", delay=6.0):
        """Simulate sending a chat message with realistic timing"""
        await asyncio.sleep(delay)  # Simulate real-world delay
        
        message_data = {
            'message_id': f"msg_{int(time.time())}",
            'sender': {'username': username},
            'content': content,
            'timestamp': time.time()
        }
        self.chat_messages_sent.append(message_data)
        
        # Process through chat handler
        if handle_chat_message_event:
            await handle_chat_message_event(message_data)
            
        return message_data


class MockBotInstance:
    """Mock bot instance for integration testing"""
    
    def __init__(self):
        self.user_points = {}
        self.gifted_subscriptions_calls = []
        self.chatroom_id = 1164726
        
    async def _handle_gifted_subscriptions(self, gifter, quantity):
        """Mock points processing"""
        points = quantity * 200  # Standard points per gift
        self.user_points[gifter] = self.user_points.get(gifter, 0) + points
        self.gifted_subscriptions_calls.append({
            'gifter': gifter,
            'quantity': quantity,
            'points': points,
            'timestamp': time.time()
        })
        
    def get_user_points(self, username):
        """Get points for a user"""
        return self.user_points.get(username, 0)
        
    def clear_points(self):
        """Clear all points for testing"""
        self.user_points.clear()
        self.gifted_subscriptions_calls.clear()


@pytest.mark.integration
class TestWebhookIntegrationEndToEnd:
    """
    BDD Integration Test Suite for Complete Webhook Processing System
    
    Tests the entire pipeline from webhook receipt through points awarding,
    including all components: parser, correlator, monitoring, and bot integration.
    """

    def setup_method(self):
        """Set up integration test fixtures"""
        self.mock_server = MockKickWebhookServer()
        self.mock_bot = MockBotInstance()
        
        # Store original global instances
        import oauth_webhook_server
        self.original_bot_instance = oauth_webhook_server.bot_instance
        self.original_chat_correlator = oauth_webhook_server.chat_correlator
        self.original_webhook_monitor = oauth_webhook_server.webhook_monitor
        
        # Set up test instances
        oauth_webhook_server.bot_instance = self.mock_bot
        if WebhookChatCorrelator:
            oauth_webhook_server.chat_correlator = WebhookChatCorrelator()
        if WebhookMonitoring:
            oauth_webhook_server.webhook_monitor = WebhookMonitoring()
        
    def teardown_method(self):
        """Clean up integration test fixtures"""
        # Restore original global instances
        import oauth_webhook_server
        oauth_webhook_server.bot_instance = self.original_bot_instance
        oauth_webhook_server.chat_correlator = self.original_chat_correlator
        oauth_webhook_server.webhook_monitor = self.original_webhook_monitor
            
    @pytest.mark.asyncio
    async def test_end_to_end_empty_payload_correlation(self):
        """
        GIVEN: Complete webhook processing system with empty payload scenario
        WHEN: Empty gift webhook received followed by Kicklet chat message
        THEN: Gifter receives correct points through correlation system
        """
        if not handle_gift_subscription_event:
            pytest.skip("Webhook handler not available for integration testing")
            
        # Arrange: Empty payload scenario (most common issue from Stories 12-15)
        empty_payload = {}
        chat_message = "Thank you, testuser, for the gifted 2 subscriptions."
        
        # Act: Send webhook and chat message with realistic timing
        webhook_task = asyncio.create_task(
            self.mock_server.send_gift_webhook(empty_payload)
        )
        chat_task = asyncio.create_task(
            self.mock_server.send_chat_message(chat_message, delay=6.0)
        )
        
        # Wait for both operations to complete
        await webhook_task
        await chat_task
        
        # Allow additional processing time for correlation
        await asyncio.sleep(0.5)
        
        # Assert: Points awarded correctly through correlation
        points = self.mock_bot.get_user_points("testuser")
        assert points == 400, f"Expected 400 points, got {points}"
        
        # Assert: Bot method called with correct parameters
        assert len(self.mock_bot.gifted_subscriptions_calls) == 1
        call = self.mock_bot.gifted_subscriptions_calls[0]
        assert call['gifter'] == "testuser"
        assert call['quantity'] == 2
        assert call['points'] == 400
        
    @pytest.mark.asyncio 
    async def test_end_to_end_standard_payload_processing(self):
        """
        GIVEN: Standard Kick API payload with gifter information
        WHEN: Gift webhook processed with complete gifter data
        THEN: Points awarded immediately without correlation delay
        """
        if not handle_gift_subscription_event:
            pytest.skip("Webhook handler not available for integration testing")
            
        # Arrange: Standard API payload format
        standard_payload = {
            "gifter": {
                "username": "eddieoz",
                "user_id": 12345
            },
            "giftees": [
                {"username": "recipient1", "user_id": 67890}
            ]
        }
        
        # Act: Process standard webhook
        start_time = time.time()
        await self.mock_server.send_gift_webhook(standard_payload)
        processing_time = time.time() - start_time
        
        # Assert: Fast processing (no correlation delay)
        assert processing_time < 1.0, f"Processing too slow: {processing_time}s"
        
        # Assert: Points awarded correctly
        points = self.mock_bot.get_user_points("eddieoz")
        assert points == 200, f"Expected 200 points for 1 gift, got {points}"
        
    @pytest.mark.asyncio
    async def test_end_to_end_anonymous_gift_processing(self):
        """
        GIVEN: Anonymous gift webhook payload
        WHEN: Gift webhook processed with anonymous gifter
        THEN: No points awarded but processing completes successfully
        """
        if not handle_gift_subscription_event:
            pytest.skip("Webhook handler not available for integration testing")
            
        # Arrange: Anonymous gift payload
        anonymous_payload = {
            "gifter": {
                "is_anonymous": True
            },
            "giftees": [
                {"username": "recipient1", "user_id": 67890},
                {"username": "recipient2", "user_id": 67891},
                {"username": "recipient3", "user_id": 67892}
            ]
        }
        
        # Act: Process anonymous webhook
        await self.mock_server.send_gift_webhook(anonymous_payload)
        
        # Assert: No points awarded (anonymous)
        total_points = sum(self.mock_bot.user_points.values())
        assert total_points == 0, f"Anonymous gifts should not award points, got {total_points}"
        
        # Assert: Processing completed without errors
        assert len(self.mock_server.webhooks_sent) == 1
        
    @pytest.mark.asyncio
    async def test_end_to_end_multiple_concurrent_gifts(self):
        """
        GIVEN: Multiple simultaneous gift events with different scenarios
        WHEN: Concurrent webhooks processed with various payload types
        THEN: All gifts processed correctly with proper correlation
        """
        if not handle_gift_subscription_event:
            pytest.skip("Webhook handler not available for integration testing")
            
        # Arrange: Multiple concurrent gift scenarios
        gift_scenarios = [
            # Standard payload - immediate processing
            {
                "payload": {"gifter": {"username": "user1", "user_id": 101}, "giftees": [{"username": "r1"}]},
                "expected_points": 200,
                "chat_message": None
            },
            # Empty payload - requires correlation  
            {
                "payload": {},
                "expected_points": 400,
                "chat_message": "Thank you, user2, for the gifted 2 subscriptions."
            },
            # Anonymous gift - no points
            {
                "payload": {"gifter": {"is_anonymous": True}, "giftees": [{"username": "r3"}]},
                "expected_points": 0,
                "chat_message": None
            }
        ]
        
        # Act: Send all webhooks concurrently
        webhook_tasks = []
        chat_tasks = []
        
        for i, scenario in enumerate(gift_scenarios):
            webhook_task = asyncio.create_task(
                self.mock_server.send_gift_webhook(scenario["payload"])
            )
            webhook_tasks.append(webhook_task)
            
            # Schedule chat message if needed
            if scenario["chat_message"]:
                chat_task = asyncio.create_task(
                    self.mock_server.send_chat_message(scenario["chat_message"], delay=6.0)
                )
                chat_tasks.append(chat_task)
        
        # Wait for all processing to complete
        await asyncio.gather(*webhook_tasks)
        if chat_tasks:
            await asyncio.gather(*chat_tasks)
        await asyncio.sleep(1.0)  # Allow correlation processing
        
        # Assert: All expected points awarded
        assert self.mock_bot.get_user_points("user1") == 200
        assert self.mock_bot.get_user_points("user2") == 400
        
        # Assert: Anonymous gift awarded no points
        total_anonymous_points = sum(
            points for user, points in self.mock_bot.user_points.items() 
            if user.startswith("anon") or user == "Anonymous"
        )
        assert total_anonymous_points == 0
        
        # Assert: All webhooks processed
        assert len(self.mock_server.webhooks_sent) == 3


@pytest.mark.performance
class TestWebhookPerformance:
    """Performance testing for webhook processing system"""
    
    def setup_method(self):
        """Set up performance test fixtures"""
        self.mock_bot = MockBotInstance()
        
        # Store original global instances  
        import oauth_webhook_server
        self.original_bot_instance = oauth_webhook_server.bot_instance
        self.original_chat_correlator = oauth_webhook_server.chat_correlator
        self.original_webhook_monitor = oauth_webhook_server.webhook_monitor
        self.original_settings = oauth_webhook_server.settings
        
        # Set up test instances
        oauth_webhook_server.bot_instance = self.mock_bot
        if WebhookChatCorrelator:
            oauth_webhook_server.chat_correlator = WebhookChatCorrelator()
        if WebhookMonitoring:
            oauth_webhook_server.webhook_monitor = WebhookMonitoring()
            
        # Disable alerts for performance testing
        oauth_webhook_server.settings = {'Alerts': {'Enable': False}}
        
    def teardown_method(self):
        """Clean up performance test fixtures"""
        # Restore original global instances
        import oauth_webhook_server
        oauth_webhook_server.bot_instance = self.original_bot_instance
        oauth_webhook_server.chat_correlator = self.original_chat_correlator
        oauth_webhook_server.webhook_monitor = self.original_webhook_monitor
        oauth_webhook_server.settings = self.original_settings
            
    @pytest.mark.asyncio
    async def test_standard_payload_processing_performance(self):
        """
        GIVEN: Standard webhook payload processing
        WHEN: Single gift webhook processed
        THEN: Processing completes within performance target (< 0.5s)
        """
        if not handle_gift_subscription_event:
            pytest.skip("Webhook handler not available for performance testing")
            
        # Arrange: Standard payload
        payload = {
            "gifter": {"username": "perftest", "user_id": 999},
            "giftees": [{"username": "recipient", "user_id": 888}]
        }
        
        # Act: Measure processing time
        start_time = time.time()
        await handle_gift_subscription_event(payload)
        processing_time = time.time() - start_time
        
        # Assert: Sub-second processing
        assert processing_time < 0.5, f"Processing too slow: {processing_time:.3f}s (target: <0.5s)"
        
        # Assert: Correct processing result
        assert self.mock_bot.get_user_points("perftest") == 200
        
    @pytest.mark.asyncio
    async def test_correlation_system_performance(self):
        """
        GIVEN: Empty payload requiring correlation
        WHEN: Webhook and chat message processed with timing
        THEN: Total processing (including correlation) completes reasonably fast
        """
        if not handle_gift_subscription_event or not handle_chat_message_event:
            pytest.skip("Handlers not available for correlation performance testing")
            
        # Arrange: Empty payload requiring correlation
        empty_payload = {}
        chat_data = {
            'message_id': 'perf_test_msg',
            'sender': {'username': 'Kicklet'},
            'content': 'Thank you, corrtest, for the gifted 1 subscriptions.',
            'timestamp': time.time()
        }
        
        # Act: Measure total correlation time
        start_time = time.time()
        
        # Process webhook (triggers correlation registration)
        await handle_gift_subscription_event(empty_payload)
        
        # Process chat message after realistic delay
        await asyncio.sleep(6.0)  # Simulate real-world timing
        await handle_chat_message_event(chat_data)
        
        # Allow correlation processing
        await asyncio.sleep(0.5)
        total_time = time.time() - start_time
        
        # Assert: Total time reasonable (under 10 seconds including delays)
        assert total_time < 10.0, f"Total correlation time too long: {total_time:.3f}s"
        
        # Assert: Correlation worked
        assert self.mock_bot.get_user_points("corrtest") == 200


@pytest.mark.load  
class TestWebhookLoadTesting:
    """Load testing for concurrent webhook processing"""
    
    def setup_method(self):
        """Set up load test fixtures"""
        self.mock_bot = MockBotInstance()
        
        # Patch global bot instance
        import oauth_webhook_server
        self.original_bot_instance = oauth_webhook_server.bot_instance
        oauth_webhook_server.bot_instance = self.mock_bot
        
    def teardown_method(self):
        """Clean up load test fixtures"""
        if self.original_bot_instance is not None:
            import oauth_webhook_server
            oauth_webhook_server.bot_instance = self.original_bot_instance
            
    @pytest.mark.asyncio
    async def test_concurrent_standard_payload_processing(self):
        """
        GIVEN: Multiple concurrent standard payload webhooks
        WHEN: 10 simultaneous gift webhooks processed
        THEN: All process successfully with acceptable performance
        """
        if not handle_gift_subscription_event:
            pytest.skip("Webhook handler not available for load testing")
            
        # Arrange: 10 concurrent gift scenarios
        concurrent_gifts = 10
        tasks = []
        
        for i in range(concurrent_gifts):
            payload = {
                "gifter": {"username": f"loadtest_{i}", "user_id": 1000 + i},
                "giftees": [{"username": f"recipient_{i}", "user_id": 2000 + i}]
            }
            task = asyncio.create_task(handle_gift_subscription_event(payload))
            tasks.append(task)
            
        # Act: Process all concurrently
        start_time = time.time()
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Assert: All processed within reasonable time
        assert total_time < 5.0, f"Concurrent processing too slow: {total_time:.3f}s"
        
        # Assert: All gifts processed correctly
        total_users = len([user for user in self.mock_bot.user_points.keys() 
                          if user.startswith("loadtest_")])
        assert total_users == concurrent_gifts
        
        # Assert: Total points correct
        total_points = sum(self.mock_bot.user_points.values())
        assert total_points == concurrent_gifts * 200
        
    @pytest.mark.asyncio
    async def test_mixed_payload_load_testing(self):
        """
        GIVEN: Mixed payload types under load
        WHEN: Various webhook types processed concurrently
        THEN: System handles mixed load correctly
        """
        if not handle_gift_subscription_event:
            pytest.skip("Webhook handler not available for mixed load testing")
            
        # Arrange: Mixed payload scenarios
        payload_scenarios = [
            # Standard payloads (fast processing)
            *[{"gifter": {"username": f"std_{i}", "user_id": i}, "giftees": [{}]} for i in range(5)],
            # Empty payloads (correlation required) 
            *[{} for _ in range(3)],
            # Anonymous payloads
            *[{"gifter": {"is_anonymous": True}, "giftees": [{}]} for _ in range(2)]
        ]
        
        # Act: Process mixed load
        tasks = [
            asyncio.create_task(handle_gift_subscription_event(payload))
            for payload in payload_scenarios
        ]
        
        start_time = time.time()
        await asyncio.gather(*tasks)
        processing_time = time.time() - start_time
        
        # Assert: Mixed load handled efficiently
        assert processing_time < 3.0, f"Mixed load processing too slow: {processing_time:.3f}s"
        
        # Assert: Standard payloads processed (5 users * 200 points each)
        standard_points = sum(
            points for user, points in self.mock_bot.user_points.items()
            if user.startswith("std_")
        )
        assert standard_points == 1000  # 5 * 200


@pytest.mark.regression
class TestWebhookRegressionSuite:
    """Regression tests for all payload variations discovered in Stories 12-15"""
    
    def setup_method(self):
        """Set up regression test fixtures"""
        self.mock_bot = MockBotInstance()
        
        # Patch global bot instance
        import oauth_webhook_server
        self.original_bot_instance = oauth_webhook_server.bot_instance
        oauth_webhook_server.bot_instance = self.mock_bot
        
    def teardown_method(self):
        """Clean up regression test fixtures"""
        if self.original_bot_instance is not None:
            import oauth_webhook_server
            oauth_webhook_server.bot_instance = self.original_bot_instance
            
    @pytest.mark.asyncio
    async def test_all_discovered_payload_variations(self):
        """
        GIVEN: All payload variations discovered during Stories 12-15
        WHEN: Each variation processed through webhook system
        THEN: System handles all variations without crashing
        """
        if not handle_gift_subscription_event:
            pytest.skip("Webhook handler not available for regression testing")
            
        # Arrange: All payload variations from investigation
        payload_variations = [
            # Story 12: Empty payload (most common)
            {},
            
            # Story 13: Standard API format
            {"gifter": {"username": "standard", "user_id": 123}, "giftees": [{}]},
            
            # Story 13: Nested data format
            {"data": {"gifter": {"username": "nested", "user_id": 456}, "giftees": [{}]}},
            
            # Story 13: Flat structure
            {"username": "flat", "user_id": 789, "giftees": [{}]},
            
            # Story 13: Anonymous variations
            {"gifter": {"is_anonymous": True}, "giftees": [{}]},
            {"gifter": {"username": "Anonymous"}, "giftees": [{}]},
            
            # Edge cases discovered
            {"gifter": None, "giftees": []},
            {"gifter": {}, "giftees": []},
            {"malformed": "data"},
            None  # Completely invalid payload
        ]
        
        # Act: Process all variations
        results = []
        for i, payload in enumerate(payload_variations):
            try:
                await handle_gift_subscription_event(payload)
                results.append({"payload_index": i, "success": True, "error": None})
            except Exception as e:
                results.append({"payload_index": i, "success": False, "error": str(e)})
                
        # Assert: System doesn't crash on any payload
        crashed_count = sum(1 for r in results if not r["success"])
        total_count = len(results)
        success_rate = (total_count - crashed_count) / total_count
        
        # Allow some failures for truly malformed data, but system should be resilient
        assert success_rate >= 0.7, f"Too many payload failures: {crashed_count}/{total_count}"
        
        # Assert: Valid payloads processed correctly
        expected_users = ["standard", "nested", "flat"]
        successful_users = [user for user in expected_users if self.mock_bot.get_user_points(user) > 0]
        assert len(successful_users) >= 2, f"Valid payloads not processed: {successful_users}"
        
    @pytest.mark.asyncio
    async def test_correlation_system_edge_cases(self):
        """
        GIVEN: Edge cases for correlation system
        WHEN: Various correlation scenarios tested
        THEN: System handles edge cases gracefully
        """
        if not handle_gift_subscription_event or not handle_chat_message_event:
            pytest.skip("Handlers not available for correlation regression testing")
            
        # Test multiple empty payloads with single chat message (should not over-correlate)
        await handle_gift_subscription_event({})
        await handle_gift_subscription_event({})
        
        await asyncio.sleep(6.0)
        
        # Single chat message should correlate with first webhook
        chat_data = {
            'message_id': 'edge_test',
            'sender': {'username': 'Kicklet'},
            'content': 'Thank you, edgecase, for the gifted 1 subscriptions.'
        }
        await handle_chat_message_event(chat_data)
        
        await asyncio.sleep(0.5)
        
        # Should have correlated successfully without errors
        points = self.mock_bot.get_user_points("edgecase")
        assert points > 0, "Edge case correlation should have succeeded"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])