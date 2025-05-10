import os
import hashlib
import base64
import secrets # For a cryptographically strong random number generator
import aiohttp # ADDED
import json
import time
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from urllib.parse import urlencode, quote_plus # Already here, good
import logging # ADDED

# Configure logger for this module
logger = logging.getLogger(__name__)

# Load environment variables (assuming .env is handled by a library like python-dotenv at a higher level or run environment)
KICK_CLIENT_ID = os.environ.get("KICK_CLIENT_ID")
KICK_CLIENT_SECRET = os.environ.get("KICK_CLIENT_SECRET")
KICK_REDIRECT_URI = os.environ.get("KICK_REDIRECT_URI")
KICK_SCOPES = os.environ.get("KICK_SCOPES", "user:read channel:read chat:write events:subscribe") # Expanded default scopes

# Default token file location
DEFAULT_TOKEN_FILE = "kickbot_tokens.json"

# Time in seconds before actual expiry to consider the token as expired, to allow for refresh.
TOKEN_EXPIRY_BUFFER = 60

# PKCE Helper Functions
def generate_code_verifier(length: int = 128) -> str:
    """
    Generates a cryptographically secure random string to be used as the PKCE code verifier.
    The length should be between 43 and 128 characters.
    """
    if not (43 <= length <= 128):
        raise ValueError("Code verifier length must be between 43 and 128 characters.")
    return secrets.token_urlsafe(length)[:length] # Ensure exact length after urlsafe encoding

def generate_code_challenge(verifier: str) -> str:
    """
    Generates the PKCE code challenge from a given code verifier.
    The challenge is the BASE64 URL-encoded SHA256 hash of the verifier.
    """
    sha256_hash = hashlib.sha256(verifier.encode('utf-8')).digest()
    # Base64 URL encode: replace + with -, / with _, and remove = padding
    base64_encoded = base64.urlsafe_b64encode(sha256_hash).decode('utf-8')
    return base64_encoded.rstrip('=')

class KickAuthManagerError(Exception):
    """Custom exception for KickAuthManager errors."""
    pass

class KickAuthManager:
    def __init__(self, client_id: str = None, client_secret: str = None, redirect_uri: str = None, scopes: str = None, token_file: str = None):
        self.logger = logging.getLogger(__name__) # Initialize logger for the class instance
        self.client_id = client_id or KICK_CLIENT_ID
        self.client_secret = client_secret or KICK_CLIENT_SECRET
        self.redirect_uri = redirect_uri or KICK_REDIRECT_URI
        # Ensure scopes is a list of strings for proper joining later
        _scopes_input = scopes or KICK_SCOPES
        if isinstance(_scopes_input, str):
            self.scopes = _scopes_input.split()
        elif isinstance(_scopes_input, (list, tuple)):
            self.scopes = list(_scopes_input)
        else:
            self.scopes = [] # Default to empty list if type is unexpected
            self.logger.warning(f"Unexpected type for scopes: {type(_scopes_input)}. Defaulting to empty scopes.")

        self.token_file_path = Path(token_file or DEFAULT_TOKEN_FILE).resolve() # Use pathlib for robust path handling
        
        self.token_endpoint = "https://id.kick.com/oauth/token"
        self.authorize_endpoint = "https://id.kick.com/oauth/authorize"

        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[float] = None # Unix timestamp for expiry
        self.token_type: Optional[str] = "Bearer" # Default, usually Bearer
        self.granted_scopes: Optional[str] = None # Scopes actually granted

        if not self.client_id:
            raise ValueError("KICK_CLIENT_ID is not set in environment or passed to constructor.")
        if not self.redirect_uri:
            raise ValueError("KICK_REDIRECT_URI is not set in environment or passed to constructor.")
        # Client secret might not be directly used in the PKCE flow by the client app itself but is good to have loaded.

        self._load_tokens()

    def get_authorization_url(self) -> tuple[str, str]:
        """
        Generates the full authorization URL and the code_verifier.
        The code_verifier needs to be stored by the calling application to be used later in the token exchange.
        """
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": self._generate_state()
        }
        # Using urllib.parse.urlencode to correctly format query parameters
        query_string = urlencode(params, quote_via=quote_plus)
        
        # The Kick documentation specifies the OAuth server is id.kick.com
        # Need to confirm the exact path for the authorization endpoint from Kick documentation.
        # Assuming /oauth/authorize based on common patterns and Auth0.
        # Step 4 of App Setup mentions: "KICK will redirect control to your redirectURL with a code to complete the OAuth 2.0 Code Grant flow with PKCE."
        # The "OAuth 2.1" page mentions the host is https://id.kick.com
        # Let's assume the path is /connect/authorize or similar, as commonly found.
        # For now, using a placeholder path, this needs to be verified from Kick's specific OAuth documentation if available,
        # or inferred from their example if they provide one.
        # The Auth0 example uses /authorize
        
        auth_url = f"{self.authorize_endpoint}?{query_string}" # Placeholder, confirm exact path
        # The Kick documentation refers to https://id.kick.com as the OAuth server.
        # Let's check Kick's App Setup Step 4: "Upon successful authorization, KICK will redirect control to your redirectURL with a code to complete the OAuth 2.0 Code Grant flow with PKCE."
        # It doesn't give the explicit authorize endpoint path.
        # The page "OAuth 2.1" (https://docs.kick.com/getting-started/generating-tokens-oauth2-flow) also mentions the host https://id.kick.com.
        # Standard OAuth endpoints are typically /authorize and /token.
        # Let's stick with common practice for now.
        
        self.logger.info(f"Generated authorization URL (first 80 chars): {auth_url[:80]}...")
        self.logger.debug(f"Full authorization URL: {auth_url}")
        
        return auth_url, code_verifier

    async def exchange_code_for_tokens(self, code: str, code_verifier: str) -> dict:
        """
        Exchanges the authorization code for an access token and refresh token.
        Raises KickAuthManagerError on failure.
        """
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
        }
        
        # Create a session
        session = aiohttp.ClientSession()
        try:
            # Make the POST request to the token endpoint
            response = await session.post(self.token_endpoint, data=payload)
            
            # Check response status
            if response.status == 200:
                try:
                    # Try to parse the response as JSON
                    result = await response.json()
                    
                    # Store the tokens
                    self._update_token_data(result)
                    self._save_tokens()
                    
                    return result
                except aiohttp.ContentTypeError as e:
                    # Handle cases where response is not JSON despite 200 OK
                    text_response = await response.text()
                    raise KickAuthManagerError(
                        f"Token endpoint returned 200 OK but non-JSON response: {text_response}"
                    )
            else:
                # Handle error responses
                error_text = "Unknown error"
                error_details = {}
                try:
                    error_details = await response.json()  # Try to get JSON error details
                    error_text = error_details.get("error_description", error_details.get("error", str(error_details)))
                except aiohttp.ContentTypeError:
                    error_text = await response.text()  # Fallback to text if not JSON
                except Exception:  # Catch any other parsing error
                    error_text = "Failed to parse error response"
                
                # If refresh token is invalid/revoked, clear it.
                actual_error_code = error_details.get("error")
                if response.status in [400, 401] and actual_error_code == "invalid_grant":
                    self.clear_tokens() # Clear all tokens as refresh failed, likely needs re-auth
                
                # Log the full error details for better debugging
                self.logger.error(f"Full error details from token endpoint: {error_details}")
                
                raise KickAuthManagerError(
                    f"Error exchanging code for tokens: {response.status} - {error_text}. Details: {error_details}"
                )
        except aiohttp.ClientError as e:  # Changed from generic ClientError to aiohttp.ClientError
            # Handle network errors or other client-side issues
            self.logger.error(f"AIOHTTP client error during token exchange: {e}", exc_info=True)
            raise KickAuthManagerError(f"AIOHTTP client error during token exchange")
        except json.JSONDecodeError as e:
            text_response = await response.text()
            raise KickAuthManagerError(f"Failed to decode JSON response from token exchange: {e}. Response text: {text_response}")
        except KickAuthManagerError:
            # Re-raise KickAuthManagerError without modification
            raise
        except Exception:
            # Catch-all for unexpected errors
            raise KickAuthManagerError(f"Unexpected error during token exchange")
        finally:
            # Always close the session
            await session.close()

    async def refresh_access_token(self) -> Dict[str, Any]:
        """
        Uses the refresh token to obtain a new access token.
        Returns the new token data on success.
        Raises KickAuthManagerError on failure.
        """
        if not self.refresh_token:
            raise KickAuthManagerError("No refresh token available to refresh the access token.")
            
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret, # Potentially required for confidential clients
            "scope": " ".join(self.scopes), # Often scopes are re-requested or re-asserted
        }
        
        # Create a session
        session = aiohttp.ClientSession()
        try:
            # Make the POST request to the token endpoint
            response = await session.post(self.token_endpoint, data=payload)
            
            # Check response status
            if response.status == 200:
                try:
                    # Try to parse the response as JSON
                    result = await response.json()
                    
                    # Update token data with new tokens
                    self._update_token_data(result)
                    self._save_tokens()
                    
                    return result
                except aiohttp.ContentTypeError:
                    # Handle cases where response is not JSON despite 200 OK
                    text_response = await response.text()
                    raise KickAuthManagerError(
                        f"Token endpoint returned 200 OK but non-JSON response: {text_response}"
                    )
            else:
                # Handle error responses
                error_text = "Unknown error"
                error_details = {} # Initialize error_details
                try:
                    error_details = await response.json()  # Try to get JSON error details
                    error_text = error_details.get("error_description", error_details.get("error", str(error_details)))
                except aiohttp.ContentTypeError:
                    error_text = await response.text()  # Fallback to text if not JSON
                except Exception:  # Catch any other parsing error
                    error_text = "Failed to parse error response"
                
                # If refresh token is invalid/revoked, clear it.
                # Check the 'error' field directly for 'invalid_grant'
                actual_error_code = error_details.get("error")
                if response.status in [400, 401] and actual_error_code == "invalid_grant":
                    self.clear_tokens() # Clear all tokens as refresh failed, likely needs re-auth
                raise KickAuthManagerError(
                    f"Error refreshing access token: {response.status} - {error_text}"
                )
        except aiohttp.ClientError:
            # Handle network errors or other client-side issues
            raise KickAuthManagerError(f"AIOHTTP client error during token refresh")
        except json.JSONDecodeError as e:
            text_response = await response.text()
            raise KickAuthManagerError(f"Failed to decode JSON response from token refresh: {e}. Response text: {text_response}")
        except KickAuthManagerError:
            # Re-raise KickAuthManagerError without modification
            raise
        except Exception:
            # Catch-all for unexpected errors
            raise KickAuthManagerError(f"Unexpected error during token refresh")
        finally:
            # Always close the session
            await session.close()

    async def get_valid_token(self) -> str:
        """
        Returns a valid access token. If the current token is expired or close to expiry,
        it automatically refreshes it.
        
        Returns:
            A valid access token string
            
        Raises:
            KickAuthManagerError: If unable to get a valid token
        """
        # Check if we have a token and if it's expired or about to expire (within 60 seconds)
        if not self.access_token or not self.token_expires_at or time.time() > (self.token_expires_at - 60):
            if self.refresh_token:
                # Refresh the token
                await self.refresh_access_token()
            else:
                raise KickAuthManagerError("No valid token available and no refresh token to get a new one.")
        
        return self.access_token
    
    def _update_token_data(self, token_response: Dict[str, Any]) -> None:
        """
        Updates the token data from a token response.
        
        Args:
            token_response: The response from the token endpoint
        """
        self.access_token = token_response.get("access_token")
        # Only update refresh token if a new one is provided
        if "refresh_token" in token_response:
            self.refresh_token = token_response.get("refresh_token")
        self.token_type = token_response.get("token_type", "Bearer")
        
        # Calculate expiry time
        expires_in = token_response.get("expires_in")
        if expires_in is not None:
            try:
                self.token_expires_at = time.time() + int(expires_in)
            except ValueError:
                raise KickAuthManagerError(f"Invalid 'expires_in' value received: {expires_in}")
        else: # If expires_in is not provided, we can't know when it expires.
              # Set to None or handle as an error/warning. For now, set to None.
            self.token_expires_at = None
        
        self.granted_scopes = token_response.get("scope") # Store granted scopes
    
    def _save_tokens(self) -> None:
        """
        Saves the current tokens to the token file.
        """
        if not self.access_token:
            return
            
        token_data_to_save = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expires_at": self.token_expires_at,
            "token_type": self.token_type,
            "client_id": self.client_id, # Save client_id to ensure tokens are for the right app
            "granted_scopes": self.granted_scopes
        }
        
        try:
            self.token_file_path.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists
            with open(self.token_file_path, "w") as f:
                json.dump(token_data_to_save, f, indent=4)
        except IOError as e:
            # Log this error appropriately in a real app
            self.logger.warning(f"Could not save tokens to file {self.token_file_path}: {e}")
            # Optionally raise KickAuthManagerError or handle as non-critical
    
    def _load_tokens(self) -> None:
        """
        Loads tokens from the token file if it exists and is valid.
        """
        if not self.token_file_path.exists():
            return
            
        try:
            with open(self.token_file_path, "r") as f:
                loaded_data = json.load(f)

            # Validate that the loaded tokens are for the current client_id
            if loaded_data.get("client_id") != self.client_id:
                self.logger.warning(f"Tokens in {self.token_file_path} are for a different client_id ('{loaded_data.get('client_id')}' vs '{self.client_id}'). Clearing tokens.")
                self.clear_tokens() # Clear the file as it's for a different app
                return

            self.access_token = loaded_data.get("access_token")
            self.refresh_token = loaded_data.get("refresh_token")
            self.token_expires_at = loaded_data.get("token_expires_at")
            self.token_type = loaded_data.get("token_type", "Bearer")
            self.granted_scopes = loaded_data.get("granted_scopes")
            
            # Basic validation
            if not self.access_token or not isinstance(self.token_expires_at, (int, float)):
                self.logger.warning(f"Invalid or incomplete token data in {self.token_file_path}. Missing keys or invalid type. Clearing tokens.")
                self.clear_tokens()
                return
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Error decoding token file {self.token_file_path}: {e}. Deleting corrupted file.")
            # Optionally, attempt to delete or rename the corrupted file
            self.clear_tokens() # A simple approach: clear if corrupted
        except IOError as e:
            self.logger.warning(f"Could not read token file {self.token_file_path}: {e}")
        except Exception as e: # Catch any other unexpected error during load
            self.logger.error(f"Unexpected error loading tokens: {e}")
            self.clear_tokens() # Clear in-memory tokens if load fails unexpectedly

    def is_access_token_valid(self, buffer_seconds: int = TOKEN_EXPIRY_BUFFER) -> bool:
        """Checks if the current access token is present and not expired (considering a buffer)."""
        if not self.access_token:
            return False
        if self.token_expires_at is None: # If no expiry time, assume it's not valid or needs refresh
            return False 
        return time.time() < (self.token_expires_at - buffer_seconds)

    def clear_tokens(self) -> None:
        """
        Clears all token data and removes the token file.
        """
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.token_type = None
        self.granted_scopes = None
        
        # Remove the token file if it exists
        self.clear_tokens_file()

    def clear_tokens_file(self) -> None:
        """Deletes the token file."""
        try:
            if self.token_file_path.exists():
                self.token_file_path.unlink()
        except IOError as e:
            self.logger.warning(f"Could not delete token file {self.token_file_path}: {e}")

    def _generate_state(self) -> str:
        # Implement the logic to generate a state parameter
        # This is a placeholder and should be replaced with the actual implementation
        return secrets.token_urlsafe(16)

# Example usage (for manual testing or a helper script):
# if __name__ == "__main__":
#     # Ensure KICK_CLIENT_ID, KICK_REDIRECT_URI are set in your environment
#     if not KICK_CLIENT_ID or not KICK_REDIRECT_URI:
#         print("Please set KICK_CLIENT_ID and KICK_REDIRECT_URI environment variables.")
#     else:
#         auth_manager = KickAuthManager()
#         auth_url, verifier = auth_manager.get_authorization_url()
#         print(f"Please open the following URL in your browser to authorize: {auth_url}")
#         print(f"After authorization, you will be redirected to your redirect_uri with a 'code'.")
#         print(f"Store this code verifier to use with the authorization code: {verifier}")
        
        # The next step would be to capture the 'code' from the redirect
        # and then call:
        # tokens = await auth_manager.exchange_code_for_tokens(auth_code_from_redirect, stored_verifier)
        # print(f"Tokens: {tokens}")
        # And then save tokens (especially refresh_token) securely. 