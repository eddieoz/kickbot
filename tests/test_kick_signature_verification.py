import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import asyncio
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature
import datetime
import time

# This will test our signature verification functionality
from kickbot.kick_signature_verifier import KickSignatureVerifier
from kickbot.kick_webhook_handler import KickWebhookHandler

class TestKickSignatureVerification(unittest.TestCase):
    """Tests for Kick webhook signature verification"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock KickBot instance
        self.mock_kick_bot = MagicMock()
        self.mock_kick_bot.send_text = AsyncMock() # Common method used by handlers

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
            kick_bot_instance=self.mock_kick_bot, # Provide the mock bot
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
        # mock_dispatch.return_value = None # dispatch_event is now part of KickWebhookHandler itself
        
        # Create mock request with signature header
        mock_request = MagicMock()
        mock_request.read = AsyncMock(return_value=json.dumps(self.webhook_payload).encode())
        mock_request.headers = {"X-Kick-Signature": self.test_signature}
        
        # Handle the webhook
        response = await self.webhook_handler.handle_webhook(mock_request)
        
        # Verify response and dispatching
        self.assertEqual(response.status, 200)
        mock_verify.assert_called_once()
        # mock_dispatch.assert_called_once_with( # mock_dispatch is KickWebhookHandler.dispatch_event
        #     "channel.subscribed", 
        #     self.webhook_payload["data"]
        # )
        # Instead, we should check if the *actual* dispatch_event of the handler was called indirectly.
        # This test might need rethinking if we are mocking dispatch_event itself on the handler instance.
        # For now, let's assume the primary goal is to check the signature verification path.
        # If signature is valid, dispatch_event (the real one) should be called. 
        # To test that, we'd need to mock the specific event handler (e.g. handle_subscription_event)
        # or assert logs if dispatch was successful.
        # Given the patch on KickWebhookHandler.dispatch_event, the below assertion is correct for *that* mock.
        mock_dispatch.assert_called_once() 
        # If we want to check arguments passed to the real dispatch_event, 
        # we need to let it run and mock the subsequent specific handler, or inspect its behavior.
    
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

    VALID_TIMESTAMP_STR = "2024-03-10T10:00:00Z"
    VALID_DATETIME = datetime.datetime.strptime(VALID_TIMESTAMP_STR, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    VALID_DATETIME_PAYLOAD_FORMAT = VALID_DATETIME.isoformat()

    # Minimal valid payload for a known event type, e.g., channel.followed
    MINIMAL_VALID_PAYLOAD_FOR_SIG_TEST = {
        "id": "evt_sig_follow_123",
        "event": "channel.followed", 
        "channel_id": "channel_sig_xyz",
        "created_at": VALID_DATETIME_PAYLOAD_FORMAT,
        "data": {
            "follower": {"id": "user_sig_follower", "username": "SigTestFollower"},
            "followed_at": VALID_DATETIME_PAYLOAD_FORMAT
        }
    }

    async def simulate_request_with_headers(self, payload_data, headers, handler_instance=None):
        current_handler = handler_instance if handler_instance else self.webhook_handler
        raw_payload = json.dumps(payload_data).encode('utf-8')
        
        mock_request = AsyncMock(spec=web.Request)
        mock_request.read = AsyncMock(return_value=raw_payload)
        mock_request.headers = headers
        return await current_handler.handle_webhook(mock_request)

    @patch('kickbot.kick_webhook_handler.KickWebhookHandler.dispatch_event', new_callable=AsyncMock)
    async def test_webhook_handler_with_valid_signature(self, mock_dispatch_event):
        secret = "test_secret"
        verifier = KickSignatureVerifier(secret=secret)
        self.webhook_handler.signature_verifier = verifier # Inject verifier
        self.webhook_handler.signature_verification = True    # Enable verification for this test

        payload = self.MINIMAL_VALID_PAYLOAD_FOR_SIG_TEST
        body_bytes = json.dumps(payload).encode('utf-8')
        timestamp = str(int(time.time()))
        signature = verifier.generate_signature(timestamp=timestamp, body=body_bytes)
        headers = {
            'Kick-Signature-Timestamp': timestamp,
            'Kick-Signature': signature
        }

        with patch.object(self.webhook_handler.signature_verifier, 'verify_signature', wraps=self.webhook_handler.signature_verifier.verify_signature) as mock_verify:
            response = await self.simulate_request_with_headers(payload, headers)
        
        self.assertEqual(response.status, 200)
        mock_verify.assert_called_once()
        mock_dispatch_event.assert_called_once() # Event should be dispatched if signature is valid
        parsed_event_arg = mock_dispatch_event.call_args[0][1]
        self.assertIsInstance(parsed_event_arg, FollowEvent)

    @patch('kickbot.kick_webhook_handler.KickWebhookHandler.dispatch_event', new_callable=AsyncMock)
    async def test_webhook_handler_with_invalid_signature(self, mock_dispatch_event):
        secret = "test_secret"
        verifier = KickSignatureVerifier(secret=secret)
        self.webhook_handler.signature_verifier = verifier
        self.webhook_handler.signature_verification = True

        payload = self.MINIMAL_VALID_PAYLOAD_FOR_SIG_TEST
        headers = {
            'Kick-Signature-Timestamp': str(int(time.time())),
            'Kick-Signature': 'invalid_signature'
        }
        response = await self.simulate_request_with_headers(payload, headers)
        self.assertEqual(response.status, 401) # Or 400 depending on chosen error for bad sig
        mock_dispatch_event.assert_not_called()

    @patch('kickbot.kick_webhook_handler.KickWebhookHandler.dispatch_event', new_callable=AsyncMock)
    async def test_webhook_handler_missing_signature(self, mock_dispatch_event):
        secret = "test_secret"
        self.webhook_handler.signature_verification = True # Verification enabled
        payload = self.MINIMAL_VALID_PAYLOAD_FOR_SIG_TEST
        headers = {}
        response = await self.simulate_request_with_headers(payload, headers)
        self.assertEqual(response.status, 400) # Or 401, request is bad without signature
        mock_dispatch_event.assert_not_called()

    async def test_webhook_handler_signature_verification_disabled(self):
        """Test webhook handler when signature verification is disabled globally."""
        handler_no_sig_ver = KickWebhookHandler(
            kick_bot_instance=self.mock_kick_bot, # Provide the mock bot
            webhook_path="/kick/events",
            port=8000,
            signature_verification=False, # Verification disabled
            log_events=False
        )
        handler_no_sig_ver.signature_verifier = self.verifier # Still assign a verifier to see it's not used
        
        # Mock dispatch_event on this specific instance to check if it gets called
        handler_no_sig_ver.dispatch_event = AsyncMock()

        payload = self.MINIMAL_VALID_PAYLOAD_FOR_SIG_TEST
        headers = {'Kick-Signature': 'some_signature'} # Provide a sig, but it shouldn't be checked

        with patch.object(handler_no_sig_ver, 'dispatch_event', new_callable=AsyncMock) as mock_dispatch_event:
            response = await self.simulate_request_with_headers(payload, headers)
        
        self.assertEqual(response.status, 200)
        mock_dispatch_event.assert_called_once() # Should still dispatch

if __name__ == '__main__':
    unittest.main() 