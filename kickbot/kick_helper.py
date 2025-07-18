import logging
import requests

from .constants import BASE_HEADERS, KickHelperException
from .kick_message import KickMessage

logger = logging.getLogger(__name__)


async def get_streamer_info(bot) -> None:
    """
    Retrieve dictionary containing all info related to the streamer and set bot attributes accordingly.

    :param bot: Main KickBot
    """
    url = f"https://kick.com/api/v2/channels/{bot.streamer_slug}"
    
    if bot.client and hasattr(bot.client, 'scraper'):
        # Use traditional client method
        response = bot.client.scraper.get(url, cookies=bot.client.cookies, headers=BASE_HEADERS)
        status = response.status_code
        match status:
            case 403 | 429:
                raise KickHelperException(f"Error retrieving streamer info. Blocked By cloudflare. ({status})")
            case 404:
                raise KickHelperException(f"Streamer info for '{bot.streamer_name}' not found. (404 error) ")
        try:
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to parse streamer info JSON: {e}")
            raise KickHelperException(f"Failed to parse streamer info JSON: {e}")
    else:
        # Use OAuth/aiohttp method
        async with bot.http_session.get(url, headers=BASE_HEADERS) as response:
            status = response.status
            if status in [403, 429]:
                raise KickHelperException(f"Error retrieving streamer info. Blocked By cloudflare. ({status})")
            elif status == 404:
                raise KickHelperException(f"Streamer info for '{bot.streamer_name}' not found. (404 error) ")
            try:
                data = await response.json()
            except Exception as e:
                logger.error(f"Failed to parse streamer info JSON: {e}")
                raise KickHelperException(f"Failed to parse streamer info JSON: {e}")
    
    bot.streamer_info = data
    bot.chatroom_info = data.get('chatroom')
    bot.chatroom_id = bot.chatroom_info.get('id')


async def get_chatroom_settings(bot) -> None:
    """
    Retrieve chatroom settings for the streamer and set bot.chatroom_settings

    :param bot: Main KickBot
    """
    url = f"https://kick.com/api/internal/v1/channels/{bot.streamer_slug}/chatroom/settings"
    
    if bot.client and hasattr(bot.client, 'scraper'):
        # Use traditional client method
        response = bot.client.scraper.get(url, cookies=bot.client.cookies, headers=BASE_HEADERS)
        if response.status_code != 200:
            raise KickHelperException(f"Error retrieving chatroom settings. Response Status: {response.status_code}")
        try:
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to parse chatroom settings JSON: {e}")
            raise KickHelperException(f"Failed to parse chatroom settings JSON: {e}")
    else:
        # Use OAuth/aiohttp method
        async with bot.http_session.get(url, headers=BASE_HEADERS) as response:
            if response.status != 200:
                raise KickHelperException(f"Error retrieving chatroom settings. Response Status: {response.status}")
            try:
                data = await response.json()
            except Exception as e:
                logger.error(f"Failed to parse chatroom settings JSON: {e}")
                raise KickHelperException(f"Failed to parse chatroom settings JSON: {e}")
    
    bot.chatroom_settings = data.get('data').get('settings')


async def get_bot_settings(bot) -> None:
    """
    Retrieve the bot settings for the stream. Checks if bot has mod / admin status. Sets attributes accordingly.

    :param bot: Main KickBot
    """
    url = f"https://kick.com/api/v2/channels/{bot.streamer_slug}/me"
    
    if bot.client and hasattr(bot.client, 'scraper'):
        # Use traditional client method
        headers = BASE_HEADERS.copy()
        headers['Authorization'] = "Bearer " + bot.client.auth_token
        headers['X-Xsrf-Token'] = bot.client.xsrf
        response = bot.client.scraper.get(url, cookies=bot.client.cookies, headers=headers)
        if response.status_code != 200:
            raise KickHelperException(f"Error retrieving bot settings. Response Status: {response.status_code}")
        data = response.json()
    else:
        # Use OAuth/aiohttp method
        headers = BASE_HEADERS.copy()
        if bot.auth_manager:
            try:
                token = await bot.auth_manager.get_valid_token()
                headers['Authorization'] = f"Bearer {token}"
            except Exception as e:
                logger.warning(f"Could not get OAuth token for bot settings: {e}")
                # Set default values if we can't get bot settings
                bot.bot_settings = {}
                bot.is_mod = False
                bot.is_super_admin = False
                return
        
        async with bot.http_session.get(url, headers=headers) as response:
            if response.status != 200:
                logger.warning(f"Error retrieving bot settings. Response Status: {response.status}")
                # Set default values if we can't get bot settings
                bot.bot_settings = {}
                bot.is_mod = False
                bot.is_super_admin = False
                return
            data = await response.json()
    
    bot.bot_settings = data
    bot.is_mod = data.get('is_moderator')
    bot.is_super_admin = data.get('is_super_admin')


def get_current_viewers(bot) -> int:
    """
    Retrieve current amount of viewers in the stream.

    :param bot: Main KickBot
    :return: Viewer count as an integer
    """
    id = bot.streamer_info.get('id')
    url = f"https://api.kick.com/private/v0/channels/{id}/viewer-count"
    response = bot.client.scraper.get(url, cookies=bot.client.cookies, headers=BASE_HEADERS)
    if response.status_code != 200:
        logger.error(f"Error retrieving current viewer count. Response Status: {response.status_code}")
    data = response.json()
    try:
        return int(data.get('data').get('viewer_count'))
    except ValueError:
        logger.error(f"Error parsing viewer count. Response Status: {response.status_code}")


def message_from_data(message: dict) -> KickMessage:
    """
    Return a KickMessage object from the raw message data, containing message and sender attributes.
    
    This function handles various message structure formats:
    1. WebSocket messages: Have a nested 'data' field that contains the actual message
    2. Webhook messages: Direct message structure without a nested 'data' field
    3. Pydantic model converted messages: May have different field names
    
    :param message: Inbound message from websocket or webhook
    :return: KickMessage object with message and sender attributes
    """
    # Initialize data to the message itself by default
    data = message
    
    # Check if this is a WebSocket message (has 'data' field)
    if 'data' in message:
        data_field = message.get('data')
        # If data is a string (JSON), we need to parse it
        if isinstance(data_field, str):
            try:
                import json
                data = json.loads(data_field)
            except json.JSONDecodeError:
                logger.warning(f"Error parsing JSON data from response {message}")
                # Continue with original message
        elif isinstance(data_field, dict):
            # Use the data field directly
            data = data_field
    
    # Handle edge cases where data might be None
    if data is None:
        logger.error(f"Error parsing message data from response {message}")
        # Fallback to using the original message to avoid complete failure
        data = message
    
    # Normalize field names for webhook format
    # Some webhooks use message_id instead of id
    if 'message_id' in data and 'id' not in data:
        data['id'] = data['message_id']
    
    # Handle sender variations
    if 'sender' in data and isinstance(data['sender'], dict):
        sender = data['sender']
        # Some webhooks use user_id instead of id for the sender
        if 'user_id' in sender and 'id' not in sender:
            sender['id'] = sender['user_id']
        # Some webhooks use channel_slug instead of slug
        if 'channel_slug' in sender and 'slug' not in sender:
            sender['slug'] = sender['channel_slug']
    
    try:
        return KickMessage(data)
    except Exception as e:
        logger.error(f"Failed to create KickMessage: {e} | Raw data: {data}")
        raise KickHelperException(f"Failed to create KickMessage: {e}")


def send_message_in_chat(bot, message: str) -> requests.Response:
    """
    Send a message in a chatroom. Uses v1 API, was having csrf issues using v2 API (code 419).
    DEPRECATED: Use send_message_in_chat_async for OAuth-based webhook bots.

    :param bot: Main KickBot
    :param message: Message to send in the chatroom
    :return: Response from sending the message post request
    """
    url = "https://kick.com/api/v1/chat-messages"
    headers = BASE_HEADERS.copy()
    headers['X-Xsrf-Token'] = bot.client.xsrf
    headers['Authorization'] = "Bearer " + bot.client.auth_token
    payload = {"message": message,
               "chatroom_id": bot.chatroom_id}
    return bot.client.scraper.post(url, json=payload, cookies=bot.client.cookies, headers=headers)


async def send_message_in_chat_async(bot, message: str) -> dict:
    """
    Send a message in a chatroom using OAuth authentication and new Chat API.
    
    :param bot: Main KickBot with OAuth authentication
    :param message: Message to send in the chatroom
    :return: Response JSON from the Chat API
    :raises: KickHelperException if sending fails
    """
    try:
        # Get OAuth token
        if bot.auth_manager:
            token = await bot.auth_manager.get_valid_token()
        elif hasattr(bot.client, 'auth_token') and bot.client.auth_token:
            token = bot.client.auth_token
        else:
            raise KickHelperException("No valid authentication token available")
        
        # New Chat API endpoint
        url = "https://api.kick.com/public/v1/chat"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "content": message,
            "type": "bot"  # Send as bot type since we're using OAuth
        }
        
        # Use aiohttp session for async request
        async with bot.http_session.post(url, json=payload, headers=headers) as response:
            response_data = await response.json()
            
            if response.status == 200:
                logger.info(f"✅ Message sent successfully: {message[:50]}...")
                return response_data
            else:
                error_msg = f"Failed to send message. Status: {response.status}, Response: {response_data}"
                logger.error(error_msg)
                raise KickHelperException(error_msg)
                
    except Exception as e:
        logger.error(f"Error sending message '{message}': {e}")
        raise KickHelperException(f"Failed to send message: {e}")


def send_reply_in_chat(bot, message: KickMessage, reply_message: str) -> requests.Response:
    """
    Reply to a users message.
    DEPRECATED: Use send_reply_in_chat_async for OAuth-based webhook bots.

    :param bot: KickBot object containing streamer, and bot info
    :param message: Original message to reply
    :param reply_message:  Reply message to be sent to the original message
    :return: Response from sending the message post request
    """
    url = f"https://kick.com/api/v2/messages/send/{bot.chatroom_id}"
    headers = BASE_HEADERS.copy()
    headers['X-Xsrf-Token'] = bot.client.xsrf
    headers['Authorization'] = "Bearer " + bot.client.auth_token
    payload = {
        "content": reply_message,
        "type": "reply",
        "metadata": {
            "original_message": {
                "id": message.id,
                "content": message.content
            },
            "original_sender": {
                "id": message.sender.user_id,
                "username": message.sender.username
            }
        }
    }
    return bot.client.scraper.post(url, json=payload, cookies=bot.client.cookies, headers=headers)


async def send_reply_in_chat_async(bot, message: KickMessage, reply_message: str) -> dict:
    """
    Reply to a user's message using OAuth authentication and new Chat API.
    
    :param bot: Main KickBot with OAuth authentication
    :param message: Original message to reply to
    :param reply_message: Reply message content
    :return: Response JSON from the Chat API
    :raises: KickHelperException if sending fails
    """
    try:
        # Get OAuth token
        if bot.auth_manager:
            token = await bot.auth_manager.get_valid_token()
        elif hasattr(bot.client, 'auth_token') and bot.client.auth_token:
            token = bot.client.auth_token
        else:
            raise KickHelperException("No valid authentication token available")
        
        # New Chat API endpoint
        url = "https://api.kick.com/public/v1/chat"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "content": reply_message,
            "type": "bot",  # Send as bot type since we're using OAuth
            "reply_to_message_id": message.id  # Reply to the original message
        }
        
        # Use aiohttp session for async request
        async with bot.http_session.post(url, json=payload, headers=headers) as response:
            response_data = await response.json()
            
            if response.status == 200:
                logger.info(f"✅ Reply sent successfully to {message.sender.username}: {reply_message[:50]}...")
                return response_data
            else:
                error_msg = f"Failed to send reply. Status: {response.status}, Response: {response_data}"
                logger.error(error_msg)
                raise KickHelperException(error_msg)
                
    except Exception as e:
        logger.error(f"Error sending reply '{reply_message}' to {message.sender.username}: {e}")
        raise KickHelperException(f"Failed to send reply: {e}")


def get_ws_uri() -> str:
    """
    This could probably be a constant somewhere else, but this makes it easy to get and easy to change.
    Also, they seem to always use the same ws, but in the case it needs to be dynamically found,
    having this function will make it easier.

    :return: kicks websocket url
    """
    # return 'wss://ws-us2.pusher.com/app/eb1d5f283081a78b932c?protocol=7&client=js&version=7.6.0&flash=false'
    return 'wss://ws-us2.pusher.com/app/32cbd69e4b950bf97679?protocol=7&client=js&version=7.6.0&flash=false'


#################################################################################################
#
#                          Helpers used by Moderator class (kick_moderator.py)
#
#################################################################################################


def ban_user(bot, username: str, minutes: int = 0, is_permanent: bool = False) -> bool:
    """
    Bans a user from chat. User by Moderator.timeout_user, and Moderator.permaban

    :param bot: Main KickBot
    :param username: Username to ban
    :param minutes: Minutes to ban user for
    :param is_permanent: Is a permanent ban. Defaults to False.
    """
    url = f"https://kick.com/api/v2/channels/{bot.streamer_slug}/bans"
    headers = BASE_HEADERS.copy()
    headers['path'] = f"/api/v2/channels/{bot.streamer_slug}/bans"
    headers['Authorization'] = "Bearer " + bot.client.auth_token
    headers['X-Xsrf-Token'] = bot.client.xsrf
    if is_permanent:
        payload = {
            "banned_username": username,
            "permanent": is_permanent
        }
    else:
        payload = {
            "banned_username": username,
            "duration": minutes,
            "permanent": is_permanent
        }
    response = bot.client.scraper.post(url, json=payload, cookies=bot.client.cookies, headers=headers)
    if response.status_code != 200:
        logger.error(f"An error occurred when setting timeout for {username} | "
                     f"Status Code: {response.status_code}")
        return False
    return True


def get_viewer_info(bot, username: str) -> dict | None:
    """
    For the Moderator to retrieve info on a user

    :param bot: Main KickBot
    :param username: Username to retrieve user info for

    :return: Dictionary containing viewer info, or None, indicating failure
    """
    slug = username.replace('_', '-')
    url = f"https://kick.com/api/v2/channels/{bot.streamer_slug}/users/{slug}"
    headers = BASE_HEADERS.copy()
    headers['Authorization'] = bot.client.auth_token
    headers['X-Xsrf-Token'] = bot.client.xsrf
    response = bot.client.scraper.get(url, cookies=bot.client.cookies, headers=headers)
    if response.status_code != 200:
        logger.error(f"Error retrieving viewer info for {username} | Status code: {response.status_code}")
        return None
    return response.json()


def get_streamer_leaderboard(bot) -> dict | None:
    """
    Retrieve the chat leaderboard

    :param bot: main KickBot
    :return: Dictionary containing leaderboard. Will return None and log error if it fails.
    """
    url = f"https://kick.com/api/v2/channels/{bot.streamer_slug}/leaderboards"
    response = bot.client.scraper.get(url, cookies=bot.client.cookies, headers=BASE_HEADERS)
    if response.status_code != 200:
        logger.warning(f"An error occurred while retrieving leaderboard. Status Code: {response.status_code}")
        return None
    try:
        return response.json()
    except Exception as e:
        logger.error(f"Failed to parse leaderboard JSON: {e}")
        return None
