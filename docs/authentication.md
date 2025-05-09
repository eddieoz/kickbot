# Kick API Authentication Documentation

This document provides a detailed explanation of the authentication methods implemented in Sr_Botoshi to interact with Kick.

## Overview

Sr_Botoshi supports two distinct authentication mechanisms:

1. **Traditional Username/Password Authentication** - Used for the chatbot functionality
2. **OAuth 2.0 with PKCE** - Used for the official Kick API integration

## 1. Traditional Username/Password Authentication

This authentication method is used for the original chatbot functionality, using `KickClient`.

### Process

1. **Initialize Client** - Create a `KickClient` instance with username and password
   ```python
   client = KickClient("bot_email@example.com", "bot_password")
   ```

2. **Token Acquisition** - The client automatically performs these steps:
   - Makes a request to `https://kick.com/kick-token-provider` to get initial tokens and cookies
   - Submits login credentials to `https://kick.com/mobile/login`
   - Handles 2-factor authentication if required (prompts for code entry in console)
   - Retrieves and stores the authentication token

3. **Two-Factor Authentication** - When 2FA is enabled on the account:
   - Kick sends a verification code to the account's email or phone
   - The bot waits for user input of the 2FA code in the console
   - The code is submitted to complete authentication

4. **User Information** - After successful authentication:
   - The bot requests user information from `https://kick.com/api/v1/user`
   - Stores the user data, including username and user ID

This authentication method allows the bot to interact with chat and perform moderator actions.

## 2. OAuth 2.0 with PKCE Authentication

This newer authentication method is used to access the official Kick API using OAuth 2.0 with PKCE (Proof Key for Code Exchange), providing more secure and standardized access. It is the required method for subscribing to real-time events like new subscriptions and gifts.

**Core Idea:** The bot owner performs a one-time interactive authorization via a web browser. This process grants the bot an initial set of tokens (access and refresh). The bot then stores these tokens (in `kickbot_tokens.json`) and uses the refresh token to maintain access without further manual intervention, unless the refresh token itself becomes invalid.

### Authentication Flow

#### 2.1 Generate Authorization URL

To initiate the OAuth flow, the `KickAuthManager` is used. This step is typically part of a helper script for the initial authorization.

```python
# From kick_auth_manager.py or a helper script
auth_manager = KickAuthManager(
    client_id="YOUR_KICK_CLIENT_ID",      # Loaded from .env or passed directly
    redirect_uri="YOUR_CONFIGURED_REDIRECT_URI", # E.g., http://localhost:8080/callback
    scopes="events:subscribe user:read" # Or KICK_SCOPES from .env
)
auth_url, code_verifier = auth_manager.get_authorization_url()
# The code_verifier must be temporarily stored to be used in step 2.3
```

This generates:
- A random `code_verifier` (a cryptographically secure random string).
- A `code_challenge` (SHA-256 hash of the `code_verifier`, base64url-encoded).
- An `auth_url` for `https://id.kick.com/oauth2/authorize` containing parameters like `client_id`, `redirect_uri`, `scope`, `response_type=code`, `code_challenge`, and `code_challenge_method=S256`.

#### 2.2 User Authorization (One-Time Manual Step)

This is the interactive part performed by the bot owner:

1.  **Run a Helper Script:** The `scripts/kick_auth_example.py` script is provided to facilitate this one-time authorization. When run (e.g., `python scripts/kick_auth_example.py --authorize`), it will:
    *   Start a temporary local web server to listen on the `redirect_uri` (e.g., `http://localhost:8080/callback`).
    *   Generate the `auth_url` and `code_verifier` (as in step 2.1).
    *   Print the `auth_url` to the console and attempt to open it in the default web browser.
2.  **Grant Access in Browser:** The bot owner visits the `auth_url` in their browser.
    *   They will be prompted to log in to Kick (if not already logged in).
    *   They will be asked to authorize Sr_Botoshi (or the name of your Kick App) for the requested scopes.
3.  **Redirection with Authorization Code:** Upon successful authorization, Kick redirects the browser to the specified `redirect_uri` (e.g., `http://localhost:8080/callback`). The redirect URL will include an `authorization_code` as a query parameter (e.g., `http://localhost:8080/callback?code=SOME_LONG_CODE`).
    *   The local web server run by `scripts/kick_auth_example.py` will capture this `authorization_code`.

#### 2.3 Code Exchange for Tokens

Immediately after the helper script captures the `authorization_code`, it uses it along with the previously generated `code_verifier` to exchange them for tokens. This is done by the `KickAuthManager`:

```python
# Executed by the helper script (e.g., kick_auth_example.py) after capturing the code
# auth_code is the code from the redirect, code_verifier was stored from step 2.1
tokens_response = await auth_manager.exchange_code_for_tokens(auth_code, code_verifier)
# tokens_response contains access_token, refresh_token, expires_in, etc.
```

This sends a POST request to Kick's token endpoint (`https://id.kick.com/oauth2/token`) with the `grant_type="authorization_code"`, `client_id`, `redirect_uri`, `code`, and `code_verifier`.

If successful, Kick responds with:
- `access_token`: The token used to make authenticated API requests.
- `refresh_token`: A long-lived token used to obtain new access tokens when the current one expires.
- `expires_in`: The lifetime of the access token in seconds.
- `token_type`: Typically "Bearer".
- `scope`: The scopes that were actually granted.

#### 2.4 Token Storage

The `KickAuthManager`, upon successful token acquisition (either initial exchange or refresh), automatically saves the relevant token data (access token, refresh token, expiry time, client ID, granted scopes) to a JSON file. 

*   **Default File:** `kickbot_tokens.json` (in the bot's root directory).
*   **Customizable:** The filename can be changed when initializing `KickAuthManager`.
*   **Purpose:** This allows the bot to persist authentication across restarts. When `KickAuthManager` is initialized, it automatically tries to load tokens from this file.
*   **Security for Local Execution:** For Sr_Botoshi, which is intended to run locally on the streamer's machine, this simple file-based storage is considered adequate. Ensure the file is in a location with appropriate user permissions.

```json
// Example content of kickbot_tokens.json
{
    "access_token": "your_access_token_here",
    "refresh_token": "your_refresh_token_here",
    "token_expires_at": 1670000000.0, // Unix timestamp
    "token_type": "Bearer",
    "client_id": "YOUR_KICK_CLIENT_ID",
    "granted_scopes": "events:subscribe user:read"
}
```

On initialization, if `KickAuthManager` finds a valid token file for the current `client_id`, it loads the tokens into memory.

#### 2.5 Token Refresh

Access tokens are short-lived. The `KickAuthManager` handles refreshing them automatically:

```python
# When the bot needs to make an API call:
try:
    valid_token = await auth_manager.get_valid_token() # This handles refresh internally
except KickAuthManagerError as e:
    print(f"Could not get a valid token: {e}. Manual re-authorization might be needed.")
    # Handle re-authorization prompt for the user
```

The `get_valid_token()` method checks if the current access token is valid (exists and not expired/about to expire). If not:
1.  It attempts to use the `refresh_token` to request a new set of tokens from `https://id.kick.com/oauth2/token` (with `grant_type="refresh_token"`).
2.  If successful, the new tokens are stored in memory and saved to `kickbot_tokens.json`, overwriting the old ones.
3.  **Refresh Failure:** If the refresh attempt fails (e.g., the refresh token has been revoked or is invalid for other reasons), `KickAuthManager` will:
    *   Clear all current token data (in memory and from `kickbot_tokens.json`).
    *   Raise a `KickAuthManagerError` indicating that re-authorization is required.
    *   The bot owner will need to repeat the one-time manual authorization process (Step 2.2) to get new tokens.

This simplified refresh strategy ensures that the bot attempts to self-maintain its authentication but clearly signals when manual intervention is necessary.

#### 2.6 API Requests

Make authenticated requests using the token:

```python
valid_token = await auth_manager.get_valid_token()
headers = {"Authorization": f"Bearer {valid_token}"}
async with aiohttp.ClientSession() as session:
    async with session.get("https://kick.com/api/v2/channels/me", headers=headers) as response:
        data = await response.json()
```

### PKCE Security Details

PKCE (RFC 7636) adds security for public clients:

1. **Code Verifier** - A random string between 43 and 128 characters
2. **Code Challenge** - SHA-256 hash of the code verifier, base64url-encoded
3. **Challenge Method** - Always "S256" in this implementation

This protects against authorization code interception attacks, as the attacker would need the code verifier to exchange the code for tokens.

### Configuration

The OAuth authentication relies on configuration typically set via environment variables (loaded from a `.env` file) or passed directly during `KickAuthManager` initialization:

- `KICK_CLIENT_ID`: **Required.** Your Kick application's client ID.
- `KICK_CLIENT_SECRET`: **Required by Kick, but not directly used in the PKCE token exchange by a public client like this bot.** It's good practice to have it in your `.env` as Kick provides it.
- `KICK_REDIRECT_URI`: **Required.** The redirect URI registered in your Kick App settings and used by the helper script (e.g., `http://localhost:8080/callback`).
- `KICK_SCOPES`: Optional. Space-separated list of requested scopes. Defaults to a set including `events:subscribe` if not provided.

## Complete OAuth Example for Initial Authorization

The project includes `scripts/kick_auth_example.py`, which demonstrates the full one-time authorization flow needed to get the initial `kickbot_tokens.json` file. 

**To perform the initial authorization for Sr_Botoshi:**
1.  Ensure your `.env` file has `KICK_CLIENT_ID`, `KICK_CLIENT_SECRET`, and `KICK_REDIRECT_URI` (e.g., `http://localhost:8080/callback`).
2.  Run the script:
    ```bash
    conda activate kickbot
    export PYTHONPATH=$(pwd):$PYTHONPATH # If not already set by your environment
    python scripts/kick_auth_example.py --authorize
    ```
3.  Follow the prompts: open the URL in your browser, authorize the application.
4.  Once the script confirms success, `kickbot_tokens.json` will be created/updated in your project root.
5.  Sr_Botoshi, when started, will then use this token file.

```python
#!/usr/bin/env python
# (Content of scripts/kick_auth_example.py is largely illustrative here,
# the actual script should be referred to for execution)

# Key parts of kick_auth_example.py for understanding the flow:

# 1. Initialization of KickAuthManager
# auth_manager = KickAuthManager() # Reads from .env by default

# 2. Function to start a local server for the redirect URI
# async def start_callback_server(auth_manager_instance, port, path_segment):
#    app = web.Application()
#    # The path for add_get should match the KICK_REDIRECT_URI's path
#    app.router.add_get(f'/{path_segment}', lambda req: handle_oauth_callback(req, auth_manager_instance))
#    ...

# 3. Handler for the OAuth callback
# async def handle_oauth_callback(request, auth_manager_instance):
#    params = request.rel_url.query
#    if 'code' in params:
#        # Authorization code received
#        auth_code = params['code']
#        # The `auth_manager_instance` would store the code_verifier from when auth_url was generated
#        # await auth_manager_instance.exchange_code_for_tokens(auth_code, stored_code_verifier)
#        return web.Response(text="Authorization successful! ...")
#    ...

# 4. Main part of the --authorize flow
# async def run_authorization_flow(auth_manager):
#    auth_url, code_verifier = auth_manager.get_authorization_url()
#    # Store code_verifier to be used by the callback handler or after callback returns
#    # Start local server
#    # Open browser with auth_url
#    # Wait for callback to set an event or return the code
#    # Exchange code for tokens using the stored code_verifier

# For actual execution and details, please see scripts/kick_auth_example.py.
```

This detailed explanation should guide the bot owner through the one-time setup and clarify how the bot maintains authentication thereafter.

## Error Handling

Both authentication methods include robust error handling:

- **Network errors** - Handled and wrapped in appropriate exceptions
- **API errors** - Status codes and error messages are included in exceptions
- **Token validation** - Tokens are validated before use and refreshed if necessary
- **File errors** - Issues with token storage/loading are logged

## Testing

The OAuth authentication implementation includes comprehensive tests:

- Unit tests for PKCE helper functions
- Tests for token exchange with various response scenarios
- Tests for token storage and loading
- Tests for token refresh functionality
- Tests for token validation and automatic refresh

Run the tests using the provided script:

```bash
./run_tests.sh
```

Or run individual test modules:

```bash
python -m unittest tests.test_kick_auth_simple
python -m unittest tests.test_kick_auth_token_storage
python -m unittest tests.test_kick_auth_manager_fixed
``` 