"""
Test suite for Unified Username Extraction Utility (Story 20)
BDD scenarios testing a centralized, extensible username extraction system
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import oauth_webhook_server


class TestUnifiedUsernameExtractionUtility:
    """Test unified username extraction utility with extensible strategy pattern"""

    def setup_method(self):
        """Setup test fixtures"""
        pass

    @pytest.mark.asyncio
    async def test_scenario_20_1_username_extraction_with_multiple_strategies(self):
        """
        BDD Scenario 20.1: Username Extraction with Multiple Strategies
        
        Given a webhook payload is received
        And username extraction strategies are defined for the event type
        When extract_username_from_payload is called
        Then it should try strategies in order until one succeeds
        And return the first successful username found
        And log the successful strategy used
        """
        # This test expects an enhanced utility class, not the current function
        from oauth_webhook_server import UnifiedUsernameExtractor
        
        extractor = UnifiedUsernameExtractor()
        
        # Test payloads that should work with different strategies
        test_cases = [
            # Standard structure should work with first strategy
            {
                "payload": {"follower": {"username": "strategy1user"}},
                "event_type": "follow",
                "expected_username": "strategy1user",
                "expected_strategy": "follower.username"
            },
            # Alternative structure should work with second strategy
            {
                "payload": {"user": {"username": "strategy2user"}},
                "event_type": "follow", 
                "expected_username": "strategy2user",
                "expected_strategy": "user.username"
            },
            # Direct field should work with third strategy
            {
                "payload": {"username": "strategy3user"},
                "event_type": "follow",
                "expected_username": "strategy3user", 
                "expected_strategy": "username"
            }
        ]
        
        for case in test_cases:
            with patch('oauth_webhook_server.logger') as mock_logger:
                # When: Username extraction is called
                result = extractor.extract_username(case["payload"], case["event_type"])
                
                # Then: Should return expected username
                assert result.username == case["expected_username"]
                assert result.strategy_used == case["expected_strategy"]
                assert result.success is True
                
                # And log the successful strategy
                mock_logger.debug.assert_called()
                debug_call = mock_logger.debug.call_args[0][0]
                assert case["expected_strategy"] in debug_call

    @pytest.mark.asyncio
    async def test_scenario_20_2_username_extraction_fallback_handling(self):
        """
        BDD Scenario 20.2: Username Extraction Fallback Handling
        
        Given a webhook payload is received
        And all username extraction strategies fail
        When extract_username_from_payload is called
        Then it should return "Unknown"
        And log a warning about extraction failure
        And include payload structure in debug logs
        """
        from oauth_webhook_server import UnifiedUsernameExtractor
        
        extractor = UnifiedUsernameExtractor()
        
        # Payload that should fail all strategies
        failing_payload = {
            "some_other_field": "value",
            "nested": {
                "data": "no username here"
            }
        }
        
        with patch('oauth_webhook_server.logger') as mock_logger:
            # When: Username extraction is called with failing payload
            result = extractor.extract_username(failing_payload, "follow")
            
            # Then: Should return Unknown result
            assert result.username == "Unknown"
            assert result.success is False
            assert result.strategy_used is None
            
            # And log warning about extraction failure
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Failed to extract username" in warning_call
            assert "follow" in warning_call

    @pytest.mark.asyncio
    async def test_scenario_20_3_event_type_specific_extraction(self):
        """
        BDD Scenario 20.3: Event Type Specific Extraction
        
        Given different event types are processed
        When extract_username_from_payload is called with event_type parameter
        Then it should use event-specific extraction strategies
        And follow event should check ["follower.username", "user.username", "username"]
        And subscription event should check ["subscriber.username", "user.username", "username"]  
        And gift event should use existing parser logic
        """
        from oauth_webhook_server import UnifiedUsernameExtractor
        
        extractor = UnifiedUsernameExtractor()
        
        # Test that different event types use different strategies
        event_specific_tests = [
            {
                "event_type": "follow",
                "payload": {"follower": {"username": "follower_user"}},
                "expected_username": "follower_user",
                "expected_strategy": "follower.username"
            },
            {
                "event_type": "subscription",
                "payload": {"subscriber": {"username": "subscriber_user"}},
                "expected_username": "subscriber_user", 
                "expected_strategy": "subscriber.username"
            },
            {
                "event_type": "gift_subscription",
                "payload": {"gifter": {"username": "gifter_user"}},
                "expected_username": "gifter_user",
                "expected_strategy": "gifter.username"
            }
        ]
        
        for test in event_specific_tests:
            # When: Event-specific extraction is called
            result = extractor.extract_username(test["payload"], test["event_type"])
            
            # Then: Should use event-specific strategy
            assert result.username == test["expected_username"]
            assert result.strategy_used == test["expected_strategy"]
            assert result.success is True

    @pytest.mark.asyncio
    async def test_strategy_registration_and_extension(self):
        """
        Test that new strategies can be registered for different event types
        
        This tests the extensibility requirement of the unified utility
        """
        from oauth_webhook_server import UnifiedUsernameExtractor
        
        extractor = UnifiedUsernameExtractor()
        
        # Register a custom strategy for a new event type
        def custom_strategy(payload):
            return payload.get('custom_user', {}).get('name')
        
        extractor.register_strategy("custom_event", "custom_user.name", custom_strategy)
        
        # Test the custom strategy
        custom_payload = {
            "custom_user": {
                "name": "custom_username",
                "id": 12345
            }
        }
        
        # When: Custom event extraction is called
        result = extractor.extract_username(custom_payload, "custom_event")
        
        # Then: Should use the registered custom strategy
        assert result.username == "custom_username"
        assert result.strategy_used == "custom_user.name"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_strategy_priority_ordering(self):
        """
        Test that strategies are tried in the correct priority order
        
        This ensures that more specific strategies are tried before generic ones
        """
        from oauth_webhook_server import UnifiedUsernameExtractor
        
        extractor = UnifiedUsernameExtractor()
        
        # Payload with multiple possible username sources
        multi_source_payload = {
            "follower": {"username": "follower_name"},
            "user": {"username": "user_name"},
            "username": "direct_name"
        }
        
        # When: Follow event extraction is called
        result = extractor.extract_username(multi_source_payload, "follow")
        
        # Then: Should use the highest priority strategy (follower.username)
        assert result.username == "follower_name"
        assert result.strategy_used == "follower.username"

    @pytest.mark.asyncio
    async def test_username_validation_and_sanitization(self):
        """
        Test that extracted usernames are validated and sanitized
        
        This ensures that empty, whitespace-only, or invalid usernames are handled
        """
        from oauth_webhook_server import UnifiedUsernameExtractor
        
        extractor = UnifiedUsernameExtractor()
        
        validation_tests = [
            # Empty string should be rejected
            {"payload": {"username": ""}, "expected_username": "Unknown"},
            # Whitespace-only should be rejected  
            {"payload": {"username": "   "}, "expected_username": "Unknown"},
            # None should be rejected
            {"payload": {"username": None}, "expected_username": "Unknown"},
            # Valid username with whitespace should be preserved
            {"payload": {"username": "  valid_user  "}, "expected_username": "  valid_user  "},
            # Valid username should be preserved
            {"payload": {"username": "valid_user"}, "expected_username": "valid_user"}
        ]
        
        for test in validation_tests:
            result = extractor.extract_username(test["payload"], "follow")
            assert result.username == test["expected_username"]

    @pytest.mark.asyncio
    async def test_extraction_result_object(self):
        """
        Test that the extraction returns a comprehensive result object
        
        This tests the enhanced interface that provides more information than just the username
        """
        from oauth_webhook_server import UnifiedUsernameExtractor, ExtractionResult
        
        extractor = UnifiedUsernameExtractor()
        
        # Successful extraction
        success_payload = {"follower": {"username": "test_user"}}
        result = extractor.extract_username(success_payload, "follow")
        
        # Should be an ExtractionResult object
        assert isinstance(result, ExtractionResult)
        assert result.username == "test_user"
        assert result.success is True
        assert result.strategy_used == "follower.username"
        assert result.event_type == "follow"
        assert result.payload == success_payload
        
        # Failed extraction
        fail_payload = {"other": "data"}
        result = extractor.extract_username(fail_payload, "follow")
        
        assert isinstance(result, ExtractionResult)
        assert result.username == "Unknown"
        assert result.success is False
        assert result.strategy_used is None
        assert result.event_type == "follow"
        assert result.payload == fail_payload

    @pytest.mark.asyncio
    async def test_performance_with_many_strategies(self):
        """
        Test performance when many strategies are registered
        
        This ensures the utility can handle a large number of strategies efficiently
        """
        from oauth_webhook_server import UnifiedUsernameExtractor
        
        extractor = UnifiedUsernameExtractor()
        
        # Register many strategies (simulating future extensibility)
        for i in range(100):
            def make_strategy(index):
                return lambda payload: payload.get(f'field_{index}', {}).get('username')
            
            extractor.register_strategy("performance_test", f"field_{i}.username", make_strategy(i))
        
        # Test payload that will match the last strategy
        perf_payload = {"field_99": {"username": "performance_user"}}
        
        # When: Extraction is performed with many strategies
        start_time = asyncio.get_event_loop().time()
        result = extractor.extract_username(perf_payload, "performance_test")
        end_time = asyncio.get_event_loop().time()
        
        # Then: Should complete quickly even with many strategies
        processing_time = end_time - start_time
        assert processing_time < 0.1, f"Performance test took {processing_time:.3f}s, should be < 0.1s"
        
        # And should find the correct result
        assert result.username == "performance_user"
        assert result.strategy_used == "field_99.username"

    @pytest.mark.asyncio
    async def test_existing_handlers_integration(self):
        """
        Test that existing event handlers can use the unified utility
        
        This tests the integration requirement from the story
        """
        from oauth_webhook_server import UnifiedUsernameExtractor
        
        # This test will pass once the handlers are refactored to use the unified utility
        extractor = UnifiedUsernameExtractor()
        
        # Test follow event integration
        follow_payload = {"follower": {"username": "integrated_follower"}}
        result = extractor.extract_username(follow_payload, "follow")
        
        assert result.username == "integrated_follower"
        
        # Test subscription event integration  
        subscription_payload = {"subscriber": {"username": "integrated_subscriber"}}
        result = extractor.extract_username(subscription_payload, "subscription")
        
        assert result.username == "integrated_subscriber"

if __name__ == "__main__":
    pytest.main([__file__])