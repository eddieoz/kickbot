#!/usr/bin/env python3
"""
Check environment variables for KickBot
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("🔍 Checking KickBot Environment Variables")
print("=" * 50)

# Check for OAuth credentials
oauth_vars = {
    'KICK_CLIENT_ID': os.getenv('KICK_CLIENT_ID'),
    'KICK_CLIENT_SECRET': os.getenv('KICK_CLIENT_SECRET'),
    'KICK_REDIRECT_URI': os.getenv('KICK_REDIRECT_URI'),
    'KICK_SCOPES': os.getenv('KICK_SCOPES')
}

print("OAuth Credentials:")
for var, value in oauth_vars.items():
    if value:
        masked_value = value[:8] + "*" * (len(value) - 8) if len(value) > 8 else "*" * len(value)
        print(f"  ✅ {var}: {masked_value}")
    else:
        print(f"  ❌ {var}: Not set")

print("\n" + "=" * 50)

# Check for user/pass credentials
userpass_vars = {
    'USERBOT_EMAIL': os.getenv('USERBOT_EMAIL'),
    'USERBOT_PASS': os.getenv('USERBOT_PASS')
}

print("User/Pass Credentials:")
for var, value in userpass_vars.items():
    if value:
        masked_value = value[:3] + "*" * (len(value) - 3) if len(value) > 3 else "*" * len(value)
        print(f"  ✅ {var}: {masked_value}")
    else:
        print(f"  ❌ {var}: Not set")

print("\n" + "=" * 50)

# Check for other settings
other_vars = {
    'KICK_WEBHOOK_PATH': os.getenv('KICK_WEBHOOK_PATH'),
    'KICK_WEBHOOK_PORT': os.getenv('KICK_WEBHOOK_PORT')
}

print("Other Settings:")
for var, value in other_vars.items():
    if value:
        print(f"  ✅ {var}: {value}")
    else:
        print(f"  ❌ {var}: Not set")

print("\n📋 Recommendations:")
if not any(oauth_vars.values()):
    print("  • Set up OAuth credentials to use OAuth authentication")
    print("  • Create a Kick.com application at https://kick.com/developer/applications")
    print("  • Add the credentials to your .env file")
    
if not any(userpass_vars.values()):
    print("  • Set up user/pass credentials if you want to use traditional authentication")
    print("  • Add USERBOT_EMAIL and USERBOT_PASS to your .env file")

print("\n💡 Currently, the bot is configured to use OAuth authentication.")
print("   If you don't have OAuth credentials, you'll need to either:")
print("   1. Set up OAuth credentials, or")
print("   2. Modify botoshi.py to use traditional authentication")