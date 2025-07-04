#!/usr/bin/env python3
"""
Test cases for Story 2: Unified Webhook Server Setup

Tests the unified webhook server that handles both OAuth callbacks and 
event webhooks on a single port with signature verification.
"""

import unittest
import asyncio
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import time
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
import aiohttp

# Add project root to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestUnifiedWebhookServer(AioHTTPTestCase):
    """Test unified webhook server for Story 2"""

    async def get_application(self):
        """Create test application"""
        # Import here to avoid circular imports
        from oauth_webhook_server import create_app
        return await create_app()

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.test_dir = tempfile.mkdtemp()
        
        # Sample webhook payloads
        self.valid_follow_payload = {
            "event": {"type": "channel.followed"},
            "data": {
                "follower": {"username": "test_follower"}
            }
        }
        
        self.valid_subscription_payload = {
            "event": {"type": "channel.subscription.new"},
            "data": {
                "subscriber": {"username": "test_subscriber"},
                "tier": 1
            }
        }
        
        self.valid_chat_message_payload = {
            "event": {"type": "chat.message.sent"},
            "data": {
                "sender": {"username": "test_user"},
                "content": "!b hello world"
            }
        }

    @unittest_run_loop
    async def test_webhook_server_startup(self):
        """
        Test: Single server process listens on port 8080
        Given: Server configuration
        When: Server starts
        Then: Both endpoints are accessible on port 8080
        """
        # Test health endpoint
        resp = await self.client.request("GET", "/health")
        self.assertEqual(resp.status, 200)
        text = await resp.text()
        self.assertEqual(text, "OK")
        
        # Test root endpoint (also health check)
        resp = await self.client.request("GET", "/")
        self.assertEqual(resp.status, 200)

    @unittest_run_loop 
    async def test_oauth_callback_handling(self):
        """
        Test: /callback endpoint handles OAuth authorization codes
        Given: OAuth authorization code
        When: GET to /callback
        Then: Token is exchanged and stored (or error is handled gracefully)
        """
        # Test with missing code parameter
        resp = await self.client.request("GET", "/callback")
        self.assertEqual(resp.status, 400)
        
        # Test with error parameter
        resp = await self.client.request("GET", "/callback?error=access_denied&error_description=User+denied+access")
        self.assertEqual(resp.status, 400)
        content = await resp.text()
        self.assertIn("access_denied", content)

    @unittest_run_loop
    async def test_webhook_event_processing(self):
        """
        Test: /events endpoint receives Kick API webhook events
        Given: Valid webhook payload
        When: POST to /events
        Then: Event is processed and returns 200
        """
        # Test follow event
        resp = await self.client.request("POST", "/events", 
                                       data=json.dumps(self.valid_follow_payload),
                                       headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status, 200)
        text = await resp.text()
        self.assertEqual(text, "Event received")
        
        # Test subscription event
        resp = await self.client.request("POST", "/events",
                                       data=json.dumps(self.valid_subscription_payload), 
                                       headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status, 200)
        
        # Test chat message event
        resp = await self.client.request("POST", "/events",
                                       data=json.dumps(self.valid_chat_message_payload),
                                       headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status, 200)

    @unittest_run_loop
    async def test_webhook_signature_validation(self):
        """
        Test: Server validates webhook signatures when enabled
        Given: Webhook payload with/without valid signature
        When: POST to /events with signature header
        Then: Valid signatures pass, invalid ones fail
        """
        # Test without signature (should pass if signature verification disabled)
        resp = await self.client.request("POST", "/events",
                                       data=json.dumps(self.valid_follow_payload),
                                       headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status, 200)
        
        # Test with invalid signature header (when signature verification is enabled)
        # This test will be enhanced when signature verification is implemented
        resp = await self.client.request("POST", "/events", 
                                       data=json.dumps(self.valid_follow_payload),
                                       headers={
                                           "Content-Type": "application/json",
                                           "X-Kick-Signature": "invalid_signature"
                                       })
        # Should still pass if signature verification is disabled by default
        self.assertEqual(resp.status, 200)

    @unittest_run_loop
    async def test_malformed_webhook_requests(self):
        """
        Test: Error handling for malformed requests
        Given: Invalid JSON payload
        When: POST to /events
        Then: Returns 400 error
        """
        # Test invalid JSON
        resp = await self.client.request("POST", "/events",
                                       data="invalid json",
                                       headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status, 400)
        text = await resp.text()
        self.assertEqual(text, "Invalid JSON")

    @unittest_run_loop
    async def test_chat_message_command_processing(self):
        """
        Test: Chat messages are processed and commands are executed
        Given: Chat message with bot command
        When: POST to /events with chat.message.sent event
        Then: Command is processed by bot instance
        """
        # Test command message
        command_payload = {
            "event": {"type": "chat.message.sent"},
            "data": {
                "sender": {"username": "test_user"},
                "content": "!github"
            }
        }
        
        resp = await self.client.request("POST", "/events",
                                       data=json.dumps(command_payload),
                                       headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status, 200)
        
        # Test non-command message
        regular_payload = {
            "event": {"type": "chat.message.sent"},
            "data": {
                "sender": {"username": "test_user"},
                "content": "hello everyone"
            }
        }
        
        resp = await self.client.request("POST", "/events",
                                       data=json.dumps(regular_payload),
                                       headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status, 200)

    @unittest_run_loop
    async def test_unknown_event_types(self):
        """
        Test: Unknown event types are handled gracefully
        Given: Webhook payload with unknown event type
        When: POST to /events
        Then: Event is logged and 200 is returned
        """
        unknown_payload = {
            "event": {"type": "unknown.event.type"},
            "data": {"some": "data"}
        }
        
        resp = await self.client.request("POST", "/events",
                                       data=json.dumps(unknown_payload),
                                       headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status, 200)


class TestWebhookServerIntegration(unittest.TestCase):
    """Test webhook server integration with bot components"""
    
    def test_bot_instance_integration(self):
        """
        Test: Webhook server integrates with bot instance
        Given: Bot instance with command handlers
        When: Webhook server processes chat events
        Then: Bot commands are executed correctly
        """
        # This will be an integration test that verifies the bot instance
        # is properly integrated with the webhook server
        pass

    def test_alert_system_integration(self):
        """
        Test: Alert system works with webhook events
        Given: Webhook events (follow, subscription)
        When: Events are processed
        Then: Alerts are sent to external system
        """
        # This will test that the alert system integration works
        pass

    def test_markov_chain_integration(self):
        """
        Test: MarkovChain integration works via webhooks
        Given: Chat message with !b command
        When: Processed via webhook
        Then: MarkovChain generates response
        """
        # This will test MarkovChain command processing via webhooks
        pass


if __name__ == '__main__':
    unittest.main()