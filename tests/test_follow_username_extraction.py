"""
Test suite for Follow Event Username Extraction (Story 17)
BDD scenarios testing robust username extraction from follow webhook payloads
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import oauth_webhook_server


class TestFollowUsernameExtraction:
    """Test follow event username extraction with multiple payload structures"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_alert_function = AsyncMock()
        
    @pytest.mark.asyncio
    async def test_scenario_17_1_standard_follow_event_with_nested_user_object(self):
        """
        BDD Scenario 17.1: Standard Follow Event with Nested User Object
        
        Given a follow webhook event is received
        And the payload contains: {"follower": {"username": "testuser123"}}
        When the follow event handler processes the data
        Then the follower_name should be "testuser123"
        And the alert should display "Novo seguidor: testuser123!"
        """
        # Given: A follow webhook event with nested user object
        event_data = {
            "follower": {
                "username": "testuser123",
                "id": 12345
            }
        }
        
        # Mock the send_alert function to capture the alert parameters
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: The follow event handler processes the data
            await oauth_webhook_server.handle_follow_event(event_data)
        
        # Then: The alert should be called with correct username
        self.mock_alert_function.assert_called_once()
        call_args = self.mock_alert_function.call_args[0]
        
        # Verify alert contains correct username
        assert "testuser123" in call_args[2]  # Title should contain username
        assert "testuser123" in call_args[3]  # Description should contain username
        assert call_args[2] == "Novo seguidor: testuser123!"
        assert call_args[3] == "Obrigado por seguir, testuser123!"

    @pytest.mark.asyncio
    async def test_scenario_17_2_follow_event_with_alternative_payload_structure(self):
        """
        BDD Scenario 17.2: Follow Event with Alternative Payload Structure
        
        Given a follow webhook event is received  
        And the payload contains: {"user": {"username": "testuser456"}}
        When the follow event handler processes the data
        Then the follower_name should be "testuser456"
        And the alert should display "Novo seguidor: testuser456!"
        """
        # Given: A follow webhook event with alternative payload structure
        event_data = {
            "user": {
                "username": "testuser456",
                "id": 45678
            }
        }
        
        # Mock the send_alert function to capture the alert parameters
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: The follow event handler processes the data
            await oauth_webhook_server.handle_follow_event(event_data)
        
        # Then: The alert should be called with correct username
        self.mock_alert_function.assert_called_once()
        call_args = self.mock_alert_function.call_args[0]
        
        # Verify alert contains correct username from alternative structure
        assert "testuser456" in call_args[2]  # Title should contain username
        assert "testuser456" in call_args[3]  # Description should contain username
        assert call_args[2] == "Novo seguidor: testuser456!"
        assert call_args[3] == "Obrigado por seguir, testuser456!"

    @pytest.mark.asyncio
    async def test_scenario_17_3_follow_event_with_missing_username_falls_back(self):
        """
        BDD Scenario 17.3: Follow Event with Missing Username Falls Back
        
        Given a follow webhook event is received
        And the payload contains: {"follower": {}}
        When the follow event handler processes the data
        Then the follower_name should be "Unknown"
        And the alert should display "Novo seguidor: Unknown!"
        """
        # Given: A follow webhook event with missing username
        event_data = {
            "follower": {
                "id": 78910
                # username is missing
            }
        }
        
        # Mock the send_alert function to capture the alert parameters
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: The follow event handler processes the data
            await oauth_webhook_server.handle_follow_event(event_data)
        
        # Then: The alert should be called with "Unknown" fallback
        self.mock_alert_function.assert_called_once()
        call_args = self.mock_alert_function.call_args[0]
        
        # Verify alert contains fallback username
        assert "Unknown" in call_args[2]  # Title should contain Unknown
        assert "Unknown" in call_args[3]  # Description should contain Unknown
        assert call_args[2] == "Novo seguidor: Unknown!"
        assert call_args[3] == "Obrigado por seguir, Unknown!"

    @pytest.mark.asyncio
    async def test_follow_event_with_direct_username_field(self):
        """
        Additional test case: Follow event with direct username field
        
        Given a follow webhook event is received
        And the payload contains: {"username": "directuser"}
        When the follow event handler processes the data
        Then the follower_name should be "directuser"
        And the alert should display "Novo seguidor: directuser!"
        """
        # Given: A follow webhook event with direct username field
        event_data = {
            "username": "directuser",
            "id": 99999
        }
        
        # Mock the send_alert function to capture the alert parameters
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: The follow event handler processes the data
            await oauth_webhook_server.handle_follow_event(event_data)
        
        # Then: The alert should be called with correct username
        self.mock_alert_function.assert_called_once()
        call_args = self.mock_alert_function.call_args[0]
        
        # Verify alert contains correct username from direct field
        assert "directuser" in call_args[2]  # Title should contain username
        assert "directuser" in call_args[3]  # Description should contain username
        assert call_args[2] == "Novo seguidor: directuser!"
        assert call_args[3] == "Obrigado por seguir, directuser!"

    @pytest.mark.asyncio
    async def test_follow_event_with_empty_payload(self):
        """
        Edge case: Follow event with completely empty payload
        
        Given a follow webhook event is received
        And the payload is completely empty: {}
        When the follow event handler processes the data
        Then the follower_name should be "Unknown"
        And the alert should display "Novo seguidor: Unknown!"
        """
        # Given: A follow webhook event with empty payload
        event_data = {}
        
        # Mock the send_alert function to capture the alert parameters
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: The follow event handler processes the data
            await oauth_webhook_server.handle_follow_event(event_data)
        
        # Then: The alert should be called with "Unknown" fallback
        self.mock_alert_function.assert_called_once()
        call_args = self.mock_alert_function.call_args[0]
        
        # Verify alert contains fallback username
        assert "Unknown" in call_args[2]  # Title should contain Unknown
        assert "Unknown" in call_args[3]  # Description should contain Unknown
        assert call_args[2] == "Novo seguidor: Unknown!"
        assert call_args[3] == "Obrigado por seguir, Unknown!"

    @pytest.mark.asyncio
    async def test_follow_event_error_handling(self):
        """
        Test error handling in follow event processing
        
        Given a follow webhook event processing fails
        When an exception occurs during processing
        Then the error should be logged
        And the function should not crash
        """
        # Given: A follow webhook event that will cause an exception
        event_data = {"follower": {"username": "testuser"}}
        
        # Mock send_alert to raise an exception
        with patch('oauth_webhook_server.send_alert', side_effect=Exception("Alert service down")):
            with patch('oauth_webhook_server.logger') as mock_logger:
                # When: The follow event handler processes the data
                await oauth_webhook_server.handle_follow_event(event_data)
                
                # Then: Error should be logged
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args[0][0]
                assert "Error handling follow event" in error_call

    @pytest.mark.asyncio
    async def test_follow_event_performance(self):
        """
        Test that follow event processing completes within acceptable time
        
        Given a follow webhook event is received
        When the follow event handler processes the data
        Then the processing should complete within 1 second
        """
        # Given: A follow webhook event
        event_data = {
            "follower": {
                "username": "performancetest",
                "id": 12345
            }
        }
        
        # Mock the send_alert function for performance testing
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # When: Processing starts
            start_time = asyncio.get_event_loop().time()
            await oauth_webhook_server.handle_follow_event(event_data)
            end_time = asyncio.get_event_loop().time()
            
            # Then: Processing should complete within 1 second
            processing_time = end_time - start_time
            assert processing_time < 1.0, f"Follow event processing took {processing_time:.3f}s, should be < 1.0s"

if __name__ == "__main__":
    pytest.main([__file__])