"""
Integration test for Story 18: Regular Subscription Event Username Extraction
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


class TestStory18Integration:
    """Integration tests for Story 18 subscription event username and tier extraction"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_alert_function = AsyncMock()

    @pytest.mark.asyncio
    async def test_complete_subscription_event_integration(self):
        """
        Test complete subscription event processing with real-world payload structures
        
        This test simulates the complete flow from webhook receipt to alert display
        """
        test_scenarios = [
            {
                "name": "Standard Kick API subscription payload",
                "payload": {
                    "subscriber": {
                        "username": "premiumuser123",
                        "id": 123456,
                        "slug": "premiumuser123"
                    },
                    "tier": 2,
                    "subscribed_at": "2024-01-15T10:30:00Z"
                },
                "expected_username": "premiumuser123",
                "expected_tier": 2
            },
            {
                "name": "Alternative user object structure with subscription_tier",
                "payload": {
                    "user": {
                        "username": "altsubuser456",
                        "id": 456789
                    },
                    "subscription_tier": 3,
                    "event_type": "subscription"
                },
                "expected_username": "altsubuser456",
                "expected_tier": 3
            },
            {
                "name": "Direct username field with nested tier",
                "payload": {
                    "username": "directsubuser789",
                    "user_id": 789012,
                    "subscription": {
                        "tier": 1
                    },
                    "timestamp": 1705312200
                },
                "expected_username": "directsubuser789",
                "expected_tier": 1
            },
            {
                "name": "Level field instead of tier",
                "payload": {
                    "subscriber": {
                        "username": "leveluser999",
                        "id": 999888
                    },
                    "level": 2
                },
                "expected_username": "leveluser999",
                "expected_tier": 2
            }
        ]

        for scenario in test_scenarios:
            with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
                # Process the subscription event
                await oauth_webhook_server.handle_subscription_event(scenario["payload"])
                
                # Verify alert was called with correct username and tier
                self.mock_alert_function.assert_called()
                call_args = self.mock_alert_function.call_args[0]
                
                # Check title and description contain expected username and tier
                title = call_args[2]
                description = call_args[3]
                
                expected_title = f"Nova assinatura Tier {scenario['expected_tier']}: {scenario['expected_username']}!"
                expected_description = f"Obrigado pela assinatura, {scenario['expected_username']}!"
                
                assert title == expected_title, f"Title mismatch for {scenario['name']}: expected '{expected_title}' but got '{title}'"
                assert description == expected_description, f"Description mismatch for {scenario['name']}: expected '{expected_description}' but got '{description}'"
                
                # Reset mock for next scenario
                self.mock_alert_function.reset_mock()

    @pytest.mark.asyncio
    async def test_username_extraction_function_for_subscriptions(self):
        """
        Test the username extraction function directly with subscription payloads
        """
        test_cases = [
            # Standard subscription cases
            ({"subscriber": {"username": "subuser1"}}, "subscription", "subuser1"),
            ({"user": {"username": "subuser2"}}, "subscription", "subuser2"),
            ({"username": "subuser3"}, "subscription", "subuser3"),
            
            # Edge cases
            ({}, "subscription", "Unknown"),
            ({"subscriber": {}}, "subscription", "Unknown"),
            ({"subscriber": {"username": ""}}, "subscription", "Unknown"),
            ({"subscriber": {"username": "   "}}, "subscription", "Unknown"),
            
            # Valid edge cases with whitespace
            ({"subscriber": {"username": "  validsubuser  "}}, "subscription", "  validsubuser  "),
        ]

        for payload, event_type, expected in test_cases:
            result = oauth_webhook_server.extract_username_from_payload(payload, event_type)
            assert result == expected, f"Expected '{expected}' but got '{result}' for payload {payload}"

    @pytest.mark.asyncio
    async def test_tier_extraction_function_directly(self):
        """
        Test the tier extraction function directly with various payloads
        """
        test_cases = [
            # Standard tier cases
            ({"tier": 1}, 1),
            ({"tier": 2}, 2),
            ({"tier": 3}, 3),
            
            # Alternative field names
            ({"subscription_tier": 2}, 2),
            ({"level": 3}, 3),
            ({"sub_tier": 1}, 1),
            
            # Nested structure
            ({"subscription": {"tier": 2}}, 2),
            
            # String values (should convert to int)
            ({"tier": "2"}, 2),
            ({"subscription_tier": "3"}, 3),
            
            # Edge cases - defaults to 1
            ({}, 1),
            ({"tier": None}, 1),
            ({"tier": ""}, 1),
            ({"tier": 0}, 1),  # Invalid tier
            ({"tier": 11}, 1), # Invalid tier (too high)
            ({"tier": -1}, 1), # Invalid tier (negative)
            
            # Valid boundary cases
            ({"tier": 1}, 1),
            ({"tier": 10}, 10),
        ]

        for payload, expected in test_cases:
            result = oauth_webhook_server.extract_tier_from_payload(payload)
            assert result == expected, f"Expected tier {expected} but got {result} for payload {payload}"

    @pytest.mark.asyncio
    async def test_performance_with_complex_subscription_payload(self):
        """
        Test performance with a complex, realistic subscription payload
        """
        complex_payload = {
            "subscriber": {
                "username": "complexsubuser",
                "id": 123456,
                "slug": "complexsubuser",
                "profile_pic": "https://cdn.kick.com/avatar.jpg",
                "verified": True,
                "follower_count": 5000,
                "following_count": 1000,
                "bio": "A complex subscriber with lots of data",
                "social_links": {
                    "twitter": "@complexsubuser",
                    "youtube": "complexsubuser"
                },
                "badges": ["verified", "subscriber"],
                "stats": {
                    "total_streams": 50,
                    "total_hours": 200
                }
            },
            "tier": 3,
            "subscribed_at": "2024-01-15T10:30:00Z",
            "subscription_months": 6,
            "is_gift": False,
            "channel": {
                "id": 789012,
                "username": "streamername",
                "slug": "streamername"
            },
            "payment": {
                "currency": "USD",
                "amount": 9.99,
                "method": "stripe"
            },
            "metadata": {
                "source": "web",
                "referrer": "direct",
                "campaign": "new_year_promo"
            }
        }

        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            start_time = asyncio.get_event_loop().time()
            await oauth_webhook_server.handle_subscription_event(complex_payload)
            end_time = asyncio.get_event_loop().time()
            
            processing_time = end_time - start_time
            assert processing_time < 0.1, f"Complex subscription payload processing took {processing_time:.3f}s, should be < 0.1s"
            
            # Verify correct username and tier were extracted
            call_args = self.mock_alert_function.call_args[0]
            title = call_args[2]
            description = call_args[3]
            
            assert "complexsubuser" in title
            assert "Tier 3" in title
            assert "complexsubuser" in description

    @pytest.mark.asyncio
    async def test_subscription_event_with_real_world_edge_cases(self):
        """
        Test subscription events with real-world edge cases and malformed data
        """
        edge_case_scenarios = [
            {
                "name": "Subscription with extra nested data",
                "payload": {
                    "data": {
                        "subscriber": {
                            "username": "nesteduser"
                        },
                        "tier": 2
                    }
                },
                "expected_username": "Unknown",  # Our extractor doesn't handle this level of nesting
                "expected_tier": 1
            },
            {
                "name": "Subscription with numeric username",
                "payload": {
                    "subscriber": {
                        "username": "12345"
                    },
                    "tier": 1
                },
                "expected_username": "12345",
                "expected_tier": 1
            },
            {
                "name": "Subscription with special characters in username",
                "payload": {
                    "subscriber": {
                        "username": "user_with-special.chars123"
                    },
                    "tier": 2
                },
                "expected_username": "user_with-special.chars123",
                "expected_tier": 2
            }
        ]

        for scenario in edge_case_scenarios:
            with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
                await oauth_webhook_server.handle_subscription_event(scenario["payload"])
                
                call_args = self.mock_alert_function.call_args[0]
                title = call_args[2]
                
                expected_title = f"Nova assinatura Tier {scenario['expected_tier']}: {scenario['expected_username']}!"
                assert title == expected_title, f"Edge case '{scenario['name']}' failed: expected '{expected_title}' but got '{title}'"
                
                self.mock_alert_function.reset_mock()

if __name__ == "__main__":
    pytest.main([__file__])