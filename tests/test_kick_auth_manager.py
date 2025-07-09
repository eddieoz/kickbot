import unittest
import os
import re
import hashlib
import base64
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch, AsyncMock, MagicMock
import importlib
import asyncio # For running async test methods
import aiohttp # For testing network errors

from kickbot.kick_auth_manager import generate_code_verifier, generate_code_challenge, KickAuthManager, KickAuthManagerError

class TestPKCEHelpers(unittest.TestCase):

    def test_generate_code_verifier_length(self):
        """Test that the code verifier has the correct length and properties."""
        for length in [43, 64, 128]:
            verifier = generate_code_verifier(length)
            self.assertEqual(len(verifier), length)
            # Check if it's URL-safe (contains A-Z, a-z, 0-9, -, _)
            self.assertTrue(re.match(r"^[A-Za-z0-9_\-]+$", verifier), 
                            f"Verifier '{verifier}' is not URL safe.")

    def test_generate_code_verifier_uniqueness(self):
        """Test that multiple calls generate unique verifiers."""
        verifiers = {generate_code_verifier() for _ in range(100)}
        self.assertEqual(len(verifiers), 100)

    def test_generate_code_verifier_invalid_length(self):
        """Test that an invalid length raises a ValueError."""
        with self.assertRaises(ValueError):
            generate_code_verifier(42)
        with self.assertRaises(ValueError):
            generate_code_verifier(129)

    def test_generate_code_challenge(self):
        """Test that the code challenge is generated correctly."""
        # Example from RFC 7636 Appendix B, though they use plain, not S256
        # We will generate our own and verify the SHA256 and Base64URL encoding
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk" # A known 43-char verifier
        expected_sha256_digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_sha256_digest).decode('utf-8').rstrip('=')
        
        challenge = generate_code_challenge(verifier)
        self.assertEqual(challenge, expected_challenge)

    def test_generate_code_challenge_empty_verifier(self):
        """Test code challenge with an empty verifier."""
        verifier = ""
        expected_sha256_digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_sha256_digest).decode('utf-8').rstrip('=')
        challenge = generate_code_challenge(verifier)
        self.assertEqual(challenge, expected_challenge)

class TestKickAuthManagerInitialization(unittest.TestCase):
    def test_initialization_with_parameters(self):
        """Test KickAuthManager initializes correctly with direct parameters."""
        manager = KickAuthManager(
            client_id="param_client_id",
            client_secret="param_client_secret",
            redirect_uri="http://param/callback",
            scopes="param:scope"
        )
        self.assertEqual(manager.client_id, "param_client_id")
        self.assertEqual(manager.client_secret, "param_client_secret")
        self.assertEqual(manager.redirect_uri, "http://param/callback")
        self.assertEqual(manager.scopes, "param:scope")

    def test_initialization_with_env_vars(self):
        """Test KickAuthManager initializes correctly from environment variables."""
        mock_env = {
            "KICK_CLIENT_ID": "env_client_id",
            "KICK_CLIENT_SECRET": "env_client_secret",
            "KICK_REDIRECT_URI": "http://env/callback",
            "KICK_SCOPES": "env:scope1 env:scope2"
        }
        with patch.dict(os.environ, mock_env, clear=True):
            from kickbot import kick_auth_manager
            importlib.reload(kick_auth_manager)
            KAManager = kick_auth_manager.KickAuthManager
            
            manager = KAManager()
            self.assertEqual(manager.client_id, "env_client_id")
            self.assertEqual(manager.client_secret, "env_client_secret")
            self.assertEqual(manager.redirect_uri, "http://env/callback")
            self.assertEqual(manager.scopes, "env:scope1 env:scope2")
        
        importlib.reload(kick_auth_manager)

    def test_initialization_missing_client_id_param(self):
        """Test ValueError is raised if client_id is None and KICK_CLIENT_ID is not in env."""
        with patch.dict(os.environ, {}, clear=True):
            from kickbot import kick_auth_manager
            importlib.reload(kick_auth_manager)
            KAManager = kick_auth_manager.KickAuthManager
            with self.assertRaisesRegex(ValueError, "KICK_CLIENT_ID is not set."):
                KAManager(client_id=None, redirect_uri="http://some.uri")
        importlib.reload(kick_auth_manager)

    def test_initialization_missing_redirect_uri_param(self):
        """Test ValueError is raised if redirect_uri is None and KICK_REDIRECT_URI is not in env."""
        with patch.dict(os.environ, {"KICK_CLIENT_ID": "temp_id_for_this_test"}, clear=True):
            from kickbot import kick_auth_manager
            importlib.reload(kick_auth_manager)
            KAManager = kick_auth_manager.KickAuthManager
            with self.assertRaisesRegex(ValueError, "KICK_REDIRECT_URI is not set."):
                KAManager(redirect_uri=None)
        importlib.reload(kick_auth_manager)

class TestKickAuthManagerAuthURL(unittest.TestCase):
    def test_get_authorization_url(self):
        """Test the generation of the authorization URL and code verifier."""
        manager = KickAuthManager(
            client_id="test_client_for_url",
            redirect_uri="https://mybot.com/kick/callback_url",
            scopes="events:read chat:send"
        )
        auth_url, code_verifier = manager.get_authorization_url()
        
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)

        self.assertEqual(parsed_url.scheme, "https")
        self.assertEqual(parsed_url.netloc, "id.kick.com")
        self.assertEqual(parsed_url.path, "/oauth2/authorize") # Confirming assumed path
        
        self.assertEqual(query_params["client_id"][0], "test_client_for_url")
        self.assertEqual(query_params["redirect_uri"][0], "https://mybot.com/kick/callback_url")
        self.assertEqual(query_params["response_type"][0], "code")
        self.assertEqual(query_params["scope"][0], "events:read chat:send")
        self.assertEqual(query_params["code_challenge_method"][0], "S256")
        
        self.assertTrue(43 <= len(code_verifier) <= 128)
        self.assertTrue("code_challenge" in query_params)
        self.assertEqual(query_params["code_challenge"][0], generate_code_challenge(code_verifier))

class TestKickAuthManagerTokenExchange(unittest.IsolatedAsyncioTestCase):

    @patch('kickbot.kick_auth_manager.aiohttp.ClientSession')
    async def test_exchange_code_for_tokens_success(self, MockClientSession):
        """Test successful token exchange."""
        manager = KickAuthManager(
            client_id="test_client", 
            redirect_uri="http://localhost/callback"
        )
        mock_response_data = {"access_token": "fake_access_token", "refresh_token": "fake_refresh_token", "expires_in": 3600}

        # This is the mock for the ClientResponse object
        mock_client_response = AsyncMock()
        mock_client_response.status = 200
        mock_client_response.json = AsyncMock(return_value=mock_response_data)
        mock_client_response.text = AsyncMock(return_value=str(mock_response_data))
        
        # Get the mock for the session instance - properly set up all needed async methods
        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_client_response)
        mock_session_instance.close = AsyncMock()
        MockClientSession.return_value = mock_session_instance

        tokens = await manager.exchange_code_for_tokens("auth_code_123", "verifier_abc")
        self.assertEqual(tokens, mock_response_data)
        
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
    async def test_exchange_code_for_tokens_api_error_json(self, MockClientSession):
        """Test API error (with JSON response) during token exchange."""
        manager = KickAuthManager(client_id="test_client", redirect_uri="http://localhost/callback")
        mock_error_response_json = {"error": "invalid_grant", "error_description": "The authorization code is invalid or expired."}

        mock_client_response = AsyncMock()
        mock_client_response.status = 400
        mock_client_response.json = AsyncMock(return_value=mock_error_response_json)
        mock_client_response.text = AsyncMock(return_value=str(mock_error_response_json))

        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_client_response)
        mock_session_instance.close = AsyncMock()
        MockClientSession.return_value = mock_session_instance

        expected_msg = "Error refreshing access token: 400 - The authorization code is invalid or expired."
        with self.assertRaises(KickAuthManagerError) as cm:
            await manager.exchange_code_for_tokens("invalid_code", "verifier_xyz")
        self.assertEqual(str(cm.exception), expected_msg)

        mock_session_instance.close.assert_called_once()

    @patch('kickbot.kick_auth_manager.aiohttp.ClientSession')
    async def test_exchange_code_for_tokens_api_error_text(self, MockClientSession):
        """Test API error (with non-JSON text response) during token exchange."""
        manager = KickAuthManager(client_id="test_client", redirect_uri="http://localhost/callback")
        mock_error_text = "Service Unavailable"

        mock_client_response = AsyncMock()
        mock_client_response.status = 503
        mock_client_response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(None, None))
        mock_client_response.text = AsyncMock(return_value=mock_error_text)

        # Properly set up the session mock
        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_client_response)
        mock_session_instance.close = AsyncMock()
        MockClientSession.return_value = mock_session_instance

        expected_msg = f"Error exchanging code for tokens: 503 - {mock_error_text}"
        with self.assertRaises(KickAuthManagerError) as cm:
            await manager.exchange_code_for_tokens("any_code", "any_verifier")
        self.assertEqual(str(cm.exception), expected_msg)
        
        mock_session_instance.close.assert_called_once()

    @patch('kickbot.kick_auth_manager.aiohttp.ClientSession')
    async def test_exchange_code_for_tokens_network_error(self, MockClientSession):
        """Test network error during token exchange (e.g. session.post raises an error)."""
        manager = KickAuthManager(client_id="test_client", redirect_uri="http://localhost/callback")
        
        # Create a proper ClientConnectorError mock
        conn_key = MagicMock()
        conn_key.ssl = False
        error = OSError("Network down")
        client_error = aiohttp.ClientConnectorError(conn_key, error)
        
        # Properly set up the session mock
        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(side_effect=client_error)
        mock_session_instance.close = AsyncMock()
        MockClientSession.return_value = mock_session_instance

        expected_msg = "AIOHTTP client error during token exchange"
        with self.assertRaises(KickAuthManagerError) as cm:
            await manager.exchange_code_for_tokens("any_code", "any_verifier")
        self.assertEqual(str(cm.exception), expected_msg)
        
        mock_session_instance.close.assert_called_once()
    
    @patch('kickbot.kick_auth_manager.aiohttp.ClientSession')
    async def test_exchange_code_for_tokens_200_ok_but_not_json(self, MockClientSession):
        """Test 200 OK response but content is not valid JSON."""
        manager = KickAuthManager(client_id="test_client", redirect_uri="http://localhost/callback")
        observed_text_response = "Mocked non-JSON response"

        mock_client_response = AsyncMock()
        mock_client_response.status = 200
        mock_client_response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(MagicMock(), tuple()))
        mock_client_response.text = AsyncMock(return_value=observed_text_response)

        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_client_response)
        mock_session_instance.close = AsyncMock()
        MockClientSession.return_value = mock_session_instance

        expected_msg_literal = f"Token endpoint returned 200 OK but non-JSON response: {observed_text_response}"
        # Using explicit assertEqual on the exception string for clearer diff if it fails
        with self.assertRaises(KickAuthManagerError) as cm:
            await manager.exchange_code_for_tokens("any_code", "any_verifier")
        self.assertEqual(str(cm.exception), expected_msg_literal)
        
        mock_session_instance.close.assert_called_once()

# To run these tests (assuming you are in the root of the project and have unittest discovery):
# python -m unittest tests.test_kick_auth_manager
# Or if your structure is different, adjust the command. 
# Make sure kickbot module is in PYTHONPATH.
# e.g., export PYTHONPATH=$(pwd):$PYTHONPATH

if __name__ == '__main__':
    unittest.main() 