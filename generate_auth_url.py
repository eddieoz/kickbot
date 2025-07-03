#!/usr/bin/env python3
"""
Generate OAuth authorization URL for KickBot and store the code verifier
This should be run before starting the OAuth flow
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the current directory BEFORE importing KickAuthManager
env_path = Path('.env')
load_dotenv(env_path)

from kickbot.kick_auth_manager import KickAuthManager

def main():
    print("🚀 KickBot OAuth URL Generator")
    print("=" * 60)
    
    try:
        # Create auth manager
        auth_manager = KickAuthManager()
        
        # Check if we already have valid tokens
        if auth_manager.access_token and auth_manager.is_access_token_valid():
            print("✅ You already have valid OAuth tokens!")
            print("The bot should work with OAuth authentication.")
            return
        
        # Generate authorization URL
        print("🔗 Generating authorization URL...")
        auth_url, code_verifier = auth_manager.get_authorization_url()
        
        # Store the code verifier for the webhook server to use
        with open('oauth_verifier.txt', 'w') as f:
            f.write(code_verifier)
        print("🔐 Code verifier stored for webhook server")
        
        print("\n📋 OAUTH AUTHORIZATION INSTRUCTIONS")
        print("=" * 60)
        print("1. Make sure the Docker container is running:")
        print("   docker-compose up -d")
        print("\n2. Open the following URL in your browser:")
        print(f"   {auth_url}")
        print("\n3. Sign in to Kick.com and authorize the application")
        print("4. You will be redirected to:")
        print("   https://webhook.botoshi.sats4.life/callback?code=...")
        print("5. The webhook server will automatically exchange the code for tokens")
        print("\n✅ Setup complete! The authorization URL is ready.")
        print("   The webhook server will handle the rest automatically.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())