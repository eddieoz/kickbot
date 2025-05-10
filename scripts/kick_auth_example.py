#!/usr/bin/env python
"""
Example script demonstrating the KickAuthManager with token storage and refresh.

This script shows how to:
1. Check for existing tokens
2. Start an OAuth flow if no tokens exist
3. Exchange authorization code for tokens
4. Get a valid token (with automatic refresh if needed)
5. Use the token for API requests

Usage:
    python scripts/kick_auth_example.py

Requirements:
    - KICK_CLIENT_ID, KICK_REDIRECT_URI set in environment or .env file
    - A local webserver to receive the OAuth callback (implemented in this script)
"""

import os
from dotenv import load_dotenv
load_dotenv()
import sys
import asyncio
import argparse
import webbrowser
from aiohttp import web, ClientSession
from urllib.parse import parse_qs, urlparse
from pathlib import Path

# Add project root to PYTHONPATH if needed
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from kickbot.kick_auth_manager import KickAuthManager, KickAuthManagerError

# Global variables
auth_manager = None
code_verifier = None
auth_code = None
callback_received = asyncio.Event()

async def handle_oauth_callback(request):
    """Handle the OAuth callback from Kick"""
    global auth_code, callback_received
    
    # Extract code from query parameters
    params = request.rel_url.query
    if 'code' in params:
        auth_code = params['code']
        callback_received.set()
        return web.Response(text="Authorization successful! You can close this window.")
    else:
        error = params.get('error', 'Unknown error')
        error_description = params.get('error_description', 'No description provided')
        callback_received.set()  # Set event even on error
        return web.Response(text=f"Authorization failed: {error} - {error_description}", status=400)

async def start_callback_server(port=8081, path='/callback'):
    """Start a local web server to receive the OAuth callback"""
    app = web.Application()
    app.router.add_get(path, handle_oauth_callback)
    
    # Start the server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)  # Listen on all interfaces
    await site.start()
    
    print(f"Callback server started at http://0.0.0.0:{port}{path}")
    return runner

async def authorize(callback_port=8081):
    """Start the authorization flow"""
    global auth_manager, code_verifier, auth_code
    
    # Create auth manager
    auth_manager = KickAuthManager()
    
    # Check if we already have valid tokens
    try:
        token = await auth_manager.get_valid_token()
        print(f"Found valid token: {token[:10]}...")
        return
    except KickAuthManagerError:
        # No valid token, need to authorize
        print("No valid token found. Starting authorization flow.")
    
    # Get authorization URL and code verifier
    auth_url, code_verifier = auth_manager.get_authorization_url()
    
    # Manual Code Acquisition Flow
    print("\n--- Manual Authorization Required ---")
    print(f"1. Open this URL in your web browser:\n   {auth_url}")
    print("\n2. Log in to Kick and authorize the application.")
    print("3. Your browser will be redirected to a URL starting with 'https://localhost/callback?code=...'")
    print("   It might show a 'site can't be reached' error, but the URL in the address bar is important.")
    print("4. Copy the value of the 'code' parameter from the address bar.")
    
    auth_code_manual = input("5. Paste the authorization code here and press Enter: ").strip()

    if not auth_code_manual:
        print("No authorization code provided. Exiting.")
        return

    try:
        # Exchange code for tokens
        print("\nExchanging authorization code for tokens...")
        tokens = await auth_manager.exchange_code_for_tokens(auth_code_manual, code_verifier)
        print("Tokens received and stored successfully in kick_token.json!")
        # Access token is now stored in auth_manager and in the token file
        
    except Exception as e:
        print(f"Error exchanging code for tokens: {e}")
        print("Please ensure you copied the code correctly and that your client ID and redirect URI are correctly set up.")

async def test_api_request():
    """Test making an API request with the token"""
    global auth_manager
    
    if not auth_manager:
        auth_manager = KickAuthManager()
    
    try:
        # Get a valid token (will refresh if needed)
        token = await auth_manager.get_valid_token()
        print(f"Using token: {token[:10]}...")
        
        # Example API request
        api_url = "https://kick.com/api/v2/channels/self"
        
        async with ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"API request successful!")
                    print(f"Channel info: {data}")
                else:
                    error_text = await response.text()
                    print(f"API request failed: {response.status} - {error_text}")
    
    except KickAuthManagerError as e:
        print(f"Error with auth manager: {e}")
    except Exception as e:
        print(f"Error making API request: {e}")

async def show_token_info():
    """Display information about the current tokens"""
    global auth_manager
    
    if not auth_manager:
        auth_manager = KickAuthManager()
    
    print("=== Token Information ===")
    if auth_manager.access_token:
        print(f"Access Token: {auth_manager.access_token[:10]}...")
        print(f"Token Type: {auth_manager.token_type}")
        
        # Check if token is expired
        if auth_manager.token_expires_at:
            expires_in = auth_manager.token_expires_at - time.time()
            if expires_in > 0:
                print(f"Token expires in: {int(expires_in)} seconds")
            else:
                print(f"Token expired {int(abs(expires_in))} seconds ago")
        
        if auth_manager.refresh_token:
            print(f"Refresh Token: {auth_manager.refresh_token[:10]}...")
        else:
            print("No refresh token available")
    else:
        print("No tokens available")

async def clear_tokens():
    """Clear stored tokens"""
    global auth_manager
    
    if not auth_manager:
        auth_manager = KickAuthManager()
    
    auth_manager.clear_tokens()
    print("All tokens cleared!")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Kick Auth Example")
    parser.add_argument('--authorize', action='store_true', help='Start authorization flow')
    parser.add_argument('--test-api', action='store_true', help='Test API with token')
    parser.add_argument('--info', action='store_true', help='Show token information')
    parser.add_argument('--clear', action='store_true', help='Clear stored tokens')
    parser.add_argument('--port', type=int, default=8081, help='Port for callback server (default: 8080)')
    
    args = parser.parse_args()
    
    if args.clear:
        await clear_tokens()
    elif args.info:
        await show_token_info()
    elif args.test_api:
        await test_api_request()
    elif args.authorize:
        await authorize(callback_port=args.port)
    else:
        # Default behavior: try to use existing token, authorize if needed
        try:
            global auth_manager
            auth_manager = KickAuthManager()
            token = await auth_manager.get_valid_token()
            print(f"Using existing token: {token[:10]}...")
            
            # Show options
            print("\nOptions:")
            print("  --authorize  Start authorization flow")
            print("  --test-api   Test API with token")
            print("  --info       Show token information")
            print("  --clear      Clear stored tokens")
        except KickAuthManagerError:
            # No valid token, authorize
            print("No valid token found. Starting authorization...")
            await authorize(callback_port=args.port)

if __name__ == "__main__":
    import time  # Import here to avoid conflict with async function
    asyncio.run(main()) 