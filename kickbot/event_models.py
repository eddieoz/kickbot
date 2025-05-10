from typing import Optional, List, Literal, Union, Any
from pydantic import BaseModel, Field, HttpUrl, RootModel, ValidationError, field_validator, validator
# import logging # Re-comment import
from datetime import datetime # THIS IS THE PRIMARY DATETIME IMPORT

class UserInfo(BaseModel):
    """Represents basic user information commonly found in events."""
    id: str # Assuming user IDs are strings, adjust if they are integers
    username: str
    # profile_picture: Optional[HttpUrl] = None # Not consistently in all uses, make optional or specific per event data
    # channel_slug: Optional[str] = None

class FollowerInfo(UserInfo):
    """Specific information for a follower."""
    pass

class SubscriberInfo(UserInfo):
    """Specific information for a subscriber."""
    pass

class GifterInfo(UserInfo):
    """Specific information for a gifter."""
    id: Optional[str] = None
    username: Optional[str] = None
    # profile_picture: Optional[HttpUrl] = None
    # channel_slug: Optional[str] = None

class RecipientInfo(UserInfo):
    """Specific information for a gift recipient."""
    pass

class BaseEventData(BaseModel):
    """Base class for the 'data' field in events, can be empty or have common fields if any."""
    pass

class FollowEventData(BaseModel):
    """Data specific to a 'channel.followed' event."""
    follower: FollowerInfo
    followed_at: datetime

class SubscriptionEventData(BaseModel):
    """Data specific to a 'channel.subscription.new' event."""
    subscriber: SubscriberInfo
    subscription_tier: Optional[str] = Field(None, alias="tier") # Tier is not in basic .new payload, make optional
    months_subscribed: int = Field(..., alias="duration") # Map from 'duration' in payload
    created_at: datetime # Renamed from subscribed_at for consistency, maps to payload's created_at
    expires_at: Optional[datetime] = None # From payload

    @field_validator('months_subscribed', mode='before')
    @classmethod
    def convert_duration_to_months(cls, v):
        # Assuming 'duration' from payload is the number of months
        if isinstance(v, int):
            return v
        # Add any other conversion logic if necessary
        raise ValueError("Invalid value for duration/months_subscribed")

class SubscriptionEvent(BaseModel):
    """Data specific to a 'channel.subscription.new' event."""
    id: str
    event: Literal["channel.subscription.new"]
    channel_id: str
    created_at: datetime # Top-level created_at for the event wrapper itself
    data: SubscriptionEventData

    @property
    def is_gift(self) -> bool:
        return False # By definition for channel.subscription.new

class GiftedSubscriptionEventData(BaseModel):
    """Data specific to a 'channel.subscription.gifts' event."""
    gifter: Optional[GifterInfo] = None # Gifter can be anonymous, so GifterInfo itself is optional or its fields are
    giftees: List[RecipientInfo] = Field(..., alias="recipients") # Map from our old 'recipients' or expect 'giftees' from payload
    subscription_tier: Optional[str] = Field(None, alias="tier") # Not in basic .gifts payload, make optional
    created_at: datetime # Field name from Kick docs for gift event is 'created_at'
    expires_at: Optional[datetime] = None # From payload

class SubscriptionRenewalEventData(BaseModel):
    """Data specific to a 'channel.subscription.renewal' event."""
    subscriber: SubscriberInfo
    subscription_tier: Optional[str] = Field(None, alias="tier") 
    months_subscribed: int = Field(..., alias="duration") # Cumulative months
    created_at: datetime # Start of current period
    expires_at: Optional[datetime] = None # End of current period

    @field_validator('months_subscribed', mode='before')
    @classmethod
    def convert_duration_to_months(cls, v):
        if isinstance(v, int):
            return v
        raise ValueError("Invalid value for duration/months_subscribed")

class GiftedSubscriptionEvent(BaseModel):
    """Data specific to a 'channel.subscription.gifts' event."""
    id: str
    event: Literal["channel.subscription.gifts"]
    channel_id: str
    created_at: datetime # Top-level created_at for the event wrapper itself
    data: GiftedSubscriptionEventData

class SubscriptionRenewalEvent(BaseModel):
    event: Literal["channel.subscription.renewal"]
    data: SubscriptionRenewalEventData

# Common structure for the entire webhook payload from Kick
# Assuming Kick's payload has 'event' for type, 'data' for specifics,
# and other metadata like 'id', 'channel_id', 'created_at' at the top level.
class KickEventBase(BaseModel):
    id: str # Assuming this is the event's unique ID from Kick
    event: str # The event type string, e.g., "channel.followed"
    channel_id: str # ID or slug of the channel
    created_at: datetime # Timestamp from Kick
    data: BaseModel # Generic data, will be parsed into specific model

class FollowEvent(KickEventBase):
    event: Literal["channel.followed"]
    data: FollowEventData

class SubscriptionEventKick(KickEventBase): # Renamed to avoid conflict with the Pydantic model SubscriptionEvent above.
    event: Literal["channel.subscription.new"]
    data: SubscriptionEventData
    
    @property
    def is_gift(self) -> bool: # Added is_gift property here as well for consistency if this model is used.
        return False

class GiftedSubscriptionEvent(KickEventBase):
    event: Literal["channel.subscription.gifts"]
    data: GiftedSubscriptionEventData

class SubscriptionRenewalEvent(KickEventBase):
    event: Literal["channel.subscription.renewal"]
    data: SubscriptionRenewalEventData

# New Models for ChatMessageSentEvent based on Kick Documentation
# https://docs.kick.com/events/event-types (Chat Message section)

class ChatMessageIdentityBadge(BaseModel):
    text: str
    type: str
    count: Optional[int] = None # Count is present for sub_gifter and subscriber

class ChatMessageIdentity(BaseModel):
    username_color: Optional[str] = None # Not always present
    badges: List[ChatMessageIdentityBadge]

class ChatMessageParticipant(BaseModel): # Common fields for sender and broadcaster
    is_anonymous: Optional[bool] = None # Made Optional
    user_id: int # Docs show integer, adjust if Kick uses string IDs elsewhere consistently
    username: str
    is_verified: Optional[bool] = None # Made Optional
    profile_picture: Optional[HttpUrl] = None
    channel_slug: str
    identity: Optional[ChatMessageIdentity] = None # Null for broadcaster, present for sender

class ChatMessageSender(ChatMessageParticipant):
    identity: ChatMessageIdentity # Sender always has identity based on docs

class ChatMessageBroadcaster(ChatMessageParticipant):
    identity: None = None # Explicitly None for broadcaster as per docs

class ChatMessageEmotePosition(BaseModel):
    s: int # start
    e: int # end

class ChatMessageEmote(BaseModel):
    emote_id: str
    positions: List[ChatMessageEmotePosition]

class ChatMessageSentData(BaseModel):
    message_id: str = Field(..., alias="id") # Corresponds to "id" in Kick's chat message payload
    content: str
    created_at: datetime # Corresponds to "created_at" in Kick's chat message payload. CORRECTLY USING 'datetime' here.
    sender: ChatMessageSender
    broadcaster: ChatMessageBroadcaster
    emotes: Optional[List[ChatMessageEmote]] = None # Emotes can be optional
    # Kick docs payload for webhook is flat, not nested under 'data' for ChatMessageSent itself.
    # The KickEventBase expects a 'data' field. This means the ChatMessageSentData itself IS the 'data'.
    # However, the Kick documentation shows the payload for "chat.message.sent" webhook *is* the ChatMessageSentData structure directly.
    # This requires a small adjustment in how we define ChatMessageSentEvent or how it's handled.
    # For now, let's assume the webhook handler will pass the entire payload as 'data' to a wrapper.

# Simpler ChatMessageSentEvent that directly reflects the Kick webhook payload structure
# This will not use KickEventBase directly because the payload structure is different.
class ChatMessageSentWebhookPayload(BaseModel):
    message_id: str
    broadcaster: ChatMessageBroadcaster
    sender: ChatMessageSender
    content: str
    emotes: Optional[List[ChatMessageEmote]] = None
    # We need to add 'event' and potentially other fields if parse_kick_event_payload is to be used generally.
    # Or, handle this type specially in KickWebhookHandler.handle_webhook

    # For now, to make it compatible with the existing _event_model_map and parse_kick_event_payload,
    # we need a model that has an 'event' discriminator and a 'data' field.
    # We can populate 'id', 'channel_id', 'created_at' in the handler if needed.

# Let's stick to trying to make it fit KickEventBase for now, assuming the handler will adapt the raw payload.
# The handler will need to construct a dict that matches KickEventBase before validation.

# Using ChatMessageSentData as the 'data' part of a KickEventBase-like structure.
class ChatMessageSentEventAdjusted(KickEventBase):
    event: Literal["chat.message.sent"]
    data: ChatMessageSentData
    # id, channel_id, created_at will be populated by the webhook handler before validation
    # if they are not present in the actual webhook payload for chat messages.

# Update Union and Map
AnyKickEvent = Union[
    FollowEvent,
    SubscriptionEventKick, 
    GiftedSubscriptionEvent,
    SubscriptionRenewalEvent,
    ChatMessageSentEventAdjusted # Added new event type
]

_event_model_map = {
    "channel.followed": FollowEvent,
    "channel.subscription.new": SubscriptionEventKick,
    "channel.subscription.gifts": GiftedSubscriptionEvent,
    "channel.subscription.renewal": SubscriptionRenewalEvent,
    "chat.message.sent": ChatMessageSentEventAdjusted # Added new event type
}

def parse_kick_event_payload(payload: dict) -> Optional[AnyKickEvent]:
    event_type = payload.get("event")
    model = _event_model_map.get(event_type)
    if model:
        try:
            return model.model_validate(payload)
        except ValidationError as e:
            # Consider logging the validation error details here
            import logging # RE-ENABLED
            logger = logging.getLogger(__name__) # RE-ENABLED
            logger.warning(f"Pydantic validation error for event {event_type}: {e}") # RE-ENABLED
            return None
    return None

# Remove the old BaseEvent and specific events that wrapped it,
# as KickEventBase now serves as the top-level structure.
# class BaseEvent(BaseModel): ... (OLD - REMOVE)
# class FollowEvent(BaseEvent): ... (OLD - REMOVE)
# class SubscriptionEvent(BaseEvent): ... (OLD - REMOVE)
# class GiftedSubscriptionEvent(BaseEvent): ... (OLD - REMOVE) 