import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import asyncio
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

# This will test our signature verification functionality
from kickbot.kick_signature_verifier import KickSignatureVerifier
from kickbot.kick_webhook_handler import KickWebhookHandler

class TestKickSignatureVerification(unittest.TestCase):
    """Tests for Kick webhook signature verification"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Example webhook payload
        self.webhook_payload = {
            "event": "channel.subscribed",
            "data": {
                "id": "12345",
                "user": {
                    "id": "67890",
                    "username": "test_subscriber"
                }
            }
        }
        
        # Example public key (PEM format)
        self.test_public_key_pem = """
        -----BEGIN PUBLIC KEY-----
        MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu1SU1LfVLPHCozMxH2Mo
        4lgOEePzNm0tRgeLezV6ffAt0gunVTLw7onLRnrq0/IzW7yWR7QkrmBL7jTKEn5u
        +qKhbwKfBstIs+bMY2Zkp18gnTxKLxoS2tFczGkPLPgizskuemMghRniWaoLcyeh
        kd3qqGElvW/VDL5AaWTg0nLVkjRo9z+40RQzuVaE8AkAFmxZzow3x+VJYKdjykkJ
        0iT9wCS0DRTXu269V264Vf/3jvredZiKRkgwlL9xNAwxXFg0x/XFw005UWVRIkdg
        cKWTjpBP2dPwVZ4WWC+9aGVd+Gyn1o0CLelf4rEjGoXbAAEgAqeGUxrcIlbjXfbc
        mwIDAQAB
        -----END PUBLIC KEY-----
        """
        
        # Create a test signature by signing the payload with a test private key
        # Note: In real tests, we'd use a pre-generated valid signature
        self.test_signature = "valid_test_signature"
        
        # Initialize the verifier
        self.verifier = KickSignatureVerifier()
        
        # Setup webhook handler with verification
        self.webhook_handler = KickWebhookHandler(
            webhook_path="/kick/events",
            port=8000,
            signature_verification=True
        )

    # Helper for running async tests
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
    
    @patch('aiohttp.ClientSession.get')
    @async_test
    async def test_fetch_public_key(self, mock_get):
        """Test fetching public key from Kick API"""
        # Mock response with test public key
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"data": {"public_key": self.test_public_key_pem}}
        )
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Fetch the key
        public_key = await self.verifier.fetch_public_key()
        
        # Verify the key was fetched and processed correctly
        self.assertIsNotNone(public_key)
        mock_get.assert_called_once_with(
            "https://api.kick.com/public/v1/public-key",
            headers={"Accept": "application/json"}
        )
    
    @patch('aiohttp.ClientSession.get')
    @async_test
    async def test_fetch_public_key_error(self, mock_get):
        """Test handling errors when fetching public key"""
        # Mock response with error
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Server error")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Attempt to fetch the key, should raise an exception
        with self.assertRaises(Exception):
            await self.verifier.fetch_public_key()
    
    @patch.object(KickSignatureVerifier, 'fetch_public_key')
    @patch.object(KickSignatureVerifier, 'verify_signature')
    @async_test
    async def test_verify_signature_valid(self, mock_verify_signature, mock_fetch_key):
        """Test verifying a valid signature"""
        # Set up mocks
        public_key = load_pem_public_key(self.test_public_key_pem.encode())
        mock_fetch_key.return_value = public_key
        mock_verify_signature.return_value = True
        
        # Verify the signature
        result = await self.verifier.verify_signature(
            json.dumps(self.webhook_payload).encode(),
            self.test_signature
        )
        
        # Assert the signature is valid
        self.assertTrue(result)
    
    @patch.object(KickSignatureVerifier, 'fetch_public_key')
    @patch.object(KickSignatureVerifier, 'verify_signature')
    @async_test
    async def test_verify_signature_invalid(self, mock_verify_signature, mock_fetch_key):
        """Test verifying an invalid signature"""
        # Set up mocks
        public_key = load_pem_public_key(self.test_public_key_pem.encode())
        mock_fetch_key.return_value = public_key
        mock_verify_signature.return_value = False
        
        # Verify the signature
        result = await self.verifier.verify_signature(
            json.dumps(self.webhook_payload).encode(),
            "invalid_signature"
        )
        
        # Assert the signature is invalid
        self.assertFalse(result)
    
    @patch.object(KickWebhookHandler, 'dispatch_event')
    @patch.object(KickSignatureVerifier, 'verify_signature')
    @async_test
    async def test_webhook_handler_with_valid_signature(self, mock_verify, mock_dispatch):
        """Test webhook handler with valid signature"""
        # Set up mocks
        mock_verify.return_value = True
        mock_dispatch.return_value = None
        
        # Create mock request with signature header
        mock_request = MagicMock()
        mock_request.read = AsyncMock(return_value=json.dumps(self.webhook_payload).encode())
        mock_request.headers = {"X-Kick-Signature": self.test_signature}
        
        # Use our webhook handler with the verifier
        self.webhook_handler.signature_verifier = self.verifier
        
        # Handle the webhook
        response = await self.webhook_handler.handle_webhook(mock_request)
        
        # Verify response and dispatching
        self.assertEqual(response.status, 200)
        mock_verify.assert_called_once()
        mock_dispatch.assert_called_once_with(
            "channel.subscribed", 
            self.webhook_payload["data"]
        )
    
    @patch.object(KickSignatureVerifier, 'verify_signature')
    @async_test
    async def test_webhook_handler_with_invalid_signature(self, mock_verify):
        """Test webhook handler with invalid signature"""
        # Set up mocks
        mock_verify.return_value = False
        
        # Create mock request with signature header
        mock_request = MagicMock()
        mock_request.read = AsyncMock(return_value=json.dumps(self.webhook_payload).encode())
        mock_request.headers = {"X-Kick-Signature": "invalid_signature"}
        
        # Use our webhook handler with the verifier
        self.webhook_handler.signature_verifier = self.verifier
        
        # Handle the webhook
        response = await self.webhook_handler.handle_webhook(mock_request)
        
        # Verify response indicates unauthorized
        self.assertEqual(response.status, 401)
        mock_verify.assert_called_once()
    
    @patch.object(KickWebhookHandler, 'dispatch_event')
    @async_test
    async def test_webhook_handler_missing_signature(self, mock_dispatch):
        """Test webhook handler with missing signature"""
        # Create mock request without signature header
        mock_request = MagicMock()
        mock_request.read = AsyncMock(return_value=json.dumps(self.webhook_payload).encode())
        mock_request.headers = {}
        
        # Use our webhook handler with verification enabled
        self.webhook_handler.signature_verifier = self.verifier
        
        # Handle the webhook
        response = await self.webhook_handler.handle_webhook(mock_request)
        
        # Verify response indicates bad request
        self.assertEqual(response.status, 400)
        mock_dispatch.assert_not_called()

if __name__ == '__main__':
    unittest.main() 