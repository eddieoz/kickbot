#!/usr/bin/env python3
"""
OAuth setup script for KickBot
This script helps you authorize the bot with Kick.com using OAuth 2.0
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the current directory BEFORE importing KickAuthManager
env_path = Path('.env')
load_dotenv(env_path)

from kickbot.kick_auth_manager import KickAuthManager

async def main():
    """Main OAuth setup function"""
    print("🚀 KickBot OAuth Setup")
    print("=" * 50)
    
    # Check if required environment variables are set
    required_vars = ['KICK_CLIENT_ID', 'KICK_CLIENT_SECRET', 'KICK_REDIRECT_URI']
    missing_vars = []
    
    print("🔍 Debug: Environment variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   {var}: {value[:8]}***")
        else:
            print(f"   {var}: NOT SET")
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file:")
        print("KICK_CLIENT_ID=your_client_id")
        print("KICK_CLIENT_SECRET=your_client_secret")
        print("KICK_REDIRECT_URI=http://localhost:8080/callback")
        print("KICK_SCOPES=chatroom:read user:read channel:read events:subscribe")
        return
    
    try:
        # Initialize the auth manager
        auth_manager = KickAuthManager()
        
        # Check if we already have valid tokens
        if auth_manager.is_access_token_valid():
            print("✅ You already have valid OAuth tokens!")
            print("The bot should work with OAuth authentication.")
            return
        
        # If we have a refresh token, try to refresh
        if auth_manager.refresh_token:
            print("🔄 Attempting to refresh existing token...")
            try:
                await auth_manager.refresh_access_token()
                print("✅ Token refreshed successfully!")
                print("The bot should work with OAuth authentication.")
                return
            except Exception as e:
                print(f"❌ Token refresh failed: {e}")
                print("Proceeding with new authorization...")
        
        # Generate authorization URL
        print("🔗 Generating authorization URL...")
        auth_url, code_verifier = auth_manager.get_authorization_url()
        
        print("\n📋 AUTHORIZATION REQUIRED")
        print("=" * 50)
        print("1. Open the following URL in your browser:")
        print(f"   {auth_url}")
        print("\n2. Sign in to Kick.com and authorize the application")
        print("3. You will be redirected to your redirect URI with a 'code' parameter")
        print("4. Copy the 'code' value from the URL")
        print("\nExample: If redirected to 'http://localhost:8080/callback?code=ABC123&state=...'")
        print("Then your code is: ABC123")
        
        # Get the authorization code from user
        print("\n" + "=" * 50)
        code = input("Enter the authorization code: ").strip()
        
        if not code:
            print("❌ No code provided. Exiting.")
            return
        
        # Exchange code for tokens
        print("🔄 Exchanging code for tokens...")
        try:
            result = await auth_manager.exchange_code_for_tokens(code, code_verifier)
            print("✅ OAuth setup completed successfully!")
            print(f"Access token expires in: {result.get('expires_in', 'unknown')} seconds")
            print("Tokens have been saved to kickbot_tokens.json")
            print("\nYou can now run the bot with OAuth authentication!")
            
        except Exception as e:
            print(f"❌ Failed to exchange code for tokens: {e}")
            return
    
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return

if __name__ == "__main__":
    asyncio.run(main())