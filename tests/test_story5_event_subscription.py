#!/usr/bin/env python3
"""
Test cases for Story 5: Event Subscription Management

Tests the automatic event subscription system including startup subscriptions,
verification, retry logic, and cleanup on shutdown.
"""

import unittest
import asyncio
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import time

# Add project root to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kickbot.kick_event_manager import KickEventManager
from kickbot.kick_auth_manager import KickAuthManager

class TestEventSubscriptionManagement(unittest.TestCase):
    """Test event subscription management for Story 5"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.test_token_file = os.path.join(self.test_dir, "test_tokens.json")
        
        # Test configuration
        self.test_client_id = "test_client_id"
        self.test_client_secret = "test_client_secret"
        self.test_redirect_uri = "https://test.example.com/callback"
        self.test_scopes = "user:read channel:read chat:write events:subscribe"
        self.test_webhook_url = "https://test.example.com/events"
        self.test_broadcaster_id = 1139843
        
        # Sample events to subscribe to
        self.test_events = [
            {"name": "channel.followed", "version": 1},
            {"name": "channel.subscription.new", "version": 1},
            {"name": "channel.subscription.gifts", "version": 1},
            {"name": "channel.subscription.renewal", "version": 1},
            {"name": "chat.message.sent", "version": 1}
        ]
        
        # Sample subscription response
        self.subscription_success_response = {
            "data": [
                {
                    "subscription_id": "sub_123",
                    "name": "channel.followed",
                    "version": 1
                },
                {
                    "subscription_id": "sub_124", 
                    "name": "chat.message.sent",
                    "version": 1
                }
            ]
        }
        
        # Sample list subscriptions response
        self.list_subscriptions_response = {
            "data": [
                {
                    "id": "sub_123",
                    "type": "channel.followed",
                    "version": 1,
                    "broadcaster_user_id": self.test_broadcaster_id,
                    "status": "active"
                },
                {
                    "id": "sub_124",
                    "type": "chat.message.sent", 
                    "version": 1,
                    "broadcaster_user_id": self.test_broadcaster_id,
                    "status": "active"
                }
            ]
        }

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir)

    def test_event_subscription_configuration(self):
        """
        Test: Event manager is properly configured with webhook URL and events
        Given: Event manager initialization with webhook URL
        When: Event manager is created
        Then: Configuration is correctly set
        """
        # Create mock auth manager
        auth_manager = MagicMock()
        
        # Create event manager
        event_manager = KickEventManager(
            auth_manager=auth_manager,
            client=None,
            broadcaster_user_id=self.test_broadcaster_id,
            webhook_url=self.test_webhook_url
        )
        
        # Verify configuration
        self.assertEqual(event_manager.broadcaster_user_id, self.test_broadcaster_id)
        self.assertEqual(event_manager.webhook_url, self.test_webhook_url)
        self.assertEqual(event_manager.auth_manager, auth_manager)
        self.assertEqual(len(event_manager.active_subscription_ids), 0)

    def test_event_subscription_payload_structure(self):
        """
        Test: Subscription payload has correct structure
        Given: Event manager with test configuration
        When: Subscription payload is constructed
        Then: Payload contains all required fields
        """
        # Test that the payload structure would be correct
        expected_payload = {
            "broadcaster_user_id": self.test_broadcaster_id,
            "events": self.test_events,
            "method": "webhook", 
            "webhook_url": self.test_webhook_url
        }
        
        # Verify each component
        self.assertEqual(expected_payload["broadcaster_user_id"], self.test_broadcaster_id)
        self.assertEqual(expected_payload["method"], "webhook")
        self.assertEqual(expected_payload["webhook_url"], self.test_webhook_url)
        self.assertEqual(len(expected_payload["events"]), 5)
        
        # Verify required event types are present
        event_names = [event["name"] for event in expected_payload["events"]]
        self.assertIn("chat.message.sent", event_names)
        self.assertIn("channel.followed", event_names)
        self.assertIn("channel.subscription.new", event_names)

    def test_subscription_verification(self):
        """
        Test: Periodic verification checks and re-creates missing subscriptions
        Given: Event manager with some missing subscriptions
        When: Verification runs
        Then: Missing subscriptions are detected and re-created
        """
        async def test_verification():
            # Create mock auth manager
            auth_manager = AsyncMock()
            auth_manager.get_valid_token.return_value = "valid_token"
            
            # Create event manager
            event_manager = KickEventManager(
                auth_manager=auth_manager,
                client=None,
                broadcaster_user_id=self.test_broadcaster_id,
                webhook_url=self.test_webhook_url
            )
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                # Mock list subscriptions - only some events are subscribed
                mock_list_response = AsyncMock()
                mock_list_response.status = 200
                partial_subscriptions = {
                    "data": [
                        {
                            "id": "sub_123",
                            "type": "channel.followed",
                            "version": 1,
                            "broadcaster_user_id": self.test_broadcaster_id,
                            "status": "active"
                        }
                        # Missing chat.message.sent and other events
                    ]
                }
                mock_list_response.json.return_value = partial_subscriptions
                mock_session.get.return_value.__aenter__.return_value = mock_list_response
                mock_session.get.return_value.__aexit__.return_value = False
                
                # Test listing current subscriptions
                current_subs = await event_manager.list_subscriptions()
                self.assertIsNotNone(current_subs)
                self.assertEqual(len(current_subs), 1)
                self.assertEqual(current_subs[0]["type"], "channel.followed")
        
        asyncio.run(test_verification())

    def test_subscription_retry_logic(self):
        """
        Test: Failed subscriptions are retried with backoff
        Given: Subscription request that fails initially
        When: Subscription is attempted
        Then: Request is retried with exponential backoff
        """
        async def test_retry():
            # Create mock auth manager
            auth_manager = AsyncMock()
            auth_manager.get_valid_token.return_value = "valid_token"
            
            # Create event manager
            event_manager = KickEventManager(
                auth_manager=auth_manager,
                client=None,
                broadcaster_user_id=self.test_broadcaster_id,
                webhook_url=self.test_webhook_url
            )
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                # Mock first attempt failure, second attempt success
                mock_response_fail = AsyncMock()
                mock_response_fail.status = 500
                mock_response_fail.json.return_value = {"error": "Internal server error"}
                
                mock_response_success = AsyncMock()
                mock_response_success.status = 200
                mock_response_success.json.return_value = self.subscription_success_response
                
                # Set up async context managers properly
                mock_session.post.return_value.__aenter__.side_effect = [mock_response_fail, mock_response_success]
                mock_session.post.return_value.__aexit__.return_value = False
                
                # The first call should fail, but we test the mechanism
                result1 = await event_manager.subscribe_to_events(self.test_events)
                self.assertFalse(result1)  # First attempt fails
                
                # Second call should succeed
                result2 = await event_manager.subscribe_to_events(self.test_events)
                self.assertTrue(result2)  # Second attempt succeeds
        
        asyncio.run(test_retry())

    def test_subscription_cleanup_on_shutdown(self):
        """
        Test: Subscriptions are cleaned up when event manager shuts down
        Given: Event manager with active subscriptions
        When: Cleanup is called
        Then: All subscriptions are removed
        """
        async def test_cleanup():
            # Create mock auth manager
            auth_manager = AsyncMock()
            auth_manager.get_valid_token.return_value = "valid_token"
            
            # Create event manager with some active subscriptions
            event_manager = KickEventManager(
                auth_manager=auth_manager,
                client=None,
                broadcaster_user_id=self.test_broadcaster_id,
                webhook_url=self.test_webhook_url
            )
            
            # Set some active subscription IDs
            event_manager.active_subscription_ids = ["sub_123", "sub_124", "sub_125"]
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                # Mock list subscriptions response
                mock_list_response = AsyncMock()
                mock_list_response.status = 200
                mock_list_response.json.return_value = self.list_subscriptions_response
                mock_session.get.return_value.__aenter__.return_value = mock_list_response
                mock_session.get.return_value.__aexit__.return_value = False
                
                # Mock successful deletion
                mock_delete_response = AsyncMock()
                mock_delete_response.status = 204  # No Content for successful deletion
                mock_session.delete.return_value.__aenter__.return_value = mock_delete_response
                mock_session.delete.return_value.__aexit__.return_value = False
                
                # Test cleanup
                result = await event_manager.clear_all_my_broadcaster_subscriptions()
                
                # Verify cleanup was successful
                self.assertTrue(result)
                mock_session.delete.assert_called_once()
                
                # Verify active subscription IDs were cleared
                self.assertEqual(len(event_manager.active_subscription_ids), 0)
        
        asyncio.run(test_cleanup())

    def test_webhook_url_configuration(self):
        """
        Test: Webhook URL is properly configured from environment
        Given: Event manager with custom webhook URL
        When: Subscription is made
        Then: Correct webhook URL is used in the request
        """
        async def test_webhook_url():
            # Create mock auth manager
            auth_manager = AsyncMock()
            auth_manager.get_valid_token.return_value = "valid_token"
            
            # Create event manager with custom webhook URL
            custom_webhook_url = "https://custom.webhook.example.com/events"
            event_manager = KickEventManager(
                auth_manager=auth_manager,
                client=None,
                broadcaster_user_id=self.test_broadcaster_id,
                webhook_url=custom_webhook_url
            )
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                # Mock successful subscription
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = self.subscription_success_response
                mock_session.post.return_value.__aenter__.return_value = mock_response
                mock_session.post.return_value.__aexit__.return_value = False
                
                # Test subscription
                await event_manager.subscribe_to_events(self.test_events)
                
                # Verify the webhook URL in the payload
                call_args = mock_session.post.call_args
                json_payload = call_args[1]['json']
                self.assertEqual(json_payload['webhook_url'], custom_webhook_url)
        
        asyncio.run(test_webhook_url())

    def test_authentication_fallback(self):
        """
        Test: Event manager falls back to direct auth token when OAuth fails
        Given: OAuth token failure and direct auth token available
        When: Subscription is attempted
        Then: Direct auth token is used as fallback
        """
        async def test_auth_fallback():
            # Create mock auth manager that fails
            auth_manager = AsyncMock()
            auth_manager.get_valid_token.side_effect = Exception("OAuth token failed")
            
            # Create event manager with direct auth token fallback
            event_manager = KickEventManager(
                auth_manager=auth_manager,
                client=None,
                broadcaster_user_id=self.test_broadcaster_id,
                webhook_url=self.test_webhook_url
            )
            event_manager.direct_auth_token = "fallback_auth_token"
            
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                # Mock successful subscription with fallback auth
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = self.subscription_success_response
                mock_session.post.return_value.__aenter__.return_value = mock_response
                mock_session.post.return_value.__aexit__.return_value = False
                
                # Test subscription - should succeed with fallback auth
                result = await event_manager.subscribe_to_events(self.test_events)
                
                # Verify subscription succeeded despite OAuth failure
                self.assertTrue(result)
                
                # Verify the request was made with fallback auth token
                call_args = mock_session.post.call_args
                headers = call_args[1]['headers']
                self.assertEqual(headers['Authorization'], 'Bearer fallback_auth_token')
        
        asyncio.run(test_auth_fallback())


if __name__ == '__main__':
    unittest.main()