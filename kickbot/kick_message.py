import json
import logging
from typing import List, Optional, Union, Dict, Any

logger = logging.getLogger(__name__)

class KickMessage:
    def __init__(self, raw_data: Union[str, Dict[str, Any]]) -> None:
        self.raw = raw_data
        data_dict: Dict[str, Any]
        try:
            if isinstance(raw_data, str):
                data_dict = json.loads(raw_data)
            elif isinstance(raw_data, dict):
                data_dict = raw_data
            else:
                raise TypeError("raw_data must be a JSON string or a dictionary.")
                
        except (json.JSONDecodeError, TypeError) as e:
            error_msg = f"Error decoding KickMessage: {e}, Raw Data: {raw_data}"
            logger.error(error_msg)
            print(error_msg)
            raise ValueError(f"Failed to parse KickMessage JSON: {e} | Raw: {raw_data}")

        # Handle both WebSocket format and webhook format
        # In webhook format, message_id is used instead of id
        self.id: str | None = data_dict.get('id') or data_dict.get('message_id')
        
        # chatroom_id might be a string or an int
        chatroom_id = data_dict.get('chatroom_id')
        if chatroom_id is not None:
            try:
                self.chatroom_id = int(chatroom_id) if isinstance(chatroom_id, (str, int)) else None
            except (ValueError, TypeError):
                logger.warning(f"Invalid chatroom_id format: {chatroom_id}")
                self.chatroom_id = None
        else:
            self.chatroom_id = None
            
        self.content: str | None = data_dict.get('content')
        self.args: list[str] | None = self.content.split() if self.content else []
        self.type: str | None = data_dict.get('type')
        self.created_at: str | None = data_dict.get('created_at')
        
        # For debugging
        if self.id is None:
            logger.debug(f"Message has no id or message_id: {data_dict}")
        
        # Add the raw data as data property for reference
        self.data = data_dict
        
        # Handle missing or invalid sender data
        sender_data = data_dict.get('sender')
        if sender_data is None:
            logger.warning(f"Message has no sender data: {data_dict}")
            self.sender = None
        elif not isinstance(sender_data, dict):
            logger.warning(f"Invalid sender data type, expected dict but got {type(sender_data)}: {sender_data}")
            self.sender = None
        else:
            try:
                self.sender = _Sender(sender_data)
            except Exception as e:
                logger.error(f"Error creating _Sender object: {e}. Raw sender data: {sender_data}")
                self.sender = None

    def __repr__(self) -> str:
        return f"KickMessage({self.raw})"


class _Sender:
    def __init__(self, raw_sender: dict) -> None:
        if not isinstance(raw_sender, dict):
            raise ValueError(f"Invalid sender data: {raw_sender}")
        
        self.raw_sender = raw_sender
        
        # Extract user_id with validation and type conversion
        user_id = raw_sender.get('id') or raw_sender.get('user_id')
        if user_id is None:
            logger.warning(f"Sender missing 'id' and 'user_id' fields: {raw_sender}")
            self.user_id = None
        else:
            # Convert to string as our code expects user_id as a string
            self.user_id = str(user_id)
        
        # Extract username with validation
        username = raw_sender.get('username')
        if username is None:
            logger.warning(f"Sender missing 'username' field: {raw_sender}")
        self.username = username
        
        # Extract slug with validation - in webhook it could be channel_slug
        self.slug = raw_sender.get('slug') or raw_sender.get('channel_slug')
        
        # Get identity with proper fallback
        identity = raw_sender.get('identity')
        
        # Ensure identity is a dict, even if it's None in the raw data
        if identity is None:
            self.identity = {}
        else:
            self.identity = identity
            
        # Extract badges or empty list
        self.badges = self.identity.get('badges', [])
        
        # Ensure badges is a list, even if it's None in the identity
        if self.badges is None:
            self.badges = []

    def __repr__(self) -> str:
        return f"KickMessage.sender({self.raw_sender})"
