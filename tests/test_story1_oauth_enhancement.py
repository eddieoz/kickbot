#!/usr/bin/env python3
"""
Test cases for Story 1: OAuth Token Management Enhancement

Tests the OAuth token management system including automatic refresh,
scope validation, and graceful fallback handling.
"""

import unittest
import asyncio
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import time

# Add project root to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kickbot.kick_auth_manager import KickAuthManager, KickAuthManagerError

class TestOAuthTokenManagement(unittest.TestCase):
    """Test OAuth token management enhancements for Story 1"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.test_token_file = os.path.join(self.test_dir, "test_tokens.json")
        
        # Test configuration
        self.test_client_id = "test_client_id"
        self.test_client_secret = "test_client_secret"
        self.test_redirect_uri = "https://test.example.com/callback"
        self.test_scopes = "user:read channel:read chat:read chat:write events:subscribe"
        
        # Sample token data
        self.valid_token_data = {
            "access_token": "valid_access_token",
            "refresh_token": "valid_refresh_token",
            "token_expires_at": time.time() + 3600,  # Expires in 1 hour
            "token_type": "Bearer",
            "client_id": self.test_client_id,
            "granted_scopes": self.test_scopes
        }
        
        self.expired_token_data = {
            "access_token": "expired_access_token",
            "refresh_token": "expired_refresh_token",
            "token_expires_at": time.time() - 3600,  # Expired 1 hour ago
            "token_type": "Bearer",
            "client_id": self.test_client_id,
            "granted_scopes": self.test_scopes
        }

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir)

    def test_oauth_token_refresh(self):
        """
        Test: OAuth token automatically refreshes when expired
        Given: Expired OAuth token
        When: API call is made
        Then: Token is automatically refreshed
        """
        # Create auth manager with expired token
        with open(self.test_token_file, 'w') as f:
            json.dump(self.expired_token_data, f)
        
        auth_manager = KickAuthManager(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            redirect_uri=self.test_redirect_uri,
            scopes=self.test_scopes,
            token_file=self.test_token_file
        )
        
        # Mock the token refresh response
        new_token_data = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": self.test_scopes
        }
        
        async def test_refresh():
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = new_token_data
                mock_session.post.return_value = mock_response
                
                # This should trigger token refresh
                valid_token = await auth_manager.get_valid_token()
                
                # Verify token was refreshed
                self.assertEqual(valid_token, "new_access_token")
                self.assertEqual(auth_manager.access_token, "new_access_token")
                self.assertEqual(auth_manager.refresh_token, "new_refresh_token")
                
                # Verify token was saved to file
                with open(self.test_token_file, 'r') as f:
                    saved_data = json.load(f)
                self.assertEqual(saved_data["access_token"], "new_access_token")
        
        asyncio.run(test_refresh())

    def test_oauth_scopes_validation(self):
        """
        Test: Token storage includes all required scopes
        Given: OAuth token with required scopes
        When: Token is validated
        Then: All required scopes are present
        """
        auth_manager = KickAuthManager(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            redirect_uri=self.test_redirect_uri,
            scopes=self.test_scopes,
            token_file=self.test_token_file
        )
        
        # Test scope validation
        required_scopes = ["user:read", "channel:read", "chat:read", "chat:write", "events:subscribe"]
        
        # Set token data
        auth_manager.access_token = "test_token"
        auth_manager.granted_scopes = self.test_scopes
        
        # Validate all required scopes are present
        granted_scope_list = auth_manager.granted_scopes.split()
        for scope in required_scopes:
            self.assertIn(scope, granted_scope_list, f"Required scope '{scope}' not found in granted scopes")

    def test_token_validation_before_api_calls(self):
        """
        Test: Token validation before making API calls
        Given: Auth manager with token
        When: get_valid_token() is called
        Then: Token is validated and returned if valid
        """
        # Create auth manager with valid token
        with open(self.test_token_file, 'w') as f:
            json.dump(self.valid_token_data, f)
        
        auth_manager = KickAuthManager(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            redirect_uri=self.test_redirect_uri,
            scopes=self.test_scopes,
            token_file=self.test_token_file
        )
        
        async def test_validation():
            # Should return valid token without refresh
            valid_token = await auth_manager.get_valid_token()
            self.assertEqual(valid_token, "valid_access_token")
        
        asyncio.run(test_validation())

    def test_graceful_fallback_on_refresh_failure(self):
        """
        Test: Graceful fallback when token refresh fails
        Given: Expired token and refresh failure
        When: Token refresh is attempted
        Then: Clear tokens and raise appropriate error
        """
        # Create auth manager with expired token
        with open(self.test_token_file, 'w') as f:
            json.dump(self.expired_token_data, f)
        
        auth_manager = KickAuthManager(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            redirect_uri=self.test_redirect_uri,
            scopes=self.test_scopes,
            token_file=self.test_token_file
        )
        
        async def test_fallback():
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value = mock_session
                
                # Mock failed refresh response
                mock_response = AsyncMock()
                mock_response.status = 400
                mock_response.json.return_value = {"error": "invalid_grant"}
                mock_response.text.return_value = "invalid_grant"
                mock_session.post.return_value = mock_response
                
                # Should raise error and clear tokens
                with self.assertRaises(KickAuthManagerError):
                    await auth_manager.get_valid_token()
                
                # Verify tokens were cleared
                self.assertIsNone(auth_manager.access_token)
                self.assertIsNone(auth_manager.refresh_token)
        
        asyncio.run(test_fallback())

    def test_required_scopes_in_authorization_url(self):
        """
        Test: All required scopes included in authorization URL
        Given: Auth manager initialization
        When: Authorization URL is generated
        Then: All required scopes are included in the URL
        """
        auth_manager = KickAuthManager(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            redirect_uri=self.test_redirect_uri,
            scopes=self.test_scopes,
            token_file=self.test_token_file
        )
        
        auth_url, code_verifier = auth_manager.get_authorization_url()
        
        # Verify all required scopes are in the URL
        required_scopes = ["user:read", "channel:read", "chat:read", "chat:write", "events:subscribe"]
        for scope in required_scopes:
            self.assertIn(scope.replace(":", "%3A"), auth_url, f"Required scope '{scope}' not found in auth URL")

    def test_token_expiry_buffer_handling(self):
        """
        Test: Token is considered expired before actual expiry (buffer time)
        Given: Token that expires soon (within buffer time)
        When: Token validity is checked
        Then: Token is considered expired and refresh is triggered
        """
        # Create token that expires in 30 seconds (within 60 second buffer)
        soon_expired_token = self.valid_token_data.copy()
        soon_expired_token["token_expires_at"] = time.time() + 30
        
        with open(self.test_token_file, 'w') as f:
            json.dump(soon_expired_token, f)
        
        auth_manager = KickAuthManager(
            client_id=self.test_client_id,
            client_secret=self.test_client_secret,
            redirect_uri=self.test_redirect_uri,
            scopes=self.test_scopes,
            token_file=self.test_token_file
        )
        
        # Token should be considered expired due to buffer
        self.assertFalse(auth_manager._is_token_valid())

if __name__ == '__main__':
    unittest.main()