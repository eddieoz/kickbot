"""
Test suite to expose the authentication integration issue between webhook and chat systems
This test demonstrates the problem where OAuth webhooks try to use legacy chat authentication
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


class TestAuthenticationIntegrationIssue:
    """Test authentication integration issues between OAuth webhooks and legacy chat system"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_alert_function = AsyncMock()
        
    @pytest.mark.asyncio
    async def test_oauth_webhook_with_legacy_chat_authentication_failure(self):
        """
        Test that demonstrates the authentication mismatch issue
        
        Given: An OAuth-authenticated webhook bot
        And: A gift subscription event is received
        When: The bot tries to send a chat message using legacy authentication
        Then: The chat message should fail due to missing XSRF token and auth_token
        And: This should be handled gracefully
        """
        # Create a more realistic bot instance that lacks legacy auth components
        class OAuthOnlyBot:
            def __init__(self):
                self.logger = MagicMock()
                self.client = None  # OAuth bots don't have a client with XSRF tokens
                self.chatroom_id = None  # OAuth bots may not have this set up
                
            async def _handle_gifted_subscriptions(self, gifter: str, amount: int) -> None:
                """Simulate the actual method that would fail with OAuth-only authentication"""
                try:
                    # This simulates the current implementation that tries to use legacy auth
                    from kickbot.kick_helper import send_message_in_chat
                    from kickbot.kick_bot import settings
                    
                    if 'GiftBlokitos' in settings and settings['GiftBlokitos'] != 0:
                        blokitos = amount * settings['GiftBlokitos']
                        message = f'!subgift_add {gifter} {blokitos}'
                        
                        # This will fail because self.client is None (no legacy auth)
                        r = send_message_in_chat(self, message)
                        
                        if r.status_code != 200:
                            self.logger.error(f"Error sending message for gift subs: {r.status_code} - {r.text}")
                        else:
                            self.logger.info(f"Added {blokitos} to user {gifter} for {amount} sub_gifts")
                except Exception as e:
                    self.logger.error(f"Error handling gifted subscriptions: {e}", exc_info=True)
                    raise  # Re-raise to see the actual error
        
        oauth_only_bot = OAuthOnlyBot()
        
        # Mock settings
        test_settings = {'GiftBlokitos': 200}
        
        with patch('kickbot.kick_bot.settings', test_settings):
            with pytest.raises(AttributeError) as exc_info:
                # When: We try to send a gift subscription message
                await oauth_only_bot._handle_gifted_subscriptions("testuser", 3)
        
        # Then: Should fail due to missing client authentication attributes
        assert "client" in str(exc_info.value) or "NoneType" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_webhook_integration_with_oauth_chat_solution(self):
        """
        Test the proposed solution using OAuth-compatible chat messaging
        
        This test shows what the fix should look like
        """
        class OAuthCompatibleBot:
            def __init__(self):
                self.logger = MagicMock()
                self.auth_manager = MagicMock()  # OAuth auth manager
                self.chatroom_id = 12345
                
            async def send_chat_message_oauth(self, message: str) -> bool:
                """OAuth-compatible chat message sending"""
                try:
                    # This would use OAuth authentication instead of legacy auth
                    from kickbot.kick_helper import send_message_in_chat_async
                    result = await send_message_in_chat_async(self, message)
                    return result.get('success', False)
                except Exception as e:
                    self.logger.error(f"Error sending OAuth chat message: {e}")
                    return False
                
            async def _handle_gifted_subscriptions_oauth_compatible(self, gifter: str, amount: int) -> None:
                """OAuth-compatible version of _handle_gifted_subscriptions"""
                if gifter == "Anonymous":
                    self.logger.info(f"Anonymous gifter sent {amount} subscriptions - no points awarded")
                    return
                    
                try:
                    from kickbot.kick_bot import settings
                    if 'GiftBlokitos' in settings and settings['GiftBlokitos'] != 0:
                        blokitos = amount * settings['GiftBlokitos']
                        message = f'!subgift_add {gifter} {blokitos}'
                        
                        # Use OAuth-compatible chat messaging
                        success = await self.send_chat_message_oauth(message)
                        
                        if success:
                            self.logger.info(f"Added {blokitos} to user {gifter} for {amount} sub_gifts")
                        else:
                            self.logger.error(f"Failed to send gift subscription message for {gifter}")
                except Exception as e:
                    self.logger.error(f"Error handling gifted subscriptions: {e}", exc_info=True)
        
        oauth_bot = OAuthCompatibleBot()
        
        # Mock the OAuth chat function to succeed
        with patch('kickbot.kick_helper.send_message_in_chat_async', return_value={'success': True}):
            with patch('kickbot.kick_bot.settings', {'GiftBlokitos': 150}):
                # When: We send a gift subscription message with OAuth-compatible method
                await oauth_bot._handle_gifted_subscriptions_oauth_compatible("oauthuser", 2)
                
                # Then: Should succeed without authentication errors
                oauth_bot.logger.info.assert_called_with("Added 300 to user oauthuser for 2 sub_gifts")

    @pytest.mark.asyncio
    async def test_current_webhook_integration_with_realistic_bot(self):
        """
        Test the current webhook integration with a bot that has both OAuth and legacy auth
        
        This simulates the actual production scenario
        """
        # Create a bot that has both OAuth and legacy components (like in production)
        class HybridBot:
            def __init__(self):
                self.logger = MagicMock()
                # OAuth components
                self.auth_manager = MagicMock()
                # Legacy components (may be None or partially initialized)
                self.client = MagicMock()
                self.client.xsrf = "mock_xsrf_token"
                self.client.auth_token = "mock_auth_token"
                self.client.cookies = {}
                self.client.scraper = MagicMock()
                self.chatroom_id = 12345
                
            async def _handle_gifted_subscriptions(self, gifter: str, amount: int) -> None:
                """Current implementation that uses legacy chat API"""
                if gifter == "Anonymous":
                    self.logger.info(f"Anonymous gifter sent {amount} subscriptions - no points awarded")
                    return
                    
                try:
                    from kickbot.kick_helper import send_message_in_chat
                    from kickbot.kick_bot import settings
                    
                    if 'GiftBlokitos' in settings and settings['GiftBlokitos'] != 0:
                        blokitos = amount * settings['GiftBlokitos']
                        message = f'!subgift_add {gifter} {blokitos}'
                        r = send_message_in_chat(self, message)
                        if r.status_code != 200:
                            self.logger.error(f"Error sending message for gift subs: {r.status_code} - {r.text}")
                        else:
                            self.logger.info(f"Added {blokitos} to user {gifter} for {amount} sub_gifts")
                except Exception as e:
                    self.logger.error(f"Error handling gifted subscriptions: {e}", exc_info=True)
        
        hybrid_bot = HybridBot()
        
        # Mock successful response from legacy API
        mock_response = MagicMock()
        mock_response.status_code = 200
        hybrid_bot.client.scraper.post.return_value = mock_response
        
        # Set up webhook integration
        oauth_webhook_server.bot_instance = hybrid_bot
        
        # Mock settings
        with patch('kickbot.kick_bot.settings', {'GiftBlokitos': 175}):
            with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
                # When: A gift subscription webhook is processed
                event_data = {
                    "gifter": {
                        "username": "hybriduser",
                        "id": 54321
                    },
                    "quantity": 4
                }
                
                await oauth_webhook_server.handle_gift_subscription_event(event_data)
        
        # Then: The chat message should be sent successfully
        hybrid_bot.client.scraper.post.assert_called_once()
        call_args = hybrid_bot.client.scraper.post.call_args
        
        # Verify the correct message was sent
        json_payload = call_args[1]['json']
        assert json_payload['message'] == '!subgift_add hybriduser 700'
        assert json_payload['chatroom_id'] == 12345

    @pytest.mark.asyncio
    async def test_webhook_error_when_legacy_auth_fails(self):
        """
        Test webhook behavior when legacy authentication fails
        
        This simulates what happens in production when XSRF tokens expire
        """
        class FailingAuthBot:
            def __init__(self):
                self.logger = MagicMock()
                self.client = MagicMock()
                self.client.xsrf = "expired_xsrf_token"
                self.client.auth_token = "expired_auth_token"
                self.client.cookies = {}
                self.client.scraper = MagicMock()
                self.chatroom_id = 12345
                
            async def _handle_gifted_subscriptions(self, gifter: str, amount: int) -> None:
                """Simulate auth failure in current implementation"""
                try:
                    from kickbot.kick_helper import send_message_in_chat
                    from kickbot.kick_bot import settings
                    
                    if 'GiftBlokitos' in settings and settings['GiftBlokitos'] != 0:
                        blokitos = amount * settings['GiftBlokitos']
                        message = f'!subgift_add {gifter} {blokitos}'
                        r = send_message_in_chat(self, message)
                        if r.status_code != 200:
                            self.logger.error(f"Error sending message for gift subs: {r.status_code} - {r.text}")
                        else:
                            self.logger.info(f"Added {blokitos} to user {gifter} for {amount} sub_gifts")
                except Exception as e:
                    self.logger.error(f"Error handling gifted subscriptions: {e}", exc_info=True)
        
        failing_bot = FailingAuthBot()
        
        # Mock auth failure response (419 CSRF token mismatch)
        mock_response = MagicMock()
        mock_response.status_code = 419
        mock_response.text = "CSRF token mismatch"
        failing_bot.client.scraper.post.return_value = mock_response
        
        # Set up webhook integration
        oauth_webhook_server.bot_instance = failing_bot
        
        with patch('kickbot.kick_bot.settings', {'GiftBlokitos': 100}):
            with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
                # When: A gift subscription webhook is processed with failing auth
                event_data = {
                    "gifter": {
                        "username": "failinguser",
                        "id": 98765
                    },
                    "quantity": 1
                }
                
                await oauth_webhook_server.handle_gift_subscription_event(event_data)
        
        # Then: Error should be logged about message sending failure
        failing_bot.logger.error.assert_called_with("Error sending message for gift subs: 419 - CSRF token mismatch")
        
        # But alert should still be sent successfully
        self.mock_alert_function.assert_called_once()
        call_args = self.mock_alert_function.call_args[0]
        assert "failinguser" in call_args[2]

if __name__ == "__main__":
    pytest.main([__file__])