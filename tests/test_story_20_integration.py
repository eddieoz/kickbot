"""
Integration test for Story 20: Unified Username Extraction Utility
Test the complete unified extraction system with real-world scenarios
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from oauth_webhook_server import UnifiedUsernameExtractor, ExtractionResult, unified_extractor


class TestStory20Integration:
    """Integration tests for the unified username extraction utility"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_alert_function = AsyncMock()

    @pytest.mark.asyncio
    async def test_complete_unified_extraction_system(self):
        """
        Test the complete unified extraction system with various real-world payloads
        """
        extractor = UnifiedUsernameExtractor()
        
        # Test scenarios covering different event types and payload structures
        real_world_scenarios = [
            {
                "name": "Kick Standard Follow Event",
                "payload": {
                    "follower": {
                        "username": "kick_follower_123",
                        "id": 123456,
                        "slug": "kick_follower_123",
                        "verified": False
                    },
                    "followed_at": "2024-01-15T10:30:00Z"
                },
                "event_type": "follow",
                "expected_username": "kick_follower_123",
                "expected_strategy": "follower.username"
            },
            {
                "name": "Alternative API Follow Event",
                "payload": {
                    "user": {
                        "username": "alt_follower_456",
                        "profile": {"verified": True}
                    },
                    "event": "follow",
                    "timestamp": 1705312200
                },
                "event_type": "follow", 
                "expected_username": "alt_follower_456",
                "expected_strategy": "user.username"
            },
            {
                "name": "Standard Subscription Event",
                "payload": {
                    "subscriber": {
                        "username": "premium_sub_789",
                        "id": 789012
                    },
                    "tier": 2,
                    "months": 3
                },
                "event_type": "subscription",
                "expected_username": "premium_sub_789", 
                "expected_strategy": "subscriber.username"
            },
            {
                "name": "Gift Subscription Event",
                "payload": {
                    "gifter": {
                        "username": "generous_gifter",
                        "id": 555555
                    },
                    "recipients": [
                        {"username": "recipient1"},
                        {"username": "recipient2"}
                    ],
                    "quantity": 2
                },
                "event_type": "gift_subscription",
                "expected_username": "generous_gifter",
                "expected_strategy": "gifter.username"
            }
        ]
        
        for scenario in real_world_scenarios:
            # When: Username extraction is performed
            result = extractor.extract_username(scenario["payload"], scenario["event_type"])
            
            # Then: Should extract correctly with detailed information
            assert result.username == scenario["expected_username"], f"Failed for {scenario['name']}"
            assert result.success is True, f"Failed for {scenario['name']}"
            assert result.strategy_used == scenario["expected_strategy"], f"Failed for {scenario['name']}"
            assert result.event_type == scenario["event_type"], f"Failed for {scenario['name']}"
            assert result.payload == scenario["payload"], f"Failed for {scenario['name']}"

    @pytest.mark.asyncio
    async def test_custom_strategy_registration_and_usage(self):
        """
        Test registering custom strategies for new event types or payload formats
        """
        extractor = UnifiedUsernameExtractor()
        
        # Register strategies for a hypothetical new event type
        extractor.register_strategy("channel_raid", "raider.username",
                                   lambda data: data.get('raid_info', {}).get('raider', {}).get('username'))
        
        extractor.register_strategy("channel_raid", "raid_leader.name", 
                                   lambda data: data.get('leader', {}).get('name'))
        
        # Test the custom strategies
        raid_payload = {
            "raid_info": {
                "raider": {
                    "username": "raid_leader_123",
                    "viewer_count": 1000
                }
            },
            "target_channel": "raided_channel"
        }
        
        # When: Custom event extraction is performed
        result = extractor.extract_username(raid_payload, "channel_raid")
        
        # Then: Should use the first matching custom strategy
        assert result.username == "raid_leader_123"
        assert result.success is True
        assert result.strategy_used == "raider.username"
        assert result.event_type == "channel_raid"

    @pytest.mark.asyncio
    async def test_enhanced_error_handling_and_logging(self):
        """
        Test that the unified system provides enhanced error handling and logging
        """
        extractor = UnifiedUsernameExtractor()
        
        complex_failing_payloads = [
            {
                "name": "Deeply nested structure",
                "payload": {
                    "event": {
                        "data": {
                            "user_info": {
                                "profile": {
                                    "display_name": "not_username"  # Wrong field
                                }
                            }
                        }
                    }
                },
                "event_type": "follow"
            },
            {
                "name": "Malformed data types",
                "payload": {
                    "follower": {
                        "username": 12345  # Number instead of string
                    }
                },
                "event_type": "follow"
            },
            {
                "name": "Null values",
                "payload": {
                    "follower": {
                        "username": None
                    },
                    "user": {
                        "username": ""  # Empty string
                    }
                },
                "event_type": "follow"
            }
        ]
        
        for failing_case in complex_failing_payloads:
            with patch('oauth_webhook_server.logger') as mock_logger:
                # When: Extraction is attempted on failing payload
                result = extractor.extract_username(failing_case["payload"], failing_case["event_type"])
                
                # Then: Should fail gracefully with comprehensive logging
                assert result.username == "Unknown", f"Failed case: {failing_case['name']}"
                assert result.success is False, f"Failed case: {failing_case['name']}"
                assert result.strategy_used is None, f"Failed case: {failing_case['name']}"
                
                # And should log warning about failure
                mock_logger.warning.assert_called()
                warning_call = mock_logger.warning.call_args[0][0]
                assert "Failed to extract username" in warning_call

    @pytest.mark.asyncio
    async def test_performance_with_realistic_payload_sizes(self):
        """
        Test performance with realistic, large webhook payloads
        """
        extractor = UnifiedUsernameExtractor()
        
        # Create a large, realistic payload
        large_payload = {
            "follower": {
                "username": "performance_user",
                "id": 999999,
                "slug": "performance_user",
                "verified": True,
                "profile_pic": "https://cdn.kick.com/very_long_url_to_profile_image.jpg",
                "bio": "A very long user biography that contains lots of text and information about the user's streaming history and preferences",
                "follower_count": 50000,
                "following_count": 1500,
                "badges": ["verified", "partner", "early_supporter"] * 10,  # Lots of badges
                "social_links": {
                    "twitter": "@performance_user",
                    "youtube": "performance_user_channel",
                    "instagram": "performance_user_insta",
                    "tiktok": "performance_user_tiktok"
                },
                "streaming_stats": {
                    "total_hours": 5000,
                    "average_viewers": 1200,
                    "peak_viewers": 10000,
                    "categories": ["Gaming", "Just Chatting", "Music"] * 20
                },
                "recent_activity": [
                    {"action": "followed", "target": f"user_{i}", "timestamp": f"2024-01-{i:02d}T10:30:00Z"}
                    for i in range(1, 101)  # 100 recent activities
                ]
            },
            "followed_at": "2024-01-15T10:30:00Z",
            "metadata": {
                "source": "web_client",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "ip_address": "192.168.1.100",
                "session_id": "session_" + "x" * 100,  # Long session ID
                "additional_data": ["item_" + str(i) for i in range(1000)]  # Large array
            }
        }
        
        # When: Extraction is performed on large payload
        start_time = asyncio.get_event_loop().time()
        result = extractor.extract_username(large_payload, "follow")
        end_time = asyncio.get_event_loop().time()
        
        # Then: Should complete quickly despite large payload
        processing_time = end_time - start_time
        assert processing_time < 0.01, f"Large payload processing took {processing_time:.4f}s, should be < 0.01s"
        
        # And should extract correctly
        assert result.username == "performance_user"
        assert result.success is True
        assert result.strategy_used == "follower.username"

    @pytest.mark.asyncio
    async def test_global_instance_usage(self):
        """
        Test that the global unified_extractor instance works correctly
        """
        # The global instance should be available and work the same way
        test_payload = {"follower": {"username": "global_test_user"}}
        
        # When: Using global instance
        result = unified_extractor.extract_username(test_payload, "follow")
        
        # Then: Should work identically to new instance
        assert result.username == "global_test_user"
        assert result.success is True
        assert result.strategy_used == "follower.username"

    @pytest.mark.asyncio
    async def test_backward_compatibility_wrapper(self):
        """
        Test that the backward compatibility wrapper continues to work
        """
        # Import the original function that now uses the unified system
        from oauth_webhook_server import extract_username_from_payload
        
        test_cases = [
            {"payload": {"follower": {"username": "compat_user1"}}, "event_type": "follow", "expected": "compat_user1"},
            {"payload": {"subscriber": {"username": "compat_user2"}}, "event_type": "subscription", "expected": "compat_user2"},
            {"payload": {"unknown": "data"}, "event_type": "follow", "expected": "Unknown"}
        ]
        
        for case in test_cases:
            # When: Using backward compatibility function
            result = extract_username_from_payload(case["payload"], case["event_type"])
            
            # Then: Should return just the username string (backward compatible)
            assert result == case["expected"]
            assert isinstance(result, str)  # Should return string, not ExtractionResult object

    @pytest.mark.asyncio
    async def test_strategy_extensibility_for_future_events(self):
        """
        Test that the system can be easily extended for future event types
        """
        extractor = UnifiedUsernameExtractor()
        
        # Simulate future event types that might be added
        future_event_types = [
            {
                "event_type": "channel_host",
                "strategy_name": "hoster.username",
                "strategy_func": lambda data: data.get('host_info', {}).get('hoster', {}).get('username'),
                "test_payload": {"host_info": {"hoster": {"username": "host_user"}}},
                "expected_username": "host_user"
            },
            {
                "event_type": "bits_donation",
                "strategy_name": "donor.username", 
                "strategy_func": lambda data: data.get('donation', {}).get('user', {}).get('username'),
                "test_payload": {"donation": {"user": {"username": "bits_donor"}, "amount": 1000}},
                "expected_username": "bits_donor"
            },
            {
                "event_type": "channel_ban",
                "strategy_name": "banned_user.username",
                "strategy_func": lambda data: data.get('banned_user', {}).get('username'),
                "test_payload": {"banned_user": {"username": "banned_user_123"}, "reason": "spam"},
                "expected_username": "banned_user_123"
            }
        ]
        
        for future_event in future_event_types:
            # Register the future event strategy
            extractor.register_strategy(
                future_event["event_type"],
                future_event["strategy_name"], 
                future_event["strategy_func"]
            )
            
            # When: Future event is processed
            result = extractor.extract_username(future_event["test_payload"], future_event["event_type"])
            
            # Then: Should work seamlessly
            assert result.username == future_event["expected_username"]
            assert result.success is True
            assert result.strategy_used == future_event["strategy_name"]
            assert result.event_type == future_event["event_type"]

if __name__ == "__main__":
    pytest.main([__file__])