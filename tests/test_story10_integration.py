#!/usr/bin/env python3
"""
Story 10: Integration Testing and Validation

Comprehensive end-to-end tests for the webhook-based KickBot system.
Tests all stories and validates the complete OAuth webhook migration.
"""

import asyncio
import json
import time
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration
WEBHOOK_URL = "http://localhost:8080"
TEST_TIMEOUT = 30

class WebhookIntegrationTester:
    """Comprehensive integration test suite for webhook-based KickBot"""
    
    def __init__(self):
        self.session = None
        self.test_results = {
            "oauth_tests": [],
            "command_tests": [],
            "webhook_tests": [],
            "performance_tests": [],
            "error_tests": []
        }
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    # =================== STORY 10 CORE TESTS ===================
    
    async def test_webhook_server_health(self):
        """Test 1: Verify webhook server is running and accessible"""
        print("🔍 Testing webhook server health...")
        
        try:
            async with self.session.get(f"{WEBHOOK_URL}/health", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Webhook server healthy: {data.get('service', 'Unknown')}")
                    self.test_results["webhook_tests"].append({
                        "test": "server_health",
                        "status": "PASS",
                        "response_time": time.time()
                    })
                    return True
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Webhook server not accessible: {e}")
            self.test_results["webhook_tests"].append({
                "test": "server_health", 
                "status": "FAIL",
                "error": str(e)
            })
            return False

    async def test_complete_webhook_flow(self):
        """Test 2: End-to-end webhook event processing"""
        print("🔍 Testing complete webhook flow...")
        
        # Simulate a chat.message.sent webhook event (flat format for unified webhook server)
        test_event = {
            "message_id": f"msg_{int(time.time())}",
            "content": "!b",  # Test MarkovChain command
            "created_at": datetime.utcnow().isoformat() + "Z",
            "sender": {
                "user_id": 999999,
                "username": "test_user",
                "channel_slug": "test_user",
                "identity": {
                    "username_color": "#FF0000",
                    "badges": []
                }
            },
            "broadcaster": {
                "user_id": 1139843,
                "username": "eddieoz",
                "channel_slug": "eddieoz",
                "identity": None
            }
        }
        
        try:
            start_time = time.time()
            async with self.session.post(
                f"{WEBHOOK_URL}/events",
                json=test_event,
                headers={
                    "Content-Type": "application/json",
                    "Kick-Event-Type": "chat.message.sent", 
                    "Kick-Event-Version": "1"
                }
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    print(f"✅ Webhook event processed successfully ({response_time:.3f}s)")
                    self.test_results["webhook_tests"].append({
                        "test": "complete_flow",
                        "status": "PASS", 
                        "response_time": response_time,
                        "event_type": "chat.message.sent"
                    })
                    return True
                else:
                    print(f"❌ Webhook processing failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Webhook flow test failed: {e}")
            self.test_results["webhook_tests"].append({
                "test": "complete_flow",
                "status": "FAIL",
                "error": str(e)
            })
            return False

    # =================== COMMAND TESTING (Story 8 included) ===================
    
    async def test_all_commands(self):
        """Test 3: All existing commands work via webhooks"""
        print("🔍 Testing all bot commands via webhooks...")
        
        # Complete list of commands from botoshi.py
        commands_to_test = [
            # Core commands
            "!following", "!leaders", "!joke", "!time", "!github", "!b",
            "!repete", "!repeat",
            
            # Sound alert commands (Story 8)
            "!sons", "!aplauso", "!burro", "!creptomoeda", "!no", "!nani",
            "!rica", "!run", "!secnagem", "!tistreza", "!zero", "!what",
            "!msg", "!doida", "!risada", "!vergonha", "!certo", "!triste",
            "!inveja", "!didi", "!elon", "!safado", "!viagem", "!laele", "!chato"
        ]
        
        successful_commands = 0
        total_response_time = 0
        
        for command in commands_to_test:
            success, response_time = await self._test_single_command(command)
            if success:
                successful_commands += 1
                total_response_time += response_time
                
        success_rate = (successful_commands / len(commands_to_test)) * 100
        avg_response_time = total_response_time / successful_commands if successful_commands > 0 else 0
        
        print(f"📊 Command Test Results:")
        print(f"   ✅ Success Rate: {success_rate:.1f}% ({successful_commands}/{len(commands_to_test)})")
        print(f"   ⚡ Average Response Time: {avg_response_time:.3f}s")
        
        self.test_results["command_tests"].append({
            "total_commands": len(commands_to_test),
            "successful": successful_commands,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time
        })
        
        return success_rate >= 90  # 90% success rate required

    async def _test_single_command(self, command: str):
        """Test a single command via webhook"""
        test_event = {
            "message_id": f"msg_{command}_{int(time.time())}",
            "content": command,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "sender": {
                "user_id": 999999,
                "username": "test_user",
                "channel_slug": "test_user",
                "identity": {"username_color": "#FF0000", "badges": []}
            },
            "broadcaster": {
                "user_id": 1139843,
                "username": "eddieoz", 
                "channel_slug": "eddieoz",
                "identity": None
            }
        }
        
        try:
            start_time = time.time()
            async with self.session.post(
                f"{WEBHOOK_URL}/events",
                json=test_event,
                headers={
                    "Content-Type": "application/json",
                    "Kick-Event-Type": "chat.message.sent", 
                    "Kick-Event-Version": "1"
                }
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    print(f"   ✅ {command} ({response_time:.3f}s)")
                    return True, response_time
                else:
                    print(f"   ❌ {command} failed ({response.status})")
                    return False, 0
                    
        except Exception as e:
            print(f"   ❌ {command} error: {e}")
            return False, 0

    # =================== PERFORMANCE TESTING ===================
    
    async def test_performance_requirements(self):
        """Test 4: Performance meets requirements (< 1s latency)"""
        print("🔍 Testing performance requirements...")
        
        # Test multiple rapid commands to check performance under load
        test_commands = ["!time", "!github", "!joke", "!b"]
        response_times = []
        
        print("   📊 Running performance test with rapid commands...")
        
        for i in range(10):  # 10 rapid tests
            for command in test_commands:
                start_time = time.time()
                success, response_time = await self._test_single_command(command)
                if success:
                    response_times.append(response_time)
                    
                # Small delay to avoid overwhelming
                await asyncio.sleep(0.1)
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            print(f"   📈 Performance Results:")
            print(f"      Average: {avg_time:.3f}s")
            print(f"      Maximum: {max_time:.3f}s") 
            print(f"      Minimum: {min_time:.3f}s")
            
            # Check if meets requirement (< 1s)
            meets_requirement = max_time < 1.0
            status = "✅ PASS" if meets_requirement else "❌ FAIL"
            print(f"   {status} Latency requirement (< 1s): {meets_requirement}")
            
            self.test_results["performance_tests"].append({
                "avg_response_time": avg_time,
                "max_response_time": max_time,
                "min_response_time": min_time,
                "meets_requirement": meets_requirement,
                "total_tests": len(response_times)
            })
            
            return meets_requirement
        else:
            print("   ❌ No successful responses for performance testing")
            return False

    # =================== ERROR SCENARIO TESTING ===================
    
    async def test_webhook_resilience(self):
        """Test 5: Webhook server handles invalid payloads gracefully"""
        print("🔍 Testing webhook server resilience...")
        
        test_scenarios = [
            {"name": "Invalid JSON", "payload": "invalid json"},
            {"name": "Empty payload", "payload": {}},
            {"name": "Missing event field", "payload": {"data": {}}},
            {"name": "Invalid event type", "payload": {"event": "invalid.event"}},
            {"name": "Malformed chat message", "payload": {
                "event": "chat.message.sent",
                "data": {"invalid": "structure"}
            }}
        ]
        
        resilience_passed = 0
        
        for scenario in test_scenarios:
            try:
                async with self.session.post(
                    f"{WEBHOOK_URL}/events",
                    json=scenario["payload"] if isinstance(scenario["payload"], dict) else None,
                    data=scenario["payload"] if isinstance(scenario["payload"], str) else None,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    # Server should return 200 even for invalid payloads (graceful handling)
                    if response.status == 200:
                        print(f"   ✅ {scenario['name']}: Handled gracefully")
                        resilience_passed += 1
                    else:
                        print(f"   ⚠️  {scenario['name']}: Status {response.status}")
                        
            except Exception as e:
                print(f"   ❌ {scenario['name']}: Exception {e}")
        
        resilience_rate = (resilience_passed / len(test_scenarios)) * 100
        print(f"   📊 Resilience Rate: {resilience_rate:.1f}%")
        
        self.test_results["error_tests"].append({
            "scenarios_tested": len(test_scenarios),
            "passed": resilience_passed,
            "resilience_rate": resilience_rate
        })
        
        return resilience_rate >= 80  # 80% resilience required

    # =================== OAUTH TESTING ===================
    
    async def test_oauth_endpoints(self):
        """Test 6: OAuth callback endpoint accessibility"""
        print("🔍 Testing OAuth endpoints...")
        
        try:
            # Test OAuth callback endpoint (should return method not allowed for GET)
            async with self.session.get(f"{WEBHOOK_URL}/callback") as response:
                # Expect 405 Method Not Allowed for GET request
                if response.status in [405, 200]:
                    print("   ✅ OAuth callback endpoint accessible")
                    return True
                else:
                    print(f"   ❌ OAuth callback unexpected status: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ OAuth endpoint test failed: {e}")
            return False

    # =================== TEST RUNNER ===================
    
    async def run_comprehensive_tests(self):
        """Run all integration tests for Story 10"""
        print("🚀 Starting Story 10: Integration Testing and Validation")
        print("=" * 60)
        
        test_results = {}
        
        # Core webhook tests
        test_results["webhook_health"] = await self.test_webhook_server_health()
        test_results["webhook_flow"] = await self.test_complete_webhook_flow()
        test_results["oauth_endpoints"] = await self.test_oauth_endpoints()
        
        # Command testing (includes Story 8)
        test_results["all_commands"] = await self.test_all_commands()
        
        # Performance testing
        test_results["performance"] = await self.test_performance_requirements()
        
        # Error handling
        test_results["resilience"] = await self.test_webhook_resilience()
        
        # Calculate overall results
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        print("\n" + "=" * 60)
        print("📊 STORY 10 INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name.replace('_', ' ').title()}")
        
        print(f"\n🎯 Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        # Story 10 Definition of Done check
        story_complete = success_rate >= 90
        print(f"\n🏆 Story 10 Status: {'✅ COMPLETE' if story_complete else '❌ NEEDS WORK'}")
        
        if story_complete:
            print("\n🎉 Webhook-based KickBot system fully validated!")
            print("✅ Ready for production deployment")
        else:
            print("\n⚠️  Some tests failed. Review results and fix issues.")
        
        return story_complete, self.test_results


# =================== MAIN TEST EXECUTION ===================

async def main():
    """Main test execution function"""
    print("🔧 KickBot Integration Test Suite")
    print("Testing webhook-based OAuth system (Story 10)")
    print("This includes validation of Stories 7 & 8")
    print()
    
    async with WebhookIntegrationTester() as tester:
        success, detailed_results = await tester.run_comprehensive_tests()
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"test_results_story10_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "overall_success": success,
                "detailed_results": detailed_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit_code = 0 if success else 1
    sys.exit(exit_code)