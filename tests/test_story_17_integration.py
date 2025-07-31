"""
Integration test for Story 17: Follow Event Username Extraction
Test complete functionality with realistic webhook payloads
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import oauth_webhook_server


class TestStory17Integration:
    """Integration tests for Story 17 follow event username extraction"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_alert_function = AsyncMock()

    @pytest.mark.asyncio
    async def test_complete_follow_event_integration(self):
        """
        Test complete follow event processing with real-world payload structures
        
        This test simulates the complete flow from webhook receipt to alert display
        """
        test_scenarios = [
            {
                "name": "Standard Kick API follow payload",
                "payload": {
                    "follower": {
                        "username": "kickuser123",
                        "id": 123456,
                        "slug": "kickuser123"
                    },
                    "followed_at": "2024-01-15T10:30:00Z"
                },
                "expected_username": "kickuser123"
            },
            {
                "name": "Alternative user object structure",
                "payload": {
                    "user": {
                        "username": "altuser456",
                        "id": 456789
                    },
                    "event_type": "follow"
                },
                "expected_username": "altuser456"
            },
            {
                "name": "Direct username field",
                "payload": {
                    "username": "directuser789",
                    "user_id": 789012,
                    "timestamp": 1705312200
                },
                "expected_username": "directuser789"
            }
        ]

        for scenario in test_scenarios:
            with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
                # Process the follow event
                await oauth_webhook_server.handle_follow_event(scenario["payload"])
                
                # Verify alert was called with correct username
                self.mock_alert_function.assert_called()
                call_args = self.mock_alert_function.call_args[0]
                
                # Check title and description contain expected username
                title = call_args[2]
                description = call_args[3]
                
                assert scenario["expected_username"] in title, f"Username not found in title for {scenario['name']}"
                assert scenario["expected_username"] in description, f"Username not found in description for {scenario['name']}"
                
                # Reset mock for next scenario
                self.mock_alert_function.reset_mock()

    @pytest.mark.asyncio
    async def test_username_extraction_function_directly(self):
        """
        Test the username extraction function directly with various payloads
        """
        test_cases = [
            # Standard cases
            ({"follower": {"username": "user1"}}, "follow", "user1"),
            ({"user": {"username": "user2"}}, "follow", "user2"),
            ({"username": "user3"}, "follow", "user3"),
            
            # Edge cases
            ({}, "follow", "Unknown"),
            ({"follower": {}}, "follow", "Unknown"),
            ({"follower": {"username": ""}}, "follow", "Unknown"),
            ({"follower": {"username": "   "}}, "follow", "Unknown"),
            
            # Valid edge cases
            ({"follower": {"username": "  validuser  "}}, "follow", "  validuser  "),
        ]

        for payload, event_type, expected in test_cases:
            result = oauth_webhook_server.extract_username_from_payload(payload, event_type)
            assert result == expected, f"Expected '{expected}' but got '{result}' for payload {payload}"

    @pytest.mark.asyncio
    async def test_performance_with_complex_payload(self):
        """
        Test performance with a complex, realistic payload
        """
        complex_payload = {
            "follower": {
                "username": "complexuser",
                "id": 123456,
                "slug": "complexuser",
                "profile_pic": "https://cdn.kick.com/avatar.jpg",
                "verified": True,
                "follower_count": 1000,
                "following_count": 500,
                "bio": "A complex user with lots of data",
                "social_links": {
                    "twitter": "@complexuser",
                    "youtube": "complexuser"
                },
                "badges": ["verified", "partner"],
                "stats": {
                    "total_streams": 100,
                    "total_hours": 500
                }
            },
            "followed_at": "2024-01-15T10:30:00Z",
            "channel": {
                "id": 789012,
                "username": "streamername",
                "slug": "streamername"
            },
            "metadata": {
                "source": "web",
                "referrer": "direct",
                "campaign": None
            }
        }

        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            start_time = asyncio.get_event_loop().time()
            await oauth_webhook_server.handle_follow_event(complex_payload)
            end_time = asyncio.get_event_loop().time()
            
            processing_time = end_time - start_time
            assert processing_time < 0.1, f"Complex payload processing took {processing_time:.3f}s, should be < 0.1s"
            
            # Verify correct username was extracted
            call_args = self.mock_alert_function.call_args[0]
            assert "complexuser" in call_args[2]

if __name__ == "__main__":
    pytest.main([__file__])