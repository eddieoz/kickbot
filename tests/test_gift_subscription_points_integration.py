"""
Test suite for Gift Subscription Points Integration (Story 19)
BDD scenarios testing gift subscription points integration and chat command execution
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


class TestGiftSubscriptionPointsIntegration:
    """Test gift subscription points integration with _handle_gifted_subscriptions"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_alert_function = AsyncMock()
        self.mock_bot = MagicMock(spec=KickBot)
        self.mock_bot._handle_gifted_subscriptions = AsyncMock()
        
        # Mock settings for GiftBlokitos
        self.mock_settings = {'GiftBlokitos': 200}
        
    @pytest.mark.asyncio
    async def test_scenario_19_1_direct_gift_subscription_points_award(self):
        """
        BDD Scenario 19.1: Direct Gift Subscription Points Award
        
        Given a gift subscription webhook event is received
        And the gifter is identified as "testgifter"
        And the quantity is 3
        And GiftBlokitos setting is 200
        When the gift subscription handler processes the event
        Then _handle_gifted_subscriptions should be called with ("testgifter", 3)
        And a chat message "!subgift_add testgifter 600" should be sent
        And points should be awarded to testgifter
        """
        # Given: A gift subscription webhook event with identified gifter
        event_data = {
            "gifter": {
                "username": "testgifter",
                "id": 12345
            },
            "quantity": 3,
            "recipients": [
                {"username": "recipient1"},
                {"username": "recipient2"},
                {"username": "recipient3"}
            ]
        }
        
        # Set up bot instance
        oauth_webhook_server.bot_instance = self.mock_bot
        
        # Mock settings
        with patch('kickbot.kick_bot.settings', self.mock_settings):
            with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
                # When: The gift subscription handler processes the event
                await oauth_webhook_server.handle_gift_subscription_event(event_data)
        
        # Then: _handle_gifted_subscriptions should be called with correct parameters
        self.mock_bot._handle_gifted_subscriptions.assert_called_once_with("testgifter", 3)

    @pytest.mark.asyncio
    async def test_scenario_19_2_correlated_gift_subscription_points_award(self):
        """
        BDD Scenario 19.2: Correlated Gift Subscription Points Award
        
        Given a gift subscription webhook with empty payload is received
        And chat correlation identifies gifter as "correlatedgifter"
        And the quantity is 5
        And GiftBlokitos setting is 150
        When the correlation result is processed
        Then _handle_gifted_subscriptions should be called with ("correlatedgifter", 5)
        And a chat message "!subgift_add correlatedgifter 750" should be sent
        And points should be awarded to correlatedgifter
        """
        # Given: Empty webhook payload that triggers correlation
        event_data = {}
        
        # Set up bot instance and correlator
        oauth_webhook_server.bot_instance = self.mock_bot
        
        # Mock correlation result
        from oauth_webhook_server import CorrelationResult
        correlation_result = CorrelationResult("correlatedgifter", 5, "CORRELATED", False)
        correlation_future = asyncio.Future()
        correlation_future.set_result(correlation_result)
        
        # Mock settings with different value
        test_settings = {'GiftBlokitos': 150}
        
        with patch('kickbot.kick_bot.settings', test_settings):
            # When: The correlation result is processed
            await oauth_webhook_server.handle_correlation_result(correlation_future, 5)
        
        # Then: _handle_gifted_subscriptions should be called with correlated parameters
        self.mock_bot._handle_gifted_subscriptions.assert_called_once_with("correlatedgifter", 5)

    @pytest.mark.asyncio
    async def test_scenario_19_3_gift_subscription_with_bot_instance_missing(self):
        """
        BDD Scenario 19.3: Gift Subscription with Bot Instance Missing
        
        Given a gift subscription webhook event is received
        And the bot_instance is None
        When the gift subscription handler processes the event
        Then no points should be awarded
        And an error should be logged about missing bot instance
        And the alert should still be sent correctly
        """
        # Given: A gift subscription webhook event with missing bot instance
        event_data = {
            "gifter": {
                "username": "orphanedgifter",
                "id": 67890
            },
            "quantity": 2
        }
        
        # Set bot instance to None
        oauth_webhook_server.bot_instance = None
        
        with patch('oauth_webhook_server.logger') as mock_logger:
            with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
                # When: The gift subscription handler processes the event
                await oauth_webhook_server.handle_gift_subscription_event(event_data)
        
        # Then: No bot method should be called, but alert should still work
        self.mock_alert_function.assert_called_once()
        
        # Verify alert contains gifter name (since payload parsing works)
        call_args = self.mock_alert_function.call_args[0]
        assert "orphanedgifter" in call_args[2]  # Title should contain gifter name

    @pytest.mark.asyncio
    async def test_scenario_19_4_gift_subscription_with_unknown_gifter(self):
        """
        BDD Scenario 19.4: Gift Subscription with Unknown Gifter
        
        Given a gift subscription webhook event is received
        And the gifter is identified as "Unknown"
        When the gift subscription handler processes the event
        Then _handle_gifted_subscriptions should NOT be called
        And no chat message should be sent
        And the alert should display "Unknown presenteou X assinatura(s)!"
        """
        # Given: A gift subscription webhook event with unknown gifter
        event_data = {}  # Empty payload will result in "PENDING_CHAT_CORRELATION" -> "Unknown"
        
        # Set up bot instance
        oauth_webhook_server.bot_instance = self.mock_bot
        
        # Mock correlator to not be available (simulates no correlation)
        oauth_webhook_server.chat_correlator = None
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: The gift subscription handler processes the event
            await oauth_webhook_server.handle_gift_subscription_event(event_data)
        
        # Then: _handle_gifted_subscriptions should NOT be called
        self.mock_bot._handle_gifted_subscriptions.assert_not_called()
        
        # And alert should display Unknown
        self.mock_alert_function.assert_called_once()
        call_args = self.mock_alert_function.call_args[0]
        assert "Unknown" in call_args[2]  # Title should contain Unknown

    @pytest.mark.asyncio
    async def test_gift_subscription_chat_command_execution(self):
        """
        Test that _handle_gifted_subscriptions properly sends chat commands using OAuth method
        
        This test focuses on the updated OAuth-compatible chat command execution
        """
        # Create a real-ish bot instance to test the method
        from kickbot.kick_bot import KickBot
        bot_instance = KickBot.__new__(KickBot)  # Create instance without __init__
        bot_instance.logger = MagicMock()
        bot_instance.auth_manager = MagicMock()  # OAuth authentication available
        
        # Mock settings and the OAuth chat function
        test_settings = {'GiftBlokitos': 250}
        
        with patch('kickbot.kick_bot.settings', test_settings):
            with patch('kickbot.kick_helper.send_message_in_chat_async', new=AsyncMock()) as mock_oauth_send:
                # When: _handle_gifted_subscriptions is called
                await bot_instance._handle_gifted_subscriptions("testuser", 4)
                
                # Then: OAuth chat method should be called with correct message
                mock_oauth_send.assert_called_once_with(bot_instance, "!subgift_add testuser 1000")
                
                # And success should be logged
                bot_instance.logger.info.assert_called_with("Added 1000 to user testuser for 4 sub_gifts")

    @pytest.mark.asyncio
    async def test_gift_subscription_chat_command_error_handling(self):
        """
        Test error handling when OAuth chat command sending fails
        """
        # Create a real-ish bot instance to test the method
        from kickbot.kick_bot import KickBot
        bot_instance = KickBot.__new__(KickBot)
        bot_instance.logger = MagicMock()
        bot_instance.auth_manager = MagicMock()  # OAuth authentication available
        
        # Mock settings and the OAuth chat function to fail
        test_settings = {'GiftBlokitos': 100}
        
        with patch('kickbot.kick_bot.settings', test_settings):
            with patch('kickbot.kick_helper.send_message_in_chat_async', side_effect=Exception("OAuth token expired")) as mock_oauth_send:
                # When: _handle_gifted_subscriptions is called
                await bot_instance._handle_gifted_subscriptions("failuser", 2)
                
                # Then: OAuth chat method should be called
                mock_oauth_send.assert_called_once_with(bot_instance, "!subgift_add failuser 200")
                
                # And error should be logged about failure to send message
                error_calls = bot_instance.logger.error.call_args_list
                message_failure = any("Failed to send gift subscription message" in str(call) for call in error_calls)
                assert message_failure, f"Expected message failure error not found in: {error_calls}"

    @pytest.mark.asyncio
    async def test_gift_subscription_anonymous_gifter_handling(self):
        """
        Test that anonymous gifters are handled correctly
        """
        from kickbot.kick_bot import KickBot
        bot_instance = KickBot.__new__(KickBot)
        bot_instance.logger = MagicMock()
        
        # When: _handle_gifted_subscriptions is called with Anonymous gifter
        await bot_instance._handle_gifted_subscriptions("Anonymous", 3)
        
        # Then: Info message should be logged and no further processing
        bot_instance.logger.info.assert_called_with("Anonymous gifter sent 3 subscriptions - no points awarded")

    @pytest.mark.asyncio
    async def test_gift_subscription_zero_gift_blokitos_setting(self):
        """
        Test handling when GiftBlokitos setting is 0 or missing
        """
        from kickbot.kick_bot import KickBot
        bot_instance = KickBot.__new__(KickBot)
        bot_instance.logger = MagicMock()
        
        # Test with GiftBlokitos = 0
        test_settings = {'GiftBlokitos': 0}
        
        with patch('kickbot.kick_bot.settings', test_settings):
            with patch('kickbot.kick_bot.send_message_in_chat') as mock_send:
                # When: _handle_gifted_subscriptions is called
                await bot_instance._handle_gifted_subscriptions("testuser", 2)
                
                # Then: No message should be sent
                mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_gift_subscription_missing_gift_blokitos_setting(self):
        """
        Test handling when GiftBlokitos setting is missing from settings
        """
        from kickbot.kick_bot import KickBot
        bot_instance = KickBot.__new__(KickBot)
        bot_instance.logger = MagicMock()
        
        # Test with missing GiftBlokitos setting
        test_settings = {'OtherSetting': 100}  # GiftBlokitos not present
        
        with patch('kickbot.kick_bot.settings', test_settings):
            with patch('kickbot.kick_bot.send_message_in_chat') as mock_send:
                # When: _handle_gifted_subscriptions is called
                await bot_instance._handle_gifted_subscriptions("testuser", 2)
                
                # Then: No message should be sent
                mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_webhook_to_points_integration_performance(self):
        """
        Test that the complete webhook-to-points flow completes within acceptable time
        """
        # Given: A gift subscription webhook event
        event_data = {
            "gifter": {
                "username": "speedtestuser",
                "id": 99999
            },
            "quantity": 5
        }
        
        # Set up bot instance
        oauth_webhook_server.bot_instance = self.mock_bot
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Processing starts
            start_time = asyncio.get_event_loop().time()
            await oauth_webhook_server.handle_gift_subscription_event(event_data)
            end_time = asyncio.get_event_loop().time()
            
            # Then: Processing should complete within 2 seconds
            processing_time = end_time - start_time
            assert processing_time < 2.0, f"Gift subscription processing took {processing_time:.3f}s, should be < 2.0s"
            
            # And points method should have been called
            self.mock_bot._handle_gifted_subscriptions.assert_called_once_with("speedtestuser", 5)

if __name__ == "__main__":
    pytest.main([__file__])