import unittest
import os
import json
import time
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

# Import the module to test
from kickbot.kick_auth_manager import KickAuthManager, KickAuthManagerError

# Helper for running async tests with a new event loop
def async_test(f):
    def wrapper(*args, **kwargs):
        # Create a new event loop for each test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
            asyncio.set_event_loop(None)
    return wrapper

class TestKickAuthTokenStorage(unittest.TestCase):
    """Tests for KickAuthManager token storage and refresh functionality"""
    
    def setUp(self):
        """Set up a temporary token file for testing"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        
        # Create auth manager with test parameters
        self.auth_manager = KickAuthManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://test/callback",
            scopes="test:scope",
            token_file=self.temp_file.name
        )
    
    def tearDown(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_save_and_load_tokens(self):
        """Test saving tokens to file and loading them back"""
        # Set up token data
        self.auth_manager.access_token = "test_access_token"
        self.auth_manager.refresh_token = "test_refresh_token"
        self.auth_manager.token_type = "Bearer"
        self.auth_manager.token_expires_at = time.time() + 3600
        
        # Save tokens
        self.auth_manager._save_tokens()
        
        # Create a new auth manager that should load the tokens
        new_auth_manager = KickAuthManager(
            client_id="test_client_id",
            redirect_uri="http://test/callback",
            token_file=self.temp_file.name
        )
        
        # Verify tokens were loaded
        self.assertEqual(new_auth_manager.access_token, "test_access_token")
        self.assertEqual(new_auth_manager.refresh_token, "test_refresh_token")
        self.assertEqual(new_auth_manager.token_type, "Bearer")
        self.assertIsNotNone(new_auth_manager.token_expires_at)
    
    def test_clear_tokens(self):
        """Test clearing tokens and removing token file"""
        # Set up token data
        self.auth_manager.access_token = "test_access_token"
        self.auth_manager.refresh_token = "test_refresh_token"
        self.auth_manager.token_expires_at = time.time() + 3600
        
        # Save tokens
        self.auth_manager._save_tokens()
        
        # Verify file exists
        self.assertTrue(os.path.exists(self.temp_file.name))
        
        # Clear tokens
        self.auth_manager.clear_tokens()
        
        # Verify tokens are cleared
        self.assertIsNone(self.auth_manager.access_token)
        self.assertIsNone(self.auth_manager.refresh_token)
        self.assertIsNone(self.auth_manager.token_expires_at)
        
        # Verify file is removed
        self.assertFalse(os.path.exists(self.temp_file.name))
    
    @patch('aiohttp.ClientSession')
    @async_test
    async def test_refresh_access_token(self, MockClientSession):
        """Test refreshing an access token"""
        # Set up token data
        self.auth_manager.refresh_token = "test_refresh_token"
        
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_json = AsyncMock(return_value={
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600
        })
        mock_response.json = mock_json
        
        # Set up mock session
        mock_session = MagicMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.close = AsyncMock()
        MockClientSession.return_value = mock_session
        
        # Call refresh_access_token
        result = await self.auth_manager.refresh_access_token()
        
        # Verify post called with correct parameters
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args[1]
        self.assertEqual(call_args['data']['refresh_token'], "test_refresh_token")
        self.assertEqual(call_args['data']['grant_type'], "refresh_token")
        
        # Verify token data updated
        self.assertEqual(self.auth_manager.access_token, "new_access_token")
        self.assertEqual(self.auth_manager.refresh_token, "new_refresh_token")
        self.assertEqual(self.auth_manager.token_type, "Bearer")
        self.assertIsNotNone(self.auth_manager.token_expires_at)
        
        # Verify tokens saved to file
        with open(self.temp_file.name, 'r') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data['access_token'], "new_access_token")
        self.assertEqual(saved_data['refresh_token'], "new_refresh_token")
    
    @patch('aiohttp.ClientSession')
    @async_test
    async def test_refresh_access_token_error(self, MockClientSession):
        """Test error handling when refreshing token"""
        # Set up token data
        self.auth_manager.refresh_token = "invalid_refresh_token"
        
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status = 400
        mock_json = AsyncMock(return_value={
            "error": "invalid_grant",
            "error_description": "Invalid refresh token"
        })
        mock_response.json = mock_json
        mock_response.text = AsyncMock(return_value='{"error":"invalid_grant","error_description":"Invalid refresh token"}')
        
        # Set up mock session
        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.close = AsyncMock()
        MockClientSession.return_value = mock_session
        
        # Call refresh_access_token and expect error
        with self.assertRaises(KickAuthManagerError):
            await self.auth_manager.refresh_access_token()
        
        # Verify session was closed
        mock_session.close.assert_called_once()
    
    @patch('aiohttp.ClientSession')
    @async_test
    async def test_get_valid_token_current(self, MockClientSession):
        """Test get_valid_token when current token is valid"""
        # Set up token data
        self.auth_manager.access_token = "current_access_token"
        self.auth_manager.token_expires_at = time.time() + 3600
        
        # Call get_valid_token
        token = await self.auth_manager.get_valid_token()
        
        # Verify token returned and no refresh called
        self.assertEqual(token, "current_access_token")
        MockClientSession.assert_not_called()
    
    @patch('kickbot.kick_auth_manager.KickAuthManager.refresh_access_token')
    @async_test
    async def test_get_valid_token_expired(self, mock_refresh):
        """Test get_valid_token when current token is expired"""
        # Set up token data
        self.auth_manager.access_token = "expired_access_token"
        self.auth_manager.refresh_token = "test_refresh_token"
        self.auth_manager.token_expires_at = time.time() - 60  # Expired 1 minute ago
        
        # Set up mock refresh to update token
        new_tokens = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }
        mock_refresh.return_value = new_tokens  # Return value from the mock
        
        # Simulate what the refresh would do
        def side_effect():
            self.auth_manager.access_token = "new_access_token"  
            self.auth_manager.refresh_token = "new_refresh_token"
            self.auth_manager.token_expires_at = time.time() + 3600
            return new_tokens
            
        mock_refresh.side_effect = side_effect
        
        # Call get_valid_token
        token = await self.auth_manager.get_valid_token()
        
        # Verify refresh called and new token returned
        mock_refresh.assert_called_once()
        self.assertEqual(token, "new_access_token")
    
    @async_test
    async def test_get_valid_token_no_tokens(self):
        """Test get_valid_token when no tokens available"""
        # Ensure no tokens are set
        self.auth_manager.access_token = None
        self.auth_manager.refresh_token = None
        
        # Call get_valid_token and expect error
        with self.assertRaises(KickAuthManagerError):
            await self.auth_manager.get_valid_token()

if __name__ == '__main__':
    unittest.main() 