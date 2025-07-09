#!/usr/bin/env python3
"""
Quick runner for Story 10 Integration Tests

This script runs comprehensive integration tests against the running KickBot
to validate the webhook-based OAuth system works end-to-end.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.test_story10_integration import main

if __name__ == "__main__":
    print("🚀 KickBot Story 10: Integration Testing and Validation")
    print("=" * 60)
    print("Prerequisites:")
    print("✅ Bot should be running with webhook server on port 8080")
    print("✅ OAuth authentication should be working") 
    print("✅ Docker container should be up and healthy")
    print()
    
    # Check if user wants to proceed
    response = input("Ready to start integration tests? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Tests cancelled.")
        sys.exit(0)
    
    print("\n🔍 Starting comprehensive integration tests...")
    print("This will test all Stories 1-8 functionality via Story 10")
    print()
    
    try:
        success = asyncio.run(main())
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 SUCCESS: All integration tests passed!")
            print("🏆 KickBot OAuth Webhook Migration COMPLETE")
            print("✅ Ready for production deployment")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ FAILURE: Some integration tests failed")
            print("⚠️  Review test results and fix issues before deployment")
            print("=" * 60)
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        sys.exit(1)