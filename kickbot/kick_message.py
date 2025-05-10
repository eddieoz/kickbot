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

        self.id: str | None = data_dict.get('id')
        self.chatroom_id: int | None = data_dict.get('chatroom_id')
        self.content: str | None = data_dict.get('content')
        self.args: list[str] | None = self.content.split() if self.content else []
        self.type: str | None = data_dict.get('type')
        self.created_at: str | None = data_dict.get('created_at')
        
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
        
        # Extract user_id with validation
        user_id = raw_sender.get('id')
        if user_id is None:
            logger.warning(f"Sender missing 'id' field: {raw_sender}")
        self.user_id = user_id
        
        # Extract username with validation
        username = raw_sender.get('username')
        if username is None:
            logger.warning(f"Sender missing 'username' field: {raw_sender}")
        self.username = username
        
        # Extract other fields
        self.slug = raw_sender.get('slug')
        self.identity = raw_sender.get('identity', {})
        
        # Ensure identity is a dict, even if it's None in the raw data
        if self.identity is None:
            self.identity = {}
            
        self.badges = self.identity.get('badges', [])
        
        # Ensure badges is a list, even if it's None in the identity
        if self.badges is None:
            self.badges = []

    def __repr__(self) -> str:
        return f"KickMessage.sender({self.raw_sender})"
