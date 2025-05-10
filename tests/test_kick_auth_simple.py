import unittest
import os
import re
import hashlib
import base64
import asyncio
import time # Ensure time is imported
import json # Ensure json is imported
from unittest.mock import patch, AsyncMock, MagicMock

# Import the functions and classes we want to test
from kickbot.kick_auth_manager import (
    generate_code_verifier,
    generate_code_challenge,
    KickAuthManager,
    KickAuthManagerError,
    # TOKEN_EXPIRY_BUFFER # If needed directly in tests, but usually tested via manager's behavior
)

class TestPKCEHelpers(unittest.TestCase):
    """Test the PKCE helper functions."""
    
    def test_generate_code_verifier_length(self):
        """Test that the code verifier has the correct length and properties."""
        for length in [43, 64, 128]:
            verifier = generate_code_verifier(length)
            self.assertEqual(len(verifier), length)
            self.assertTrue(re.match(r"^[A-Za-z0-9_\-]+$", verifier), 
                            f"Verifier '{verifier}' is not URL safe.")

    def test_generate_code_challenge(self):
        """Test that the code challenge is generated correctly."""
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        expected_sha256_digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_sha256_digest).decode('utf-8').rstrip('=')
        challenge = generate_code_challenge(verifier)
        self.assertEqual(challenge, expected_challenge)


class TestKickAuthManagerInit(unittest.TestCase): # Renamed for clarity from TestKickAuthManager
    """Test basic KickAuthManager initialization and auth URL generation."""
    
    def test_initialization(self):
        """Test KickAuthManager initializes correctly with direct parameters."""
        manager = KickAuthManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://test/callback",
            scopes="test:scope"
        )
        self.assertEqual(manager.client_id, "test_client_id")
        self.assertEqual(manager.client_secret, "test_client_secret")
        self.assertEqual(manager.redirect_uri, "http://test/callback")
        self.assertEqual(manager.scopes, "test:scope")
    
    def test_get_authorization_url(self):
        """Test the generation of the authorization URL."""
        manager = KickAuthManager(
            client_id="test_client_id",
            redirect_uri="http://test/callback",
            scopes="test:scope"
        )
        auth_url, code_verifier = manager.get_authorization_url()
        
        self.assertIn("client_id=test_client_id", auth_url)
        self.assertIn("redirect_uri=http%3A%2F%2Ftest%2Fcallback", auth_url)
        self.assertIn("scope=test%3Ascope", auth_url)
        self.assertIn("code_challenge_method=S256", auth_url)
        self.assertTrue(43 <= len(code_verifier) <= 128)
        self.assertTrue(re.match(r"^[A-Za-z0-9_\-]+$", code_verifier))
        code_challenge = generate_code_challenge(code_verifier)
        self.assertIn(f"code_challenge={code_challenge}", auth_url)


def async_test(f):
    """Decorator to run async test methods."""
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
            asyncio.set_event_loop(None)
    return wrapper

class TestKickAuthTokenExchange(unittest.TestCase):
    """Test token exchange functionality with simplified mocking."""
    
    @async_test
    async def test_exchange_code_success(self):
        manager = KickAuthManager(client_id="test_client_id", redirect_uri="http://test/callback")
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "test_access_token", "refresh_token": "test_refresh_token", "expires_in": 3600
        })
        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.close = AsyncMock()
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Patch _save_tokens as it's tested separately and involves file I/O
            with patch.object(manager, '_save_tokens', MagicMock()) as mock_save:
                result = await manager.exchange_code_for_tokens("test_code", "test_verifier")
                mock_save.assert_called_once() # Ensure it was called

            mock_session.post.assert_called_once()
            call_args, call_kwargs = mock_session.post.call_args
            self.assertEqual(call_args[0], "https://id.kick.com/oauth2/token")
            self.assertEqual(call_kwargs["data"]["client_id"], "test_client_id")
            self.assertEqual(result["access_token"], "test_access_token")
            mock_session.close.assert_called_once()
    
    @async_test
    async def test_exchange_code_error(self):
        manager = KickAuthManager(client_id="test_client_id", redirect_uri="http://test/callback")
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={"error": "invalid_grant", "error_description": "Invalid code or verifier"})
        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.close = AsyncMock()
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with self.assertRaises(KickAuthManagerError):
                await manager.exchange_code_for_tokens("invalid_code", "invalid_verifier")
            mock_session.close.assert_called_once()

class TestKickAuthTokenManagement(unittest.TestCase):
    """Test token storage, loading, validity, and refresh mechanisms."""

    def setUp(self):
        self.test_token_file = "test_kickbot_tokens.json" 
        self.client_id = "test_client_id_for_token_mgmt"

        # Patch Path.exists to return False during KickAuthManager initialization
        # ensuring _load_tokens in __init__ doesn't attempt to read a file.
        with patch('kickbot.kick_auth_manager.Path.exists', return_value=False) as mock_init_path_exists:
            with patch('builtins.open') as mock_init_builtins_open: # CHANGED from Path.open
                self.manager = KickAuthManager(
                    client_id=self.client_id,
                    redirect_uri="http://test/callback_token_mgmt",
                    scopes="test:scope_token_mgmt",
                    token_file=self.test_token_file
                )
                # Check if _load_tokens in __init__ correctly did not proceed due to Path.exists == False
                mock_init_path_exists.assert_called_once() # Called by _load_tokens
                mock_init_builtins_open.assert_not_called() # Should not be called if file doesn't exist

        # Tokens should be None as _load_tokens (from init) shouldn't have loaded anything
        self.assertIsNone(self.manager.access_token)
        self.assertIsNone(self.manager.refresh_token)
        self.assertIsNone(self.manager.token_expires_at)

    def tearDown(self):
        # Clean up the test token file if mocks didn't prevent its creation or if it's useful for debugging
        # Note: Mocks should ideally prevent actual file creation.
        if os.path.exists(self.test_token_file):
            try:
                os.remove(self.test_token_file)
            except OSError:
                pass # Ignore if it can't be removed (e.g. permissions, race condition)

    @patch('builtins.open')
    @patch('kickbot.kick_auth_manager.Path.mkdir')
    @patch('json.dump')
    def test_save_tokens_success(self, mock_json_dump, mock_mkdir, mock_open):
        mock_file_handle = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file_handle
        
        current_time = time.time()
        self.manager.access_token = "saved_access_token"
        self.manager.refresh_token = "saved_refresh_token"
        self.manager.token_expires_at = current_time + 3600
        self.manager.token_type = "Bearer"
        self.manager.granted_scopes = "test:scope"
        self.manager.client_id = self.client_id # Ensure manager has the client_id

        self.manager._save_tokens()

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        # self.manager.token_file_path should be Path(self.test_token_file).resolve()
        self.assertEqual(str(self.manager.token_file_path.name), self.test_token_file)
        mock_open.assert_called_once_with(self.manager.token_file_path, "w")
        
        expected_data_to_save = {
            "access_token": "saved_access_token", "refresh_token": "saved_refresh_token",
            "token_expires_at": self.manager.token_expires_at, "token_type": "Bearer",
            "client_id": self.client_id, "granted_scopes": "test:scope"
        }
        mock_json_dump.assert_called_once_with(expected_data_to_save, mock_file_handle, indent=4)

    @patch('builtins.open')
    @patch('json.dump')
    def test_save_tokens_no_access_token(self, mock_json_dump, mock_open):
        self.manager.access_token = None
        self.manager._save_tokens()
        mock_open.assert_not_called()
        mock_json_dump.assert_not_called()

    @patch('kickbot.kick_auth_manager.Path.exists')
    @patch('builtins.open')
    @patch('json.load')
    def test_load_tokens_success(self, mock_json_load, mock_open, mock_path_exists):
        mock_path_exists.return_value = True
        mock_file_handle = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file_handle
        
        fake_expiry_time = time.time() + 3600
        loaded_data = {
            "access_token": "loaded_access_token", "refresh_token": "loaded_refresh_token",
            "token_expires_at": fake_expiry_time, "token_type": "OAuth2",
            "client_id": self.client_id, "granted_scopes": "read:chat write:chat"
        }
        mock_json_load.return_value = loaded_data

        # Reset manager before loading to ensure a clean state
        self.manager.access_token = None 
        self.manager._load_tokens()

        mock_path_exists.assert_called_once_with()
        mock_open.assert_called_once_with(self.manager.token_file_path, "r")
        mock_json_load.assert_called_once_with(mock_file_handle)

        self.assertEqual(self.manager.access_token, loaded_data["access_token"])
        self.assertEqual(self.manager.refresh_token, loaded_data["refresh_token"])
        self.assertEqual(self.manager.token_expires_at, loaded_data["token_expires_at"])
        self.assertEqual(self.manager.token_type, loaded_data["token_type"])
        self.assertEqual(self.manager.granted_scopes, loaded_data["granted_scopes"])

    @patch('kickbot.kick_auth_manager.Path.exists')
    def test_load_tokens_file_not_exists(self, mock_path_exists):
        mock_path_exists.return_value = False
        self.manager.access_token = None # Ensure clean state
        self.manager._load_tokens()
        mock_path_exists.assert_called_once_with()
        self.assertIsNone(self.manager.access_token)

    @patch('kickbot.kick_auth_manager.Path.exists')
    @patch('builtins.open')
    @patch('json.load')
    @patch.object(KickAuthManager, 'clear_tokens_file') 
    def test_load_tokens_corrupted_json(self, mock_clear_tokens_file, mock_json_load, mock_open, mock_path_exists):
        mock_path_exists.return_value = True
        # Ensure open returns a context manager
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_json_load.side_effect = json.JSONDecodeError("mock error", "doc", 0)
        
        # Reset manager before loading to ensure a clean state
        self.manager.access_token = None 
        self.manager.refresh_token = None
        self.manager.token_expires_at = None

        # The actual error message includes the full JSONDecodeError string.
        # json.JSONDecodeError("mock error", "doc", 0) stringifies to "mock error: line 1 column 1 (char 0)"
        json_error_str = str(json.JSONDecodeError("mock error", "doc", 0))
        expected_log_message = f"Error decoding token file {self.manager.token_file_path}: {json_error_str}. Deleting corrupted file."
        
        with self.assertLogs(logger='kickbot.kick_auth_manager', level='WARNING') as cm:
            self.manager._load_tokens()
        
        self.assertIsNone(self.manager.access_token)
        mock_path_exists.assert_called_once_with()
        mock_open.assert_called_once_with(self.manager.token_file_path, "r")
        mock_json_load.assert_called_once()
        mock_clear_tokens_file.assert_called_once_with()

        # Check if the expected log message is in the captured logs
        self.assertTrue(any(expected_log_message in message for message in cm.output),
                        f"Expected log message '{expected_log_message}' not found in {cm.output}")

    @patch('kickbot.kick_auth_manager.Path.exists')
    @patch('builtins.open')
    @patch('json.load')
    @patch.object(KickAuthManager, 'clear_tokens_file') # Patch clear_tokens_file instead of clear_tokens
    def test_load_tokens_mismatched_client_id(self, mock_clear_tokens_file, mock_json_load, mock_open, mock_path_exists):
        mock_path_exists.return_value = True
        mock_open.return_value.__enter__.return_value = MagicMock() # Mock file handle
        
        correct_client_id = self.manager.client_id
        mismatched_client_id = "mismatched_test_client_id"
        self.assertNotEqual(correct_client_id, mismatched_client_id)

        loaded_data = {
            "access_token": "loaded_access_token", "refresh_token": "loaded_refresh_token",
            "token_expires_at": time.time() + 3600, "token_type": "Bearer",
            "client_id": mismatched_client_id, 
            "granted_scopes": "test:scope"
        }
        mock_json_load.return_value = loaded_data

        self.manager.access_token = "old_access_token" 
        self.manager.refresh_token = "old_refresh_token"
        self.manager.token_expires_at = time.time() + 10000

        expected_log_message = f"Tokens in {self.manager.token_file_path} are for a different client_id ('{mismatched_client_id}' vs '{correct_client_id}'). Clearing tokens."

        with self.assertLogs(logger='kickbot.kick_auth_manager', level='WARNING') as cm:
            self.manager._load_tokens() 

        self.assertTrue(any(expected_log_message in message for message in cm.output),
                        f"Expected log message '{expected_log_message}' not found in {cm.output}")

        mock_path_exists.assert_called_once_with()
        mock_open.assert_called_once_with(self.manager.token_file_path, "r")
        mock_json_load.assert_called_once()
        # The real clear_tokens should have been called, which in turn calls clear_tokens_file
        mock_clear_tokens_file.assert_called_once_with()

        # Verify tokens are cleared in the manager instance by the real clear_tokens method
        self.assertIsNone(self.manager.access_token)
        self.assertIsNone(self.manager.refresh_token)
        self.assertIsNone(self.manager.token_expires_at)

    @patch('kickbot.kick_auth_manager.Path.exists')
    @patch('builtins.open')
    @patch('json.load')
    @patch.object(KickAuthManager, 'clear_tokens_file')
    def test_load_tokens_incomplete_data(self, mock_clear_tokens_file, mock_json_load, mock_open, mock_path_exists):
        mock_path_exists.return_value = True
        mock_open.return_value.__enter__.return_value = MagicMock() # Mock file handle

        # Example of incomplete data (missing 'refresh_token')
        incomplete_data = {
            "access_token": "loaded_access_token",
            # "refresh_token": "loaded_refresh_token", # Still missing, though current code doesn't check this specifically for this log
            "token_expires_at": "not_a_number", # CHANGED to be an invalid type
            "token_type": "Bearer",
            "client_id": self.manager.client_id, # Correct client_id to pass that check
            "granted_scopes": "test:scope"
        }
        mock_json_load.return_value = incomplete_data

        # Reset manager state
        self.manager.access_token = "old_access_token"
        self.manager.refresh_token = "old_refresh_token"
        self.manager.token_expires_at = time.time() + 10000

        expected_log_message = f"Invalid or incomplete token data in {self.manager.token_file_path}. Missing keys or invalid type. Clearing tokens."
        # Note: The actual logged message in KickAuthManager might be more specific about WHICH key is missing.
        # If so, this expected_log_message might need adjustment or the test could check for a more general message part.

        with self.assertLogs(logger='kickbot.kick_auth_manager', level='WARNING') as cm:
            self.manager._load_tokens() # This should trigger the incomplete data logic

        self.assertTrue(any(expected_log_message in message for message in cm.output),
                        f"Expected log message part '{expected_log_message}' not found in {cm.output}")

        mock_path_exists.assert_called_once_with()
        mock_open.assert_called_once_with(self.manager.token_file_path, "r")
        mock_json_load.assert_called_once()
        mock_clear_tokens_file.assert_called_once_with()

        self.assertIsNone(self.manager.access_token)
        self.assertIsNone(self.manager.refresh_token)
        self.assertIsNone(self.manager.token_expires_at)

    def test_is_access_token_valid(self):
        self.manager.access_token = None
        self.assertFalse(self.manager.is_access_token_valid())

        self.manager.access_token = "some_token"
        self.manager.token_expires_at = None # No expiry
        self.assertFalse(self.manager.is_access_token_valid())

        current_mock_time = 10000.0
        with patch('time.time', return_value=current_mock_time):
            self.manager.access_token = "valid_token"
            # Valid: Expires in 1 hour (TOKEN_EXPIRY_BUFFER is 60s)
            self.manager.token_expires_at = current_mock_time + 3600 
            self.assertTrue(self.manager.is_access_token_valid()) 

            # Expired: Expired 1 second ago
            self.manager.token_expires_at = current_mock_time - 1 
            self.assertFalse(self.manager.is_access_token_valid())

            # Expiring soon (within buffer): Expires in 30s, buffer is 60s
            self.manager.token_expires_at = current_mock_time + 30 
            self.assertFalse(self.manager.is_access_token_valid())

            # Valid (just outside buffer): Expires in 90s, buffer is 60s
            self.manager.token_expires_at = current_mock_time + 90 
            self.assertTrue(self.manager.is_access_token_valid())

    @patch.object(KickAuthManager, 'clear_tokens_file')
    def test_clear_tokens(self, mock_clear_tokens_file):
        self.manager.access_token = "acc"; self.manager.refresh_token = "ref"
        self.manager.token_expires_at = time.time(); self.manager.granted_scopes = "test"
        self.manager.clear_tokens()
        self.assertIsNone(self.manager.access_token)
        self.assertIsNone(self.manager.refresh_token)
        self.assertIsNone(self.manager.token_expires_at)
        self.assertIsNone(self.manager.granted_scopes)
        mock_clear_tokens_file.assert_called_once()

    @patch('kickbot.kick_auth_manager.Path.exists')
    @patch('kickbot.kick_auth_manager.Path.unlink')
    def test_clear_tokens_file(self, mock_unlink, mock_exists):
        mock_exists.return_value = True
        self.manager.clear_tokens_file()
        mock_exists.assert_called_once()
        mock_unlink.assert_called_once()

        mock_exists.reset_mock(); mock_unlink.reset_mock()
        mock_exists.return_value = False
        self.manager.clear_tokens_file()
        mock_exists.assert_called_once()
        mock_unlink.assert_not_called()

    # --- Asynchronous tests for refresh_access_token and get_valid_token ---
    @async_test
    @patch('aiohttp.ClientSession')
    @patch('time.time')
    async def test_refresh_access_token_success(self, mock_time, mock_client_session):
        # Simulate having a valid refresh token and expired access token
        self.manager.refresh_token = "initial_refresh_token"
        self.manager.access_token = "expired_access_token"
        self.manager.token_expires_at = time.time() - 3600 # Expired
        mock_time.return_value = time.time() # Ensure time.time() is consistent

        # Mock aiohttp response for successful token refresh
        mock_api_response = MagicMock()
        mock_api_response.status = 200
        new_tokens = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "refreshed:scope"
        }
        mock_api_response.json = AsyncMock(return_value=new_tokens)
        
        mock_session_instance = mock_client_session.return_value 
        mock_session_instance.post = AsyncMock(return_value=mock_api_response) 
        mock_session_instance.close = AsyncMock()

        # Patch _save_tokens directly on the instance for this call
        with patch.object(self.manager, '_save_tokens', new_callable=MagicMock) as mock_save_on_instance:
            await self.manager.refresh_access_token()
            mock_save_on_instance.assert_called_once() # Check the instance mock

        # Assertions
        self.assertEqual(self.manager.access_token, new_tokens["access_token"])
        self.assertEqual(self.manager.token_expires_at, time.time() + new_tokens["expires_in"])
        self.assertEqual(self.manager.token_type, new_tokens["token_type"])
        self.assertEqual(self.manager.refresh_token, new_tokens["refresh_token"])
        self.assertEqual(self.manager.granted_scopes, "refreshed:scope")

    @async_test
    @patch('kickbot.kick_auth_manager.KickAuthManager.clear_tokens') 
    @patch('aiohttp.ClientSession')
    async def test_refresh_access_token_failure_invalid_grant(self, mock_client_session, mock_clear_tokens):
        self.manager.refresh_token = "invalid_refresh_token"
        mock_http_response = MagicMock()
        mock_http_response.status = 400
        mock_http_response.json = AsyncMock(return_value={"error": "invalid_grant", "error_description": "Refresh token expired or revoked"})
        
        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_http_response)
        mock_session_instance.close = AsyncMock()
        mock_client_session.return_value = mock_session_instance

        with self.assertRaisesRegex(KickAuthManagerError, "Error refreshing access token: 400 - Refresh token expired or revoked"):
            await self.manager.refresh_access_token()
        mock_clear_tokens.assert_called_once()

    @async_test
    async def test_refresh_access_token_no_refresh_token(self):
        self.manager.refresh_token = None
        with self.assertRaisesRegex(KickAuthManagerError, "No refresh token available to refresh the access token."):
            await self.manager.refresh_access_token()

    @async_test
    @patch('time.time')
    async def test_get_valid_token_returns_existing_valid_token(self, mock_time):
        current_time = 1700000000.0
        mock_time.return_value = current_time
        self.manager.access_token = "valid_existing_token"
        self.manager.token_expires_at = current_time + 3600 
        
        with patch.object(self.manager, 'refresh_access_token', new_callable=AsyncMock) as mock_refresh:
            token = await self.manager.get_valid_token()
            self.assertEqual(token, "valid_existing_token")
            mock_refresh.assert_not_called()

    @async_test
    @patch('aiohttp.ClientSession')
    @patch('time.time')
    async def test_get_valid_token_expired_successful_refresh(self, mock_time, mock_client_session):
        current_time = 1700000000.0
        mock_time.return_value = current_time
        self.manager.access_token = "expired_token"
        self.manager.token_expires_at = current_time - 100 
        self.manager.refresh_token = "can_refresh_token"

        mock_http_response = MagicMock()
        mock_http_response.status = 200
        new_access_token = "refreshed_token_for_get_valid"
        new_expires_in = 7200
        mock_http_response.json = AsyncMock(return_value={"access_token": new_access_token, "expires_in": new_expires_in})
        
        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_http_response)
        mock_session_instance.close = AsyncMock()
        mock_client_session.return_value = mock_session_instance

        # ADD: Patch _save_tokens directly on the instance
        with patch.object(self.manager, '_save_tokens', new_callable=MagicMock) as mock_save_tokens_on_instance:
            token = await self.manager.get_valid_token()

            self.assertEqual(token, new_access_token)
            self.assertEqual(self.manager.access_token, new_access_token)
            self.assertEqual(self.manager.token_expires_at, current_time + new_expires_in)
            mock_save_tokens_on_instance.assert_called_once() # Ensure instance mock is checked
            mock_session_instance.post.assert_called_once()

    @async_test
    @patch('aiohttp.ClientSession')
    @patch('time.time')
    async def test_get_valid_token_expired_refresh_fails(self, mock_time, mock_client_session):
        current_fixed_time = 1700000000.0
        mock_time.return_value = current_fixed_time

        self.manager.access_token = "expired_token"
        self.manager.refresh_token = "valid_refresh_token"
        self.manager.token_expires_at = current_fixed_time - 1000 # Expired

        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.json = AsyncMock(return_value={"error": "invalid_grant", "error_description": "Token is bad"})
        mock_response.text = AsyncMock(return_value="Token is bad") # Fallback for error text if not JSON
        
        mock_session_instance = mock_client_session.return_value
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session_instance.close = AsyncMock()

        with self.assertRaisesRegex(KickAuthManagerError, r"Error refreshing access token: 401 - Token is bad"):
            await self.manager.get_valid_token()
        
        mock_session_instance.post.assert_awaited_once()
        # Assert that clear_tokens was called if refresh fails with invalid_grant
        # This requires clear_tokens to be a mock or to check its side effects
        # For now, we focus on the raised exception. If clear_tokens is an important side effect, it should be asserted.

    @async_test
    async def test_get_valid_token_no_token_no_refresh_token(self):
        self.manager.access_token = None
        self.manager.refresh_token = None
        with self.assertRaisesRegex(KickAuthManagerError, "No valid token available and no refresh token to get a new one."):
            await self.manager.get_valid_token()

    @async_test
    @patch('time.time')
    async def test_get_valid_token_expired_token_no_refresh_token(self, mock_time):
        current_fixed_time = 1700000000.0 # Use a fixed float timestamp
        mock_time.return_value = current_fixed_time

        self.manager.access_token = "expired_token"
        self.manager.refresh_token = None
        self.manager.token_expires_at = current_fixed_time - 1000 # Expired, based on the fixed mock time

        with self.assertRaisesRegex(KickAuthManagerError, "No valid token available and no refresh token to get a new one."):
            await self.manager.get_valid_token()

if __name__ == '__main__':
    unittest.main() 