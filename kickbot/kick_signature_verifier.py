import aiohttp
import logging
import base64
from typing import Optional
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kick_signature_verifier")

class KickSignatureVerifier:
    """
    Handles verification of signatures on webhooks from Kick.com.
    
    This class fetches the public key from Kick's API and uses it to verify
    the signature on incoming webhooks, ensuring they are authentic and have
    not been tampered with.
    """
    
    def __init__(self):
        """Initialize the signature verifier."""
        self.public_key = None
        self.public_key_url = "https://api.kick.com/public/v1/public-key"
    
    async def fetch_public_key(self):
        """
        Fetch the public key from Kick API.
        
        Returns:
            The loaded public key object
        
        Raises:
            Exception: If there's an error fetching or loading the key
        """
        logger.info(f"Fetching public key from {self.public_key_url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.public_key_url,
                    headers={"Accept": "application/json"}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to fetch public key: {response.status} - {error_text}")
                        raise Exception(f"Failed to fetch public key: {response.status}")
                    
                    data = await response.json()
                    
                    if "data" not in data or "public_key" not in data["data"]:
                        logger.error(f"Invalid response format: {data}")
                        raise Exception("Invalid public key response format")
                    
                    public_key_pem = data["data"]["public_key"]
                    logger.info("Successfully fetched public key")
                    
                    # Load the PEM-encoded public key
                    try:
                        public_key = load_pem_public_key(public_key_pem.encode())
                        self.public_key = public_key
                        return public_key
                    except Exception as e:
                        logger.error(f"Failed to load public key: {e}")
                        raise Exception(f"Failed to load public key: {e}")
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error while fetching public key: {e}")
            raise Exception(f"HTTP error while fetching public key: {e}")
    
    async def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify the signature of a webhook payload.
        
        Args:
            payload: The raw webhook payload bytes
            signature: The base64-encoded signature from the X-Kick-Signature header
            
        Returns:
            True if the signature is valid, False otherwise
        """
        try:
            # Ensure we have the public key
            if not self.public_key:
                await self.fetch_public_key()
            
            # Decode the base64 signature
            try:
                signature_bytes = base64.b64decode(signature)
            except Exception as e:
                logger.error(f"Failed to decode signature: {e}")
                return False
            
            # Verify the signature
            try:
                self.public_key.verify(
                    signature_bytes,
                    payload,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                # If verify doesn't raise an exception, the signature is valid
                logger.info("Signature verification successful")
                return True
            
            except InvalidSignature:
                logger.warning("Invalid signature detected")
                return False
            
            except Exception as e:
                logger.error(f"Error during signature verification: {e}")
                return False
        
        except Exception as e:
            logger.error(f"Unexpected error in signature verification: {e}")
            return False 