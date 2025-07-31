"""
Performance benchmark tests for webhook processing (Story 21)
Comprehensive performance testing to ensure webhook processing meets acceptable thresholds
"""

import pytest
import asyncio
import time
import statistics
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import oauth_webhook_server


class MockMinimalBot:
    """Minimal mock bot for performance testing"""
    
    def __init__(self):
        self.logger = MagicMock()
        self.auth_manager = MagicMock()
        
    async def _handle_gifted_subscriptions(self, gifter: str, amount: int) -> None:
        """Minimal mock implementation for performance testing"""
        pass  # Do nothing for performance tests


class TestPerformanceBenchmarks:
    """Performance benchmark tests for webhook processing"""

    def setup_method(self):
        """Setup performance test fixtures"""
        self.mock_bot = MockMinimalBot()
        self.mock_alert_function = AsyncMock()
        
        # Store original bot instance
        self.original_bot_instance = oauth_webhook_server.bot_instance
        oauth_webhook_server.bot_instance = self.mock_bot
        
        # Disable alerts for performance testing
        self.original_settings = getattr(oauth_webhook_server, 'settings', {})
        oauth_webhook_server.settings = {'Alerts': {'Enable': False}}
        
    def teardown_method(self):
        """Clean up performance test fixtures"""
        oauth_webhook_server.bot_instance = self.original_bot_instance
        oauth_webhook_server.settings = self.original_settings

    @pytest.mark.asyncio
    async def test_single_webhook_processing_benchmark(self):
        """
        Benchmark single webhook processing times
        
        Requirement: Single webhook should process in < 0.1s
        """
        test_payloads = [
            {
                "name": "Follow Event",
                "handler": oauth_webhook_server.handle_follow_event,
                "payload": {"follower": {"username": "benchmark_follower"}}
            },
            {
                "name": "Subscription Event",
                "handler": oauth_webhook_server.handle_subscription_event,
                "payload": {"subscriber": {"username": "benchmark_subscriber"}, "tier": 2}
            },
            {
                "name": "Gift Subscription Event",
                "handler": oauth_webhook_server.handle_gift_subscription_event,
                "payload": {"gifter": {"username": "benchmark_gifter"}, "quantity": 3}
            }
        ]
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            for test_case in test_payloads:
                # Warm up (first call may be slower due to imports/initialization)
                await test_case["handler"](test_case["payload"])
                
                # Benchmark multiple runs
                times = []
                for _ in range(10):
                    start_time = time.perf_counter()
                    await test_case["handler"](test_case["payload"])
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)
                
                # Analyze performance
                avg_time = statistics.mean(times)
                max_time = max(times)
                min_time = min(times)
                
                print(f"\n{test_case['name']} Performance:")
                print(f"  Average: {avg_time:.4f}s")
                print(f"  Min: {min_time:.4f}s")
                print(f"  Max: {max_time:.4f}s")
                
                # Assert performance requirements
                assert avg_time < 0.1, f"{test_case['name']} average time {avg_time:.4f}s exceeds 0.1s threshold"
                assert max_time < 0.2, f"{test_case['name']} max time {max_time:.4f}s exceeds 0.2s threshold"

    @pytest.mark.asyncio
    async def test_concurrent_webhook_processing_benchmark(self):
        """
        Benchmark concurrent webhook processing
        
        Requirement: System should handle 100 concurrent webhooks in < 5s
        """
        # Create 100 concurrent webhook events
        concurrent_events = []
        for i in range(100):
            event_type = i % 3
            if event_type == 0:
                concurrent_events.append({
                    "handler": oauth_webhook_server.handle_follow_event,
                    "payload": {"follower": {"username": f"concurrent_follower_{i}"}}
                })
            elif event_type == 1:
                concurrent_events.append({
                    "handler": oauth_webhook_server.handle_subscription_event,
                    "payload": {"subscriber": {"username": f"concurrent_subscriber_{i}"}, "tier": (i % 3) + 1}
                })
            else:
                concurrent_events.append({
                    "handler": oauth_webhook_server.handle_gift_subscription_event,
                    "payload": {"gifter": {"username": f"concurrent_gifter_{i}"}, "quantity": (i % 5) + 1}
                })
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # Benchmark concurrent processing
            start_time = time.perf_counter()
            tasks = [event["handler"](event["payload"]) for event in concurrent_events]
            await asyncio.gather(*tasks)
            end_time = time.perf_counter()
            
            total_time = end_time - start_time
            throughput = len(concurrent_events) / total_time
            
            print(f"\nConcurrent Processing Benchmark:")
            print(f"  Events: {len(concurrent_events)}")
            print(f"  Total time: {total_time:.3f}s")
            print(f"  Throughput: {throughput:.1f} events/second")
            print(f"  Average per event: {total_time/len(concurrent_events):.4f}s")
            
            # Assert performance requirements
            assert total_time < 5.0, f"Concurrent processing took {total_time:.3f}s, should be < 5.0s"
            assert throughput > 20, f"Throughput {throughput:.1f} events/s is below minimum 20 events/s"

    @pytest.mark.asyncio
    async def test_large_payload_processing_benchmark(self):
        """
        Benchmark processing of large webhook payloads
        
        Requirement: Large payloads should process in < 0.2s
        """
        # Create very large realistic payloads
        large_payloads = [
            {
                "name": "Large Follow Payload",
                "handler": oauth_webhook_server.handle_follow_event,
                "payload": {
                    "follower": {
                        "username": "large_payload_follower",
                        "id": 999999,
                        "bio": "A" * 10000,  # 10KB bio
                        "followers": [f"follower_{i}" for i in range(1000)],  # Large array
                        "metadata": {f"key_{i}": f"value_{i}" * 100 for i in range(100)}  # Large dict
                    },
                    "additional_data": ["item_" * 100 for _ in range(500)]  # More large data
                }
            },
            {
                "name": "Large Gift Subscription Payload",
                "handler": oauth_webhook_server.handle_gift_subscription_event,
                "payload": {
                    "gifter": {
                        "username": "large_payload_gifter",
                        "profile": {
                            "description": "B" * 5000,  # 5KB description
                            "streaming_history": [
                                {"date": f"2024-01-{i:02d}", "hours": 8, "viewers": list(range(100))}
                                for i in range(1, 32)  # Month of streaming data
                            ]
                        }
                    },
                    "quantity": 10,
                    "recipients": [
                        {"username": f"recipient_{i}", "profile": {"data": "C" * 100}}
                        for i in range(100)  # 100 recipients with data
                    ]
                }
            }
        ]
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            for test_case in large_payloads:
                # Warm up
                await test_case["handler"](test_case["payload"])
                
                # Benchmark multiple runs with large payloads
                times = []
                for _ in range(5):  # Fewer runs due to large payload size
                    start_time = time.perf_counter()
                    await test_case["handler"](test_case["payload"])
                    end_time = time.perf_counter()
                    times.append(end_time - start_time)
                
                avg_time = statistics.mean(times)
                max_time = max(times)
                payload_size = len(str(test_case["payload"]))
                
                print(f"\n{test_case['name']} Performance:")
                print(f"  Payload size: {payload_size:,} characters")
                print(f"  Average time: {avg_time:.4f}s")
                print(f"  Max time: {max_time:.4f}s")
                
                # Assert performance requirements for large payloads
                assert avg_time < 0.2, f"{test_case['name']} average time {avg_time:.4f}s exceeds 0.2s threshold"
                assert max_time < 0.5, f"{test_case['name']} max time {max_time:.4f}s exceeds 0.5s threshold"

    @pytest.mark.asyncio
    async def test_username_extraction_performance_benchmark(self):
        """
        Benchmark username extraction performance with unified extractor
        
        Requirement: Username extraction should be < 0.001s per call
        """
        from oauth_webhook_server import unified_extractor
        
        test_payloads = [
            {"follower": {"username": "perf_test_user_1"}},
            {"user": {"username": "perf_test_user_2"}},
            {"username": "perf_test_user_3"},
            {"subscriber": {"username": "perf_test_user_4"}},
            {"gifter": {"username": "perf_test_user_5"}},
            # Complex nested payload
            {
                "data": {
                    "user_info": {
                        "follower": {
                            "username": "perf_test_nested_user",
                            "complex_data": {f"field_{i}": f"value_{i}" for i in range(100)}
                        }
                    }
                }
            }
        ]
        
        event_types = ["follow", "subscription", "gift_subscription"]
        
        # Benchmark username extraction
        extraction_times = []
        
        for _ in range(1000):  # Many iterations for accurate timing
            for payload in test_payloads:
                for event_type in event_types:
                    start_time = time.perf_counter()
                    result = unified_extractor.extract_username(payload, event_type)
                    end_time = time.perf_counter()
                    extraction_times.append(end_time - start_time)
        
        avg_extraction_time = statistics.mean(extraction_times)
        max_extraction_time = max(extraction_times)
        
        print(f"\nUsername Extraction Performance:")
        print(f"  Total extractions: {len(extraction_times)}")
        print(f"  Average time: {avg_extraction_time:.6f}s")
        print(f"  Max time: {max_extraction_time:.6f}s")
        print(f"  Throughput: {len(extraction_times)/sum(extraction_times):.0f} extractions/second")
        
        # Assert performance requirements
        assert avg_extraction_time < 0.001, f"Username extraction average time {avg_extraction_time:.6f}s exceeds 0.001s"
        assert max_extraction_time < 0.01, f"Username extraction max time {max_extraction_time:.6f}s exceeds 0.01s"

    @pytest.mark.asyncio
    async def test_memory_usage_benchmark(self):
        """
        Benchmark memory usage during webhook processing
        
        Requirement: Memory usage should remain stable during processing
        """
        import gc
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        
        # Measure baseline memory
        gc.collect()  # Clean up before measurement
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process many webhooks
        webhook_events = []
        for i in range(1000):
            webhook_events.extend([
                {
                    "handler": oauth_webhook_server.handle_follow_event,
                    "payload": {"follower": {"username": f"memory_test_follower_{i}"}}
                },
                {
                    "handler": oauth_webhook_server.handle_subscription_event,
                    "payload": {"subscriber": {"username": f"memory_test_subscriber_{i}"}, "tier": 1}
                },
                {
                    "handler": oauth_webhook_server.handle_gift_subscription_event,
                    "payload": {"gifter": {"username": f"memory_test_gifter_{i}"}, "quantity": 1}
                }
            ])
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # Process events in batches
            batch_size = 100
            memory_measurements = []
            
            for i in range(0, len(webhook_events), batch_size):
                batch = webhook_events[i:i + batch_size]
                tasks = [event["handler"](event["payload"]) for event in batch]
                await asyncio.gather(*tasks)
                
                # Measure memory after each batch
                gc.collect()
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_measurements.append(current_memory)
        
        final_memory = memory_measurements[-1]
        memory_increase = final_memory - baseline_memory
        max_memory = max(memory_measurements)
        
        print(f"\nMemory Usage Benchmark:")
        print(f"  Baseline memory: {baseline_memory:.1f} MB")
        print(f"  Final memory: {final_memory:.1f} MB")
        print(f"  Memory increase: {memory_increase:.1f} MB")
        print(f"  Peak memory: {max_memory:.1f} MB")
        print(f"  Events processed: {len(webhook_events)}")
        
        # Assert memory requirements
        assert memory_increase < 50, f"Memory increased by {memory_increase:.1f} MB, should be < 50 MB"
        assert max_memory < baseline_memory + 100, f"Peak memory {max_memory:.1f} MB exceeds baseline + 100 MB"

    @pytest.mark.asyncio
    async def test_error_handling_performance_impact(self):
        """
        Benchmark performance impact of error handling
        
        Requirement: Error handling should not significantly impact performance
        """
        # Test normal processing time
        normal_payload = {"follower": {"username": "normal_user"}}
        
        with patch('oauth_webhook_server.send_alert', new=self.mock_alert_function):
            # Benchmark normal processing
            normal_times = []
            for _ in range(100):
                start_time = time.perf_counter()
                await oauth_webhook_server.handle_follow_event(normal_payload)
                end_time = time.perf_counter()
                normal_times.append(end_time - start_time)
            
            # Benchmark error processing
            error_payloads = [
                {},  # Empty payload
                {"invalid": "structure"},  # Invalid structure
                {"follower": {"username": None}},  # None username
            ]
            
            error_times = []
            for error_payload in error_payloads:
                for _ in range(30):  # Fewer iterations for error cases
                    start_time = time.perf_counter()
                    await oauth_webhook_server.handle_follow_event(error_payload)
                    end_time = time.perf_counter()
                    error_times.append(end_time - start_time)
        
        avg_normal_time = statistics.mean(normal_times)
        avg_error_time = statistics.mean(error_times)
        performance_impact = (avg_error_time - avg_normal_time) / avg_normal_time * 100
        
        print(f"\nError Handling Performance Impact:")
        print(f"  Normal processing: {avg_normal_time:.4f}s")
        print(f"  Error processing: {avg_error_time:.4f}s")
        print(f"  Performance impact: {performance_impact:.1f}%")
        
        # Assert that error handling doesn't significantly impact performance
        assert performance_impact < 100, f"Error handling adds {performance_impact:.1f}% overhead, should be < 100%"
        assert avg_error_time < 0.2, f"Error processing time {avg_error_time:.4f}s is too slow"

if __name__ == "__main__":
    pytest.main([__file__])