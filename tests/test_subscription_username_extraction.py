"""
Test suite for Subscription Event Username Extraction (Story 18)
BDD scenarios testing robust username extraction from subscription webhook payloads
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import oauth_webhook_server


class TestSubscriptionUsernameExtraction:
    """Test subscription event username extraction with multiple payload structures"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_alert_function = AsyncMock()
        
    @pytest.mark.asyncio
    async def test_scenario_18_1_standard_subscription_event_with_nested_user_object(self):
        """
        BDD Scenario 18.1: Standard Subscription Event with Nested User Object
        
        Given a subscription webhook event is received
        And the payload contains: {"subscriber": {"username": "testuser789"}, "tier": 2}
        When the subscription event handler processes the data
        Then the subscriber_name should be "testuser789"
        And the tier should be 2
        And the alert should display "Nova assinatura Tier 2: testuser789!"
        """
        # Given: A subscription webhook event with nested user object
        event_data = {
            "subscriber": {
                "username": "testuser789",
                "id": 789012
            },
            "tier": 2
        }
        
        # Mock the send_alert function to capture the alert parameters
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: The subscription event handler processes the data
            await oauth_webhook_server.handle_subscription_event(event_data)
        
        # Then: The alert should be called with correct username and tier
        self.mock_alert_function.assert_called_once()
        call_args = self.mock_alert_function.call_args[0]
        
        # Verify alert contains correct username and tier
        assert "testuser789" in call_args[2]  # Title should contain username
        assert "testuser789" in call_args[3]  # Description should contain username
        assert "Tier 2" in call_args[2]       # Title should contain tier
        assert call_args[2] == "Nova assinatura Tier 2: testuser789!"
        assert call_args[3] == "Obrigado pela assinatura, testuser789!"

    @pytest.mark.asyncio
    async def test_scenario_18_2_subscription_event_with_alternative_payload_structure(self):
        """
        BDD Scenario 18.2: Subscription Event with Alternative Payload Structure
        
        Given a subscription webhook event is received
        And the payload contains: {"user": {"username": "testuser999"}, "subscription_tier": 1}
        When the subscription event handler processes the data
        Then the subscriber_name should be "testuser999"
        And the tier should be 1
        And the alert should display "Nova assinatura Tier 1: testuser999!"
        """
        # Given: A subscription webhook event with alternative payload structure
        event_data = {
            "user": {
                "username": "testuser999",
                "id": 99999
            },
            "subscription_tier": 1
        }
        
        # Mock the send_alert function to capture the alert parameters
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: The subscription event handler processes the data
            await oauth_webhook_server.handle_subscription_event(event_data)
        
        # Then: The alert should be called with correct username and tier
        self.mock_alert_function.assert_called_once()
        call_args = self.mock_alert_function.call_args[0]
        
        # Verify alert contains correct username and tier from alternative structure
        assert "testuser999" in call_args[2]  # Title should contain username
        assert "testuser999" in call_args[3]  # Description should contain username
        assert "Tier 1" in call_args[2]       # Title should contain tier
        assert call_args[2] == "Nova assinatura Tier 1: testuser999!"
        assert call_args[3] == "Obrigado pela assinatura, testuser999!"

    @pytest.mark.asyncio
    async def test_scenario_18_3_subscription_event_with_direct_username_field(self):
        """
        BDD Scenario 18.3: Subscription Event with Direct Username Field
        
        Given a subscription webhook event is received
        And the payload contains: {"username": "directuser", "tier": 3}
        When the subscription event handler processes the data
        Then the subscriber_name should be "directuser"
        And the tier should be 3
        And the alert should display "Nova assinatura Tier 3: directuser!"
        """
        # Given: A subscription webhook event with direct username field
        event_data = {
            "username": "directuser",
            "tier": 3,
            "id": 33333
        }
        
        # Mock the send_alert function to capture the alert parameters
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: The subscription event handler processes the data
            await oauth_webhook_server.handle_subscription_event(event_data)
        
        # Then: The alert should be called with correct username and tier
        self.mock_alert_function.assert_called_once()
        call_args = self.mock_alert_function.call_args[0]
        
        # Verify alert contains correct username and tier from direct fields
        assert "directuser" in call_args[2]  # Title should contain username
        assert "directuser" in call_args[3]  # Description should contain username
        assert "Tier 3" in call_args[2]      # Title should contain tier
        assert call_args[2] == "Nova assinatura Tier 3: directuser!"
        assert call_args[3] == "Obrigado pela assinatura, directuser!"

    @pytest.mark.asyncio
    async def test_subscription_event_with_missing_username_falls_back(self):
        """
        Test subscription event with missing username falls back to "Unknown"
        
        Given a subscription webhook event is received
        And the payload contains: {"subscriber": {}, "tier": 2}
        When the subscription event handler processes the data
        Then the subscriber_name should be "Unknown"
        And the alert should display "Nova assinatura Tier 2: Unknown!"
        """
        # Given: A subscription webhook event with missing username
        event_data = {
            "subscriber": {
                "id": 11111
                # username is missing
            },
            "tier": 2
        }
        
        # Mock the send_alert function to capture the alert parameters
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: The subscription event handler processes the data
            await oauth_webhook_server.handle_subscription_event(event_data)
        
        # Then: The alert should be called with "Unknown" fallback
        self.mock_alert_function.assert_called_once()
        call_args = self.mock_alert_function.call_args[0]
        
        # Verify alert contains fallback username
        assert "Unknown" in call_args[2]  # Title should contain Unknown
        assert "Unknown" in call_args[3]  # Description should contain Unknown
        assert "Tier 2" in call_args[2]   # Title should still contain tier
        assert call_args[2] == "Nova assinatura Tier 2: Unknown!"
        assert call_args[3] == "Obrigado pela assinatura, Unknown!"

    @pytest.mark.asyncio
    async def test_subscription_event_with_empty_payload(self):
        """
        Edge case: Subscription event with completely empty payload
        
        Given a subscription webhook event is received
        And the payload is completely empty: {}
        When the subscription event handler processes the data
        Then the subscriber_name should be "Unknown"
        And the tier should default to 1
        And the alert should display "Nova assinatura Tier 1: Unknown!"
        """
        # Given: A subscription webhook event with empty payload
        event_data = {}
        
        # Mock the send_alert function to capture the alert parameters
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: The subscription event handler processes the data
            await oauth_webhook_server.handle_subscription_event(event_data)
        
        # Then: The alert should be called with defaults
        self.mock_alert_function.assert_called_once()
        call_args = self.mock_alert_function.call_args[0]
        
        # Verify alert contains fallback values
        assert "Unknown" in call_args[2]  # Title should contain Unknown
        assert "Unknown" in call_args[3]  # Description should contain Unknown
        assert "Tier 1" in call_args[2]   # Title should contain default tier
        assert call_args[2] == "Nova assinatura Tier 1: Unknown!"
        assert call_args[3] == "Obrigado pela assinatura, Unknown!"

    @pytest.mark.asyncio
    async def test_subscription_event_tier_extraction_strategies(self):
        """
        Test various tier extraction strategies
        
        Tests different ways tier information might be provided in payloads
        """
        tier_test_cases = [
            # Standard tier field
            ({"subscriber": {"username": "user1"}, "tier": 2}, 2),
            # Alternative tier field names
            ({"subscriber": {"username": "user2"}, "subscription_tier": 3}, 3),
            ({"subscriber": {"username": "user3"}, "level": 1}, 1),
            # Nested tier information
            ({"subscriber": {"username": "user4"}, "subscription": {"tier": 2}}, 2),
            # Missing tier defaults to 1
            ({"subscriber": {"username": "user5"}}, 1),
        ]
        
        for event_data, expected_tier in tier_test_cases:
            with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
                await oauth_webhook_server.handle_subscription_event(event_data)
                
                call_args = self.mock_alert_function.call_args[0]
                title = call_args[2]
                
                # Verify tier is correctly extracted and displayed
                assert f"Tier {expected_tier}" in title, f"Expected tier {expected_tier} not found in title: {title}"
                
                # Reset mock for next test case
                self.mock_alert_function.reset_mock()

    @pytest.mark.asyncio
    async def test_subscription_event_error_handling(self):
        """
        Test error handling in subscription event processing
        
        Given a subscription webhook event processing fails
        When an exception occurs during processing
        Then the error should be logged
        And the function should not crash
        """
        # Given: A subscription webhook event that will cause an exception
        event_data = {"subscriber": {"username": "testuser"}, "tier": 1}
        
        # Mock send_alert to raise an exception
        with patch('oauth_webhook_server.send_alert', side_effect=Exception("Alert service down")):
            with patch('oauth_webhook_server.logger') as mock_logger:
                # When: The subscription event handler processes the data
                await oauth_webhook_server.handle_subscription_event(event_data)
                
                # Then: Error should be logged
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args[0][0]
                assert "Error handling subscription event" in error_call

    @pytest.mark.asyncio
    async def test_subscription_event_performance(self):
        """
        Test that subscription event processing completes within acceptable time
        
        Given a subscription webhook event is received
        When the subscription event handler processes the data
        Then the processing should complete within 1 second
        """
        # Given: A subscription webhook event
        event_data = {
            "subscriber": {
                "username": "performancetest",
                "id": 12345
            },
            "tier": 2
        }
        
        # Mock the send_alert function for performance testing
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Processing starts
            start_time = asyncio.get_event_loop().time()
            await oauth_webhook_server.handle_subscription_event(event_data)
            end_time = asyncio.get_event_loop().time()
            
            # Then: Processing should complete within 1 second
            processing_time = end_time - start_time
            assert processing_time < 1.0, f"Subscription event processing took {processing_time:.3f}s, should be < 1.0s"

if __name__ == "__main__":
    pytest.main([__file__])