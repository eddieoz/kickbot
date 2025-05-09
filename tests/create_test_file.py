#!/usr/bin/env python
"""
Script to create a test file with a fixed version of the failing tests
"""

file_content = """
\"\"\"
Tests for KickAuthManager - Fixed version that works even in unittest discover
\"\"\"

import unittest
import os
import re
import hashlib
import base64
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch, AsyncMock, MagicMock
import importlib
import asyncio  # For running async test methods
import warnings
import aiohttp
from aiohttp.client_exceptions import ContentTypeError, ClientConnectorError

# Import the functions and classes we want to test
from kickbot.kick_auth_manager import (
    generate_code_verifier,
    generate_code_challenge,
    KickAuthManager,
    KickAuthManagerError
)

# Only include the tests that were failing in the original file
class TestKickAuthManagerTokenExchange(unittest.IsolatedAsyncioTestCase):
    \"\"\"Test token exchange functionality.\"\"\"

    @patch('kickbot.kick_auth_manager.aiohttp.ClientSession')
    async def test_exchange_code_for_tokens_success(self, MockClientSession):
        \"\"\"Test successful token exchange.\"\"\"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            
            manager = KickAuthManager(
                client_id="test_client", 
                redirect_uri="http://localhost/callback"
            )
            mock_response_data = {"access_token": "fake_access_token", "refresh_token": "fake_refresh_token", "expires_in": 3600}

            # Set up mock response
            mock_client_response = AsyncMock()
            mock_client_response.status = 200
            mock_client_response.json = AsyncMock(return_value=mock_response_data)
            mock_client_response.text = AsyncMock(return_value=str(mock_response_data))
            
            # Set up session mock
            mock_session_instance = AsyncMock()
            mock_session_instance.post = AsyncMock(return_value=mock_client_response)
            mock_session_instance.close = AsyncMock()
            MockClientSession.return_value = mock_session_instance

            tokens = await manager.exchange_code_for_tokens("auth_code_123", "verifier_abc")
            self.assertEqual(tokens, mock_response_data)
            
            # Check that post was called with correct parameters
            expected_payload = {
                "grant_type": "authorization_code",
                "client_id": "test_client",
                "code": "auth_code_123",
                "redirect_uri": "http://localhost/callback",
                "code_verifier": "verifier_abc",
            }
            mock_session_instance.post.assert_called_once_with(manager.token_endpoint, data=expected_payload)
            mock_session_instance.close.assert_called_once()

    @patch('kickbot.kick_auth_manager.aiohttp.ClientSession')
    async def test_exchange_code_for_tokens_200_ok_but_not_json(self, MockClientSession):
        \"\"\"Test 200 OK response but content is not valid JSON.\"\"\"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            
            manager = KickAuthManager(client_id="test_client", redirect_uri="http://localhost/callback")
            mock_text_response = "<html><body>Success but not JSON</body></html>"

            # Create a proper ContentTypeError
            request_info = MagicMock()
            request_info.real_url = "https://id.kick.com/oauth2/token"
            content_error = ContentTypeError(request_info, mock_text_response)
            
            # Set up mock response
            mock_client_response = AsyncMock()
            mock_client_response.status = 200
            mock_client_response.json = AsyncMock(side_effect=content_error)
            mock_client_response.text = AsyncMock(return_value=mock_text_response)

            # Set up session mock
            mock_session_instance = AsyncMock()
            mock_session_instance.post = AsyncMock(return_value=mock_client_response)
            mock_session_instance.close = AsyncMock()
            MockClientSession.return_value = mock_session_instance

            try:
                await manager.exchange_code_for_tokens("any_code", "any_verifier")
                self.fail("Expected KickAuthManagerError but no exception was raised")
            except KickAuthManagerError:
                # Expected exception, test passes
                pass
                
            mock_session_instance.close.assert_called_once()

    @patch('kickbot.kick_auth_manager.aiohttp.ClientSession')
    async def test_exchange_code_for_tokens_api_error_json(self, MockClientSession):
        \"\"\"Test API error (with JSON response) during token exchange.\"\"\"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            
            manager = KickAuthManager(client_id="test_client", redirect_uri="http://localhost/callback")
            mock_error_response_json = {"error": "invalid_grant", "error_description": "The authorization code is invalid or expired."}

            # Set up mock response
            mock_client_response = AsyncMock()
            mock_client_response.status = 400
            mock_client_response.json = AsyncMock(return_value=mock_error_response_json)
            mock_client_response.text = AsyncMock(return_value=str(mock_error_response_json))

            # Set up session mock
            mock_session_instance = AsyncMock()
            mock_session_instance.post = AsyncMock(return_value=mock_client_response)
            mock_session_instance.close = AsyncMock()
            MockClientSession.return_value = mock_session_instance

            try:
                await manager.exchange_code_for_tokens("invalid_code", "verifier_xyz")
                self.fail("Expected KickAuthManagerError but no exception was raised")
            except KickAuthManagerError:
                # Expected exception, test passes
                pass
                
            mock_session_instance.close.assert_called_once()

    @patch('kickbot.kick_auth_manager.aiohttp.ClientSession')
    async def test_exchange_code_for_tokens_api_error_text(self, MockClientSession):
        \"\"\"Test API error (with non-JSON text response) during token exchange.\"\"\"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            
            manager = KickAuthManager(client_id="test_client", redirect_uri="http://localhost/callback")
            mock_error_text = "Service Unavailable"

            # Set up mock response
            mock_client_response = AsyncMock()
            mock_client_response.status = 503
            mock_client_response.json = AsyncMock(side_effect=ContentTypeError(None, None))
            mock_client_response.text = AsyncMock(return_value=mock_error_text)

            # Set up session mock
            mock_session_instance = AsyncMock()
            mock_session_instance.post = AsyncMock(return_value=mock_client_response)
            mock_session_instance.close = AsyncMock()
            MockClientSession.return_value = mock_session_instance

            try:
                await manager.exchange_code_for_tokens("any_code", "any_verifier")
                self.fail("Expected KickAuthManagerError but no exception was raised")
            except KickAuthManagerError:
                # Expected exception, test passes
                pass
                
            mock_session_instance.close.assert_called_once()

    @patch('kickbot.kick_auth_manager.aiohttp.ClientSession')
    async def test_exchange_code_for_tokens_network_error(self, MockClientSession):
        \"\"\"Test network error during token exchange (e.g. session.post raises an error).\"\"\"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            
            manager = KickAuthManager(client_id="test_client", redirect_uri="http://localhost/callback")
            
            # Create a proper ClientConnectorError mock
            conn_key = MagicMock()
            conn_key.ssl = False
            error = OSError("Network down")
            client_error = ClientConnectorError(conn_key, error)
            
            # Set up session mock
            mock_session_instance = AsyncMock()
            mock_session_instance.post = AsyncMock(side_effect=client_error)
            mock_session_instance.close = AsyncMock()
            MockClientSession.return_value = mock_session_instance

            try:
                await manager.exchange_code_for_tokens("any_code", "any_verifier")
                self.fail("Expected KickAuthManagerError but no exception was raised")
            except KickAuthManagerError:
                # Expected exception, test passes
                pass
                
            mock_session_instance.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
"""

with open("tests/test_kick_auth_manager_fixed.py", "w") as f:
    f.write(file_content)

print("Test file created successfully!") 