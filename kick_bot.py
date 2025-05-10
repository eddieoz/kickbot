import logging
import asyncio
import websockets
import aiohttp
import json
from kickbot.constants import KickBotException

class KickBot:
    """
    Main class for interacting with the Bot API.
    """
    def __init__(self, username: str, password: str) -> None:
        self.logger = logging.getLogger(__name__) # This is 'kickbot.kick_bot'
        self.logger.setLevel(logging.DEBUG)  # FORCE DEBUG LEVEL FOR THIS LOGGER INSTANCE
        
        # Ensure there's a handler that can output DEBUG messages
        # This might add a duplicate handler if basicConfig is also working, 
        # but for diagnostics, seeing the message is key.
        if not self.logger.handlers or not any(h.level <= logging.DEBUG for h in self.logger.handlers):
            # Remove existing handlers if they might be filtering out DEBUG
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
            
            stream_handler = logging.StreamHandler() # Outputs to stderr by default
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)-8s - %(message)s', datefmt='%Y-%m-%d %I:%M.%S %p')
            stream_handler.setFormatter(formatter)
            stream_handler.setLevel(logging.DEBUG) # Ensure handler processes DEBUG
            self.logger.addHandler(stream_handler)
            self.logger.propagate = False # Prevent duplication if root logger also has a handler

        self.username = username
        self.http_session = aiohttp.ClientSession()
        self.auth_token = "YOUR_KICK_OAUTH_TOKEN_WITH_CHAT_WRITE_SCOPE"
        self.target_channel_slug = "your_streamer_channel_slug" # e.g., "eddieoz"
        self.kick_api_base_url = "https://kick.com/api/v2" # Or other version

    async def _handle_chat_message_logic(self, km: KickMessage):
        """Shared logic to handle a KickMessage object (placeholder)."""
        self.logger.debug(f"_handle_chat_message_logic received KickMessage from user: {km.sender.username if km.sender else 'UnknownSender'} content: '{km.content}'")
        # Actual handler logic will be re-inserted here later
        pass

    async def _handle_chat_message(self, message_data: dict):
        """Handles an incoming chat message from WebSocket data."""
        try:
            km = KickMessage(message_data)
            self.logger.debug(f"WS Message object: User {km.sender.username if km.sender else 'UnknownSender'} said '{km.content}'")
            await self._handle_chat_message_logic(km)
        except Exception as e:
            self.logger.error(f"Error creating/handling KickMessage from WebSocket: {e} | Data: {message_data}", exc_info=True)

    async def process_webhook_chat_message(self, message_data_dict: dict):
        """Processes a chat message dictionary received from a webhook.
           Creates a KickMessage and passes it to the shared handling logic.
        """
        self.logger.debug(f"Processing webhook chat message data dict: {message_data_dict}")
        try:
            km = KickMessage(message_data_dict)
            self.logger.info(f"Webhook KickMessage: User {km.sender.username if km.sender else 'UnknownSender'} said '{km.content}'")
            await self._handle_chat_message_logic(km)
        except Exception as e:
            self.logger.error(f"Error creating/handling KickMessage from Webhook: {e} | Data: {message_data_dict}", exc_info=True)

    async def _join_chatroom(self, chatroom_id):
        # ... existing code ...
        self.logger.info("Timed event tasks cancelled.")

    async def _handle_first_connect(self, message):
        """
        Handle the 'pusher:connection_established' event from the websocket.
        Currently a no-op.
        """
        # self.logger.info("WebSocket connection established (pusher:connection_established event).") # Redundant with a DEBUG log now
        self.logger.debug(f"Handling 'pusher:connection_established': {message}")
        # Optionally, parse the message or update state if needed.
        pass

    async def _send_message_via_api(self, channel_slug: str, message_content: str):
        """
        Sends a message to a specified channel slug using Kick's HTTP API.
        Ensure http_session, auth_token, and kick_api_base_url are set on self.
        """
        if not hasattr(self, 'http_session') or not self.http_session or self.http_session.closed:
            self.logger.error("HTTP session not initialized or closed. Cannot send API message.")
            # You might want to re-initialize the session here if appropriate, or ensure it's always up.
            raise KickBotException("HTTP session not available for API calls.")

        if not hasattr(self, 'auth_token') or not self.auth_token:
            self.logger.error("Auth token not configured. Cannot send API message.")
            raise KickBotException("Auth token not configured for API calls.")
        
        if not hasattr(self, 'kick_api_base_url') or not self.kick_api_base_url:
            self.logger.error("Kick API base URL not configured.")
            raise KickBotException("Kick API base URL not configured.")

        api_url = f"{self.kick_api_base_url}/channels/{channel_slug}/messages"
        payload = {"content": message_content, "type": "message"}
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        self.logger.debug(f"Attempting to send API message to channel '{channel_slug}': {message_content!r}")
        try:
            async with self.http_session.post(api_url, json=payload, headers=headers) as response:
                response_text = await response.text()
                if 200 <= response.status < 300:
                    self.logger.info(f"API Message sent successfully to channel '{channel_slug}'. Status: {response.status}")
                else:
                    self.logger.error(f"Failed to send API message to channel '{channel_slug}'. Status: {response.status}, Response: {response_text}")
                    raise KickBotException(f"API error sending message to {channel_slug}: {response.status} - {response_text}")
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP ClientError sending API message to '{channel_slug}': {e}", exc_info=True)
            raise KickBotException(f"HTTP ClientError sending API message to {channel_slug}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected exception sending API message to '{channel_slug}': {e}", exc_info=True)
            raise KickBotException(f"Unexpected exception sending API message to {channel_slug}: {e}")

    async def send_text(self, message: str) -> None:
        """
        Used to send text in the chat using the HTTP API.
        reply_text below is used to reply to a specific users message.

        :param message: Message to be sent in the chat
        """
        if not isinstance(message, str) or message.strip() == "":
            raise KickBotException("Invalid message. Must be a non empty string.")
        
        if not hasattr(self, 'target_channel_slug') or not self.target_channel_slug:
            self.logger.error("target_channel_slug is not configured in KickBot. Cannot send message.")
            raise KickBotException("target_channel_slug not configured.")

        self.logger.debug(f"Queueing send_text (API): {message!r} to channel {self.target_channel_slug}")
        try:
            await self._send_message_via_api(self.target_channel_slug, message)
        except KickBotException as e:
            # Log the error. The original method raised a generic error.
            # Re-raising to signal failure.
            self.logger.error(f"An error occurred while sending message {message!r} via API: {e}")
            raise KickBotException(f"An error occurred while sending message {message!r} via API.")


    async def reply_text(self, original_message: KickMessage, reply_message: str) -> None:
        """
        Used inside a command/message handler function to reply to the original message / command using the HTTP API.

        :param original_message: The original KickMessage argument in the handler function
        :param reply_message: string to reply to the original message
        """
        if not isinstance(reply_message, str) or reply_message.strip() == "":
            raise KickBotException("Invalid reply message. Must be a non empty string.")
        
        if '@@Restream' in reply_message:
            self.logger.warning(f"Skipping reply to avoid breaking: {reply_message!r}")
            return

        # Check if sender exists and has a username, to avoid AttributeError
        if not hasattr(original_message, 'sender') or original_message.sender is None:
            self.logger.error(f"Cannot reply: Original message has no sender. Message: {original_message}")
            raise KickBotException(f"Cannot reply: Original message has no sender")
            
        if not hasattr(original_message.sender, 'username') or original_message.sender.username is None:
            self.logger.error(f"Cannot reply: Sender has no username. Sender: {original_message.sender}")
            raise KickBotException(f"Cannot reply: Sender has no username")

        if not hasattr(self, 'target_channel_slug') or not self.target_channel_slug:
            self.logger.error("target_channel_slug is not configured in KickBot. Cannot send reply.")
            raise KickBotException("target_channel_slug not configured for replies.")
        
        target_slug_for_reply = self.target_channel_slug 
        
        # You might want more sophisticated logic here if your bot operates in multiple channels
        # or if original_message contains a reliable source channel slug/ID.
        # For example, if original_message has a broadcaster_slug attribute:
        # if hasattr(original_message, 'broadcaster_slug') and original_message.broadcaster_slug:
        #    target_slug_for_reply = original_message.broadcaster_slug

        mention_prefix = f"@{original_message.sender.username} "
        full_reply_content = f"{mention_prefix}{reply_message}"

        self.logger.debug(f"Queueing reply_text (API): {full_reply_content!r} to channel {target_slug_for_reply}")
        try:
            await self._send_message_via_api(target_slug_for_reply, full_reply_content)
        except KickBotException as e:
            self.logger.error(f"An error occurred while sending reply {reply_message!r} via API: {e}")
            # Re-raise to signal failure, consistent with original method's behavior.
            raise KickBotException(f"An error occurred while sending reply {reply_message!r} via API.")

    # It's good practice to also revert the __init__ logging change if we are done with it.
    # However, let's keep it for one more round to ensure we see webhook logs if they start appearing.
    # Reminder to clean up KickBot.__init__ logging after confirming webhook path or deciding against it.

    # ... rest of the existing methods ... 