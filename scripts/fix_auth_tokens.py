#!/usr/bin/env python3
"""
Tool to check and fix Kick bot authentication token issues.
This script helps diagnose and resolve token-related problems that can cause
event subscription failures.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kickbot.kick_auth_manager import KickAuthManager, DEFAULT_TOKEN_FILE
from kickbot.kick_client import KickClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("auth_fixer")

def check_token_file(token_file=DEFAULT_TOKEN_FILE):
    """Check if token file exists and is valid"""
    token_path = Path(token_file)
    
    logger.info(f"Checking token file: {token_path.absolute()}")
    
    if not token_path.exists():
        logger.warning(f"Token file does not exist: {token_path}")
        return False
    
    try:
        with open(token_path, 'r') as f:
            token_data = json.load(f)
            
        # Check required fields
        required_fields = ['access_token', 'refresh_token', 'token_expires_at']
        missing = [field for field in required_fields if field not in token_data]
        
        if missing:
            logger.warning(f"Token file is missing required fields: {missing}")
            return False
            
        logger.info("Token file exists and has required fields")
        return True
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading token file: {e}")
        return False

def create_token_from_client(email, password, token_file=DEFAULT_TOKEN_FILE):
    """Create a new token file using KickClient credentials"""
    if not email or not password:
        logger.error("Email and password are required")
        return False
    
    try:
        logger.info("Creating KickClient to get auth token")
        client = KickClient(email, password)
        
        if not client.auth_token:
            logger.error("Failed to get auth token from KickClient")
            return False
            
        # Create minimal token file with direct auth token
        token_data = {
            "access_token": client.auth_token,
            "refresh_token": None, 
            "token_expires_at": None,  # We don't know when it expires
            "token_type": "Bearer",
            "client_id": os.environ.get("KICK_CLIENT_ID", "unknown"),
            "granted_scopes": "user:read channel:read chat:write events:subscribe"
        }
        
        token_path = Path(token_file)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(token_path, 'w') as f:
            json.dump(token_data, f, indent=4)
            
        logger.info(f"Created token file with client auth token: {token_path}")
        
        # Also set environment variable for fallback
        os.environ["KICK_AUTH_TOKEN"] = client.auth_token
        logger.info("Set KICK_AUTH_TOKEN environment variable")
        
        return True
    except Exception as e:
        logger.error(f"Error creating token from client: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Fix Kick bot auth token issues")
    parser.add_argument("--check", action="store_true", help="Check if token file exists and is valid")
    parser.add_argument("--fix", action="store_true", help="Fix token issues using client credentials")
    parser.add_argument("--email", help="Kick email for creating new tokens")
    parser.add_argument("--password", help="Kick password for creating new tokens")
    parser.add_argument("--token-file", default=DEFAULT_TOKEN_FILE, help="Path to token file")
    
    args = parser.parse_args()
    
    if args.check:
        if check_token_file(args.token_file):
            print("✅ Token file is valid")
            return 0
        else:
            print("❌ Token file is invalid or missing")
            return 1
    
    if args.fix:
        if not args.email or not args.password:
            print("Error: Email and password are required with --fix")
            return 1
            
        if create_token_from_client(args.email, args.password, args.token_file):
            print("✅ Created token file from client credentials")
            return 0
        else:
            print("❌ Failed to create token file")
            return 1
    
    # If no action specified, show help
    if not (args.check or args.fix):
        parser.print_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 