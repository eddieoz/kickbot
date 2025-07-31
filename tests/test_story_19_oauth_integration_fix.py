"""
Test suite for Story 19 OAuth Integration Fix
Tests the updated _handle_gifted_subscriptions method with OAuth-compatible chat messaging
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kickbot.kick_bot import KickBot


class TestStory19OAuthIntegrationFix:
    """Test the OAuth-compatible gift subscription integration fix"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_settings = {'GiftBlokitos': 200}

    @pytest.mark.asyncio
    async def test_oauth_bot_uses_oauth_chat_method(self):
        """
        Test that OAuth-enabled bots use the OAuth chat method
        
        Given: A bot with OAuth authentication manager
        When: _handle_gifted_subscriptions is called
        Then: OAuth-compatible chat messaging should be used
        """
        # Create a bot instance with OAuth components
        bot = KickBot.__new__(KickBot)  # Create without __init__
        bot.logger = MagicMock()
        bot.auth_manager = MagicMock()  # OAuth auth manager present
        
        # Mock the OAuth chat function
        with patch('kickbot.kick_helper.send_message_in_chat_async', new=AsyncMock()) as mock_oauth_chat:
            with patch('kickbot.kick_bot.settings', self.mock_settings):
                # When: Gift subscription is processed
                await bot._handle_gifted_subscriptions("oauthuser", 3)
                
                # Then: OAuth chat method should be called
                mock_oauth_chat.assert_called_once_with(bot, "!subgift_add oauthuser 600")
                
                # And success should be logged
                bot.logger.info.assert_called_with("Added 600 to user oauthuser for 3 sub_gifts")

    @pytest.mark.asyncio
    async def test_http_session_bot_uses_oauth_chat_method(self):
        """
        Test that bots with http_session use the OAuth chat method
        
        Given: A bot with http_session (but no auth_manager)
        When: _handle_gifted_subscriptions is called
        Then: OAuth-compatible chat messaging should be used
        """
        # Create a bot instance with http_session
        bot = KickBot.__new__(KickBot)
        bot.logger = MagicMock()
        bot.http_session = MagicMock()  # HTTP session for async requests
        # No auth_manager
        
        with patch('kickbot.kick_helper.send_message_in_chat_async', new=AsyncMock()) as mock_oauth_chat:
            with patch('kickbot.kick_bot.settings', self.mock_settings):
                # When: Gift subscription is processed
                await bot._handle_gifted_subscriptions("sessionuser", 2)
                
                # Then: OAuth chat method should be called
                mock_oauth_chat.assert_called_once_with(bot, "!subgift_add sessionuser 400")
                
                # And success should be logged
                bot.logger.info.assert_called_with("Added 400 to user sessionuser for 2 sub_gifts")

    @pytest.mark.asyncio
    async def test_legacy_bot_uses_legacy_chat_method(self):
        """
        Test that legacy bots fall back to legacy chat method
        
        Given: A bot with only legacy client authentication
        When: _handle_gifted_subscriptions is called
        Then: Legacy chat messaging should be used
        """
        # Create a bot instance with legacy components only
        bot = KickBot.__new__(KickBot)
        bot.logger = MagicMock()
        bot.client = MagicMock()
        bot.client.xsrf = "legacy_xsrf"
        bot.chatroom_id = 12345
        # No auth_manager or http_session
        
        # Mock successful legacy response
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('kickbot.kick_bot.send_message_in_chat', return_value=mock_response) as mock_legacy_chat:
            with patch('kickbot.kick_bot.settings', self.mock_settings):
                # When: Gift subscription is processed
                await bot._handle_gifted_subscriptions("legacyuser", 1)
                
                # Then: Legacy chat method should be called
                mock_legacy_chat.assert_called_once_with(bot, "!subgift_add legacyuser 200")
                
                # And success should be logged
                bot.logger.info.assert_called_with("Added 200 to user legacyuser for 1 sub_gifts")

    @pytest.mark.asyncio
    async def test_oauth_chat_method_failure_handling(self):
        """
        Test error handling when OAuth chat method fails
        
        Given: A bot with OAuth authentication
        When: OAuth chat messaging fails
        Then: Error should be logged and method should return gracefully
        """
        bot = KickBot.__new__(KickBot)
        bot.logger = MagicMock()
        bot.auth_manager = MagicMock()
        
        # Mock OAuth chat function to raise exception
        with patch('kickbot.kick_helper.send_message_in_chat_async', side_effect=Exception("OAuth token expired")):
            with patch('kickbot.kick_bot.settings', self.mock_settings):
                # When: Gift subscription is processed
                await bot._handle_gifted_subscriptions("failuser", 2)
                
                # Then: Error should be logged
                bot.logger.error.assert_called()
                error_calls = [call for call in bot.logger.error.call_args_list if "Failed to send gift subscription message" in str(call)]
                assert len(error_calls) > 0

    @pytest.mark.asyncio
    async def test_legacy_chat_method_failure_handling(self):
        """
        Test error handling when legacy chat method fails
        
        Given: A bot with legacy authentication
        When: Legacy chat messaging fails (e.g., 419 CSRF error)
        Then: Error should be logged appropriately
        """
        bot = KickBot.__new__(KickBot)
        bot.logger = MagicMock()
        bot.client = MagicMock()
        bot.client.xsrf = "expired_xsrf"
        
        # Mock failed legacy response
        mock_response = MagicMock()
        mock_response.status_code = 419
        mock_response.text = "CSRF token mismatch"
        
        with patch('kickbot.kick_bot.send_message_in_chat', return_value=mock_response):
            with patch('kickbot.kick_bot.settings', self.mock_settings):
                # When: Gift subscription is processed
                await bot._handle_gifted_subscriptions("csrffailuser", 1)
                
                # Then: Specific legacy error should be logged
                bot.logger.error.assert_called()
                error_calls = bot.logger.error.call_args_list
                csrf_error = any("Legacy chat API error: 419" in str(call) for call in error_calls)
                assert csrf_error, f"Expected CSRF error not found in: {error_calls}"

    @pytest.mark.asyncio
    async def test_no_authentication_method_available(self):
        """
        Test handling when no authentication method is available
        
        Given: A bot with no authentication methods
        When: _handle_gifted_subscriptions is called
        Then: Appropriate error should be logged
        """
        bot = KickBot.__new__(KickBot)
        bot.logger = MagicMock()
        # No auth_manager, no http_session, no client
        
        with patch('kickbot.kick_bot.settings', self.mock_settings):
            # When: Gift subscription is processed
            await bot._handle_gifted_subscriptions("noauthuser", 1)
            
            # Then: Error about no compatible method should be logged
            bot.logger.error.assert_called()
            error_calls = bot.logger.error.call_args_list
            no_method_error = any("No compatible chat messaging method available" in str(call) for call in error_calls)
            assert no_method_error, f"Expected 'no compatible method' error not found in: {error_calls}"

    @pytest.mark.asyncio
    async def test_anonymous_gifter_handling_unchanged(self):
        """
        Test that anonymous gifter handling remains unchanged
        
        Given: An anonymous gifter
        When: _handle_gifted_subscriptions is called
        Then: No chat message should be sent and appropriate log message should be created
        """
        bot = KickBot.__new__(KickBot)
        bot.logger = MagicMock()
        bot.auth_manager = MagicMock()
        
        # When: Anonymous gift subscription is processed
        await bot._handle_gifted_subscriptions("Anonymous", 5)
        
        # Then: Only info message should be logged, no chat sending attempted
        bot.logger.info.assert_called_once_with("Anonymous gifter sent 5 subscriptions - no points awarded")
        
        # Verify no error logs (indicating no chat send was attempted)
        assert not bot.logger.error.called

    @pytest.mark.asyncio
    async def test_zero_gift_blokitos_setting_unchanged(self):
        """
        Test that zero GiftBlokitos setting behavior remains unchanged
        
        Given: GiftBlokitos setting is 0
        When: _handle_gifted_subscriptions is called
        Then: No chat message should be sent
        """
        bot = KickBot.__new__(KickBot)
        bot.logger = MagicMock()
        bot.auth_manager = MagicMock()
        
        with patch('kickbot.kick_helper.send_message_in_chat_async', new=AsyncMock()) as mock_oauth_chat:
            with patch('kickbot.kick_bot.settings', {'GiftBlokitos': 0}):
                # When: Gift subscription is processed with zero setting
                await bot._handle_gifted_subscriptions("zerouser", 3)
                
                # Then: No chat message should be sent
                mock_oauth_chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_webhook_integration_with_fixed_method(self):
        """
        Test complete webhook integration with the fixed method
        
        This simulates the complete flow from webhook to points award
        """
        import oauth_webhook_server
        
        # Create OAuth-compatible bot
        bot = KickBot.__new__(KickBot)
        bot.logger = MagicMock()
        bot.auth_manager = MagicMock()
        
        # Set up webhook server with our bot
        oauth_webhook_server.bot_instance = bot
        
        with patch('kickbot.kick_helper.send_message_in_chat_async', new=AsyncMock()) as mock_oauth_chat:
            with patch('kickbot.kick_bot.settings', {'GiftBlokitos': 300}):
                with patch('oauth_webhook_server.send_alert', new=AsyncMock()):
                    # When: A gift subscription webhook is processed
                    event_data = {
                        "gifter": {
                            "username": "webhookuser",
                            "id": 11111
                        },
                        "quantity": 2
                    }
                    
                    await oauth_webhook_server.handle_gift_subscription_event(event_data)
        
        # Then: OAuth chat message should be sent with correct parameters
        mock_oauth_chat.assert_called_once_with(bot, "!subgift_add webhookuser 600")
        
        # And success should be logged
        success_logs = [call for call in bot.logger.info.call_args_list if "Added 600 to user webhookuser for 2 sub_gifts" in str(call)]
        assert len(success_logs) > 0

if __name__ == "__main__":
    pytest.main([__file__])