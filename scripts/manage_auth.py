#!/usr/bin/env python3
"""
OAuth Token Management Script for KickBot

This script provides utilities for managing OAuth authentication tokens.

Usage:
    python scripts/manage_auth.py --help
    python scripts/manage_auth.py --clear-tokens
    python scripts/manage_auth.py --force-reauth
    python scripts/manage_auth.py --check-tokens
    python scripts/manage_auth.py --refresh-tokens
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv is optional
    pass

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from kickbot.kick_auth_manager import KickAuthManager, KickAuthManagerError

async def check_tokens():
    """Check the status of current OAuth tokens"""
    print("🔍 Checking OAuth token status...")
    
    token_file = Path('kickbot_tokens.json')
    if not token_file.exists():
        print("❌ No token file found")
        return False
    
    try:
        auth_manager = KickAuthManager()
        token = await auth_manager.get_valid_token()
        print(f"✅ Valid OAuth token found: {token[:20]}...")
        
        # Display token info
        if auth_manager.token_expires_at:
            import time
            expires_in = auth_manager.token_expires_at - time.time()
            if expires_in > 0:
                hours = int(expires_in // 3600)
                minutes = int((expires_in % 3600) // 60)
                print(f"⏰ Token expires in: {hours}h {minutes}m")
            else:
                print("⚠️  Token is expired")
        
        if auth_manager.granted_scopes:
            print(f"🔑 Granted scopes: {auth_manager.granted_scopes}")
        
        return True
        
    except KickAuthManagerError as e:
        print(f"❌ Token validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking tokens: {e}")
        return False

async def refresh_tokens():
    """Attempt to refresh OAuth tokens"""
    print("🔄 Attempting to refresh OAuth tokens...")
    
    try:
        auth_manager = KickAuthManager()
        
        if not auth_manager.refresh_token:
            print("❌ No refresh token available")
            return False
        
        await auth_manager.refresh_access_token()
        print("✅ Tokens refreshed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to refresh tokens: {e}")
        return False

def clear_tokens():
    """Clear all OAuth tokens and temporary files"""
    print("🗑️  Clearing OAuth tokens...")
    
    files_to_clear = [
        'kickbot_tokens.json',
        'oauth_verifier.txt', 
        'oauth_code.txt'
    ]
    
    cleared_count = 0
    for file_name in files_to_clear:
        file_path = Path(file_name)
        if file_path.exists():
            file_path.unlink()
            print(f"🗑️  Removed: {file_name}")
            cleared_count += 1
    
    if cleared_count == 0:
        print("ℹ️  No token files found to clear")
    else:
        print(f"✅ Cleared {cleared_count} authentication file(s)")
    
    return cleared_count > 0

async def force_reauth():
    """Force re-authentication by clearing tokens and starting OAuth flow"""
    print("🔄 Forcing re-authentication...")
    
    # Clear existing tokens
    clear_tokens()
    
    print("\n🔐 Starting OAuth authorization flow...")
    print("The bot will need to be re-authorized with your Kick account.")
    print("Run the bot normally and it will guide you through the OAuth process.")
    
    return True

async def main():
    parser = argparse.ArgumentParser(
        description='KickBot OAuth Token Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/manage_auth.py --check-tokens     # Check current token status
  python scripts/manage_auth.py --refresh-tokens   # Try to refresh expired tokens  
  python scripts/manage_auth.py --clear-tokens     # Remove all tokens
  python scripts/manage_auth.py --force-reauth     # Clear tokens and force re-auth
        """
    )
    
    parser.add_argument('--check-tokens', action='store_true',
                       help='Check the status of current OAuth tokens')
    parser.add_argument('--refresh-tokens', action='store_true',
                       help='Attempt to refresh OAuth tokens')
    parser.add_argument('--clear-tokens', action='store_true',
                       help='Clear all OAuth tokens and temporary files')
    parser.add_argument('--force-reauth', action='store_true',
                       help='Force re-authentication by clearing tokens')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    if args.check_tokens:
        await check_tokens()
    
    if args.refresh_tokens:
        await refresh_tokens()
    
    if args.clear_tokens:
        clear_tokens()
    
    if args.force_reauth:
        await force_reauth()

if __name__ == "__main__":
    asyncio.run(main())