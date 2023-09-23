import requests
import logging
import tls_client

from typing import Optional
from requests.cookies import RequestsCookieJar

from .constants import BASE_HEADERS, KickAuthException

logger = logging.getLogger(__name__)


class KickClient:
    """
    Class mainly for authenticating user, and handling http requests using tls_client to bypass cloudflare
    """
    def __init__(self, username: str, password: str) -> None:
        self.username: str = username
        self.password: str = password
        self.scraper = tls_client.Session(
            client_identifier="chrome_116",
            random_tls_extension_order=True
        )
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
        login_response = self._send_login_request(login_payload)
        login_data = login_response.json()
        login_status = login_response.status_code
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
                raise KickAuthException("Cloudflare blocked (gay). Might need to set a proxy. Response:", login_data)
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
        data = user_info_response.json()
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
        return self.scraper.post(url, json=payload, cookies=self.cookies, headers=headers)

    @staticmethod
    def _get_2fa_code() -> str:
        input_attempts = 0
        while input_attempts < 3:
            input_code = input("Enter the 2fa code you received from kick: ")
            try:
                code = int(input_code)
                if len(str(code)) != 6:
                    print("    Invalid input code format.")
                    input_attempts += 1
                else:
                    return str(code)
            except ValueError:
                print("    Invalid code input. must consist of numbers only.")
                input_attempts += 1
        raise KickAuthException("Max 2fa code input attempts reached.")

    def _send_login_2fa_code(self, payload: dict) -> bool:
        url = 'https://kick.com/mobile/login'
        headers = BASE_HEADERS.copy()
        headers['X-Xsrf-Token'] = self.xsrf
        response = self.scraper.post(url, json=payload, cookies=self.cookies, headers=headers)
        self.auth_token = response.json().get('token')
        return response.status_code == 200
