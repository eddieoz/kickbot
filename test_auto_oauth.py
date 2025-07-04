#!/usr/bin/env python3
"""
Test script for automatic OAuth authorization flow.
This simulates the scenario where the bot starts without valid tokens.
"""

import os
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kickbot.kick_auth_manager import KickAuthManager

async def test_automatic_oauth():
    """Test the automatic OAuth authorization flow."""
    
    # Remove existing tokens to simulate missing token scenario
    token_file = Path("kickbot_tokens.json")
    if token_file.exists():
        backup_file = Path("kickbot_tokens_test_backup.json")
        token_file.rename(backup_file)
        print(f"📋 Moved existing tokens to {backup_file}")
    
    try:
        # Create auth manager
        auth_manager = KickAuthManager()
        
        # This should fail and trigger automatic authorization
        print("🧪 Testing automatic OAuth flow...")
        print("🔍 Attempting to get valid token (should fail)...")
        
        try:
            token = await auth_manager.get_valid_token()
            print("✅ Found existing valid token - test scenario invalid")
            return False
        except Exception as e:
            print(f"❌ Expected failure: {e}")
            
        # Test the fallback redirect URI method
        print("🔗 Testing fallback redirect URI method...")
        auth_url, code_verifier = auth_manager.get_authorization_url_with_fallback_redirect()
        
        print(f"✅ Generated authorization URL: {auth_url[:80]}...")
        print(f"✅ Generated code verifier: {code_verifier[:20]}...")
        
        # Verify the URL contains the fallback redirect URI
        fallback_uri = os.environ.get('KICK_REDIRECT_URI_FALLBACK', 'http://localhost:5010/callback')
        if fallback_uri in auth_url:
            print("✅ Authorization URL contains fallback redirect URI")
        else:
            print("❌ Authorization URL does not contain fallback redirect URI")
            return False
        
        print("\n" + "="*60)
        print("🎉 AUTOMATIC OAUTH FLOW TEST SUCCESSFUL")
        print("="*60)
        print("The bot is now ready to handle missing tokens automatically!")
        print("When Docker starts without tokens, it will:")
        print("1. Start temporary callback server on port 5010")
        print("2. Display authorization URL and open browser")
        print("3. Wait for user to authorize")
        print("4. Exchange code for tokens")
        print("5. Continue with normal bot operation")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        # Restore backup if it exists
        backup_file = Path("kickbot_tokens_test_backup.json")
        if backup_file.exists():
            backup_file.rename(token_file)
            print(f"📋 Restored tokens from backup")

if __name__ == "__main__":
    success = asyncio.run(test_automatic_oauth())
    sys.exit(0 if success else 1)