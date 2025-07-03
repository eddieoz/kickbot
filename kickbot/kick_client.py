import requests
import logging
import tls_client
import aiohttp
import time
import random

from typing import Optional
from requests.cookies import RequestsCookieJar

from .constants import BASE_HEADERS, KickAuthException

logger = logging.getLogger(__name__)


class KickClient:
    """
    Class mainly for authenticating user, and handling http requests using tls_client to bypass cloudflare
    """
    def __init__(self, username: str, password: str, aiohttp_session: Optional[aiohttp.ClientSession] = None) -> None:
        self.username: str = username
        self.password: str = password
        self.scraper = tls_client.Session(
            client_identifier="chrome_116",
            random_tls_extension_order=True
        )
        self.session = aiohttp_session
        self.xsrf: Optional[str] = None
        self.cookies: Optional[RequestsCookieJar] = None
        self.auth_token: Optional[str] = None
        self.user_data: Optional[dict] = None
        self.user_id: Optional[int] = None
        self._login()

    def _login(self) -> None:
        """
        Main function to authenticate the user bot.

        Retrieves tokens and cookies from /kick-token-provider with self.scraper (tls-client),
        """
        logger.info("Logging user-bot in...")
        try:
            initial_token_response = self._request_token_provider()
            token_data = initial_token_response.json()
            self.cookies = initial_token_response.cookies
            self.xsrf = initial_token_response.cookies['XSRF-TOKEN']

        except (requests.exceptions.HTTPError, requests.exceptions.JSONDecodeError) as e:
            logger.error(f"An error occurred while attempting login. {str(e)}")
            exit(1)

        name_field_name = token_data.get('nameFieldName')
        token_field = token_data.get('validFromFieldName')
        login_token = token_data.get('encryptedValidFrom')
        if any(value is None for value in [name_field_name, token_field, login_token]):
            raise KickAuthException("Error when parsing token fields while attempting login.")

        login_payload = self._base_login_payload(name_field_name, token_field, login_token)
        login_response = self._send_login_request_with_retry(login_payload)
        login_status = login_response.status_code
        
        # Debug response before parsing JSON
        logger.debug(f"Login response status: {login_status}")
        logger.debug(f"Login response headers: {login_response.headers}")
        logger.debug(f"Login response text: {login_response.text}")
        
        # Handle empty or non-JSON responses
        if not login_response.text.strip():
            raise KickAuthException(f"Empty response from login endpoint. Status: {login_status}")
        
        try:
            login_data = login_response.json()
        except Exception as e:
            raise KickAuthException(f"Failed to parse login response as JSON. Status: {login_status}, Response: {login_response.text[:500]}, Error: {e}")
        match login_status:
            case 200:
                self.auth_token = login_data.get('token')
                twofactor = login_data.get('2fa_required')
                if twofactor:
                    logger.info("2FA REQUIRED")
                    twofactor_code = self._get_2fa_code()
                    login_payload['one_time_password'] = twofactor_code
                    twofactor_result = self._send_login_2fa_code(login_payload)
                    if not twofactor_result:
                        raise KickAuthException("Error occurred while sending 2fa login code.")
            case 422:
                raise KickAuthException("Login Failed:", login_data)
            case 419:
                raise KickAuthException("Csrf Error:", login_data)
            case 403:
                raise KickAuthException("Cloudflare blocked. Might need to set a proxy. Response:", login_data)
            case _:
                raise KickAuthException(f"Unexpected Response. Status Code: {login_status} | Response: {login_data}")
        logger.info("Login Successful...")
        self._get_user_info()

    def _get_user_info(self) -> None:
        """
        Retrieve user info after authenticating.
        Sets self.user_data and self.user_id (data of the user bot)
        """
        url = 'https://kick.com/api/v1/user'
        headers = BASE_HEADERS.copy()
        headers['Authorization'] = "Bearer " + self.auth_token
        headers['X-Xsrf-Token'] = self.xsrf
        user_info_response = self.scraper.get(url, cookies=self.cookies, headers=headers)
        if user_info_response.status_code != 200:
            raise KickAuthException(f"Error fetching user info from {url}")
        try:
            data = user_info_response.json()
        except Exception as e:
            logger.error(f"Failed to parse user info JSON: {e}")
            raise KickAuthException(f"Failed to parse user info JSON: {e}")
        self.user_data = data
        self.bot_name = data.get('username')
        self.user_id = data.get('id')

    def _request_token_provider(self) -> requests.Response:
        """
         Request the token provider to retrieve some useful tokens, and cookies

         :return: Response from the token provider request using the scraper (tls-client)
         """
        url = "https://kick.com/kick-token-provider"
        headers = BASE_HEADERS.copy()
        headers['Referer'] = "https://kick.com"
        headers['path'] = "/kick-token-provider"
        return self.scraper.get(url, cookies=self.cookies, headers=headers)

    def _base_login_payload(self, name_field_name: str, token_field: str, login_token: str) -> dict:
        payload = {
            name_field_name: '',
            token_field: login_token,
            "email": self.username,
            "isMobileRequest": True,
            "password": self.password,
        }
        return payload

    def _send_login_request(self, payload: dict) -> requests.Response:
        """
        Perform the login post request to the mobile login endpoint. On desktop, I get 2fa more, and a csrf error (419).

        :param payload: Login payload containing user info and tokens.
        :return: Login post request response
        """
        url = 'https://kick.com/mobile/login'
        headers = BASE_HEADERS.copy()
        headers['X-Xsrf-Token'] = self.xsrf
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        return self.scraper.post(url, data=payload, cookies=self.cookies, headers=headers)

    def _send_login_request_with_retry(self, payload: dict, max_retries: int = 3) -> requests.Response:
        """
        Perform the login post request with retry logic for rate limiting.
        
        :param payload: Login payload containing user info and tokens.
        :param max_retries: Maximum number of retry attempts
        :return: Login post request response
        """
        for attempt in range(max_retries + 1):
            try:
                response = self._send_login_request(payload)
                
                # If we get 429 (rate limited), wait and retry
                if response.status_code == 429 and attempt < max_retries:
                    # Extract retry-after header if present
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        # Exponential backoff with jitter
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                    
                    logger.warning(f"Rate limited (429), waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                
                return response
                
            except Exception as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Login request failed: {e}, retrying in {wait_time} seconds")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        
        # If we get here, all retries failed
        raise KickAuthException(f"Login failed after {max_retries} retries")

    @staticmethod
    def _get_2fa_code() -> str:
        input_attempts = 0
        while input_attempts < 3:
            input_code = input("Enter the 2fa code you received from kick: ")
            if len(input_code) == 6 and input_code.isdigit():
                return input_code
            else:
                print("    Invalid input code format. Must be exactly 6 digits.")
                input_attempts += 1
        raise KickAuthException("Max 2fa code input attempts reached.")

    def _send_login_2fa_code(self, payload: dict) -> bool:
        url = 'https://kick.com/mobile/login'
        headers = BASE_HEADERS.copy()
        headers['X-Xsrf-Token'] = self.xsrf
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        response = self.scraper.post(url, data=payload, cookies=self.cookies, headers=headers)
        
        if response.status_code == 200:
            try:
                login_data = response.json()
                self.auth_token = login_data.get('token')
                if self.auth_token:
                    return True
                else:
                    logger.error("2FA login successful (200 OK) but no token found in response.")
                    # Potentially raise an error here or return False to be caught by the caller
                    # For now, let it fall through to return False as per original logic's effect
                    return False # Or raise specific error
            except requests.exceptions.JSONDecodeError as e:
                logger.error(f"2FA login successful (200 OK) but failed to parse JSON response: {e}. Response text: {response.text}")
                return False # Or raise specific error
        else:
            error_text = response.text
            logger.error(f"2FA login request failed. Status: {response.status_code}, Response: {error_text}")
            # The caller will raise based on the boolean, but we've logged the details.
            # To make the exception more direct, we could raise here:
            # raise KickAuthException(f"2FA login failed. Status: {response.status_code}, Response: {error_text}")
            return False
