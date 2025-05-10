from typing import Optional, List, Literal, Union
from pydantic import BaseModel, Field, HttpUrl, RootModel, ValidationError, field_validator
import datetime
# import logging # Re-comment import

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
    followed_at: datetime.datetime

class SubscriptionEventData(BaseModel):
    """Data specific to a 'channel.subscription.new' event."""
    subscriber: SubscriberInfo
    subscription_tier: Optional[str] = Field(None, alias="tier") # Tier is not in basic .new payload, make optional
    months_subscribed: int = Field(..., alias="duration") # Map from 'duration' in payload
    created_at: datetime.datetime # Renamed from subscribed_at for consistency, maps to payload's created_at
    expires_at: Optional[datetime.datetime] = None # From payload

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
    created_at: datetime.datetime # Top-level created_at for the event wrapper itself
    data: SubscriptionEventData

    @property
    def is_gift(self) -> bool:
        return False # By definition for channel.subscription.new

class GiftedSubscriptionEventData(BaseModel):
    """Data specific to a 'channel.subscription.gifts' event."""
    gifter: Optional[GifterInfo] = None # Gifter can be anonymous, so GifterInfo itself is optional or its fields are
    giftees: List[RecipientInfo] = Field(..., alias="recipients") # Map from our old 'recipients' or expect 'giftees' from payload
    subscription_tier: Optional[str] = Field(None, alias="tier") # Not in basic .gifts payload, make optional
    created_at: datetime.datetime # Field name from Kick docs for gift event is 'created_at'
    expires_at: Optional[datetime.datetime] = None # From payload

class SubscriptionRenewalEventData(BaseModel):
    """Data specific to a 'channel.subscription.renewal' event."""
    subscriber: SubscriberInfo
    subscription_tier: Optional[str] = Field(None, alias="tier") 
    months_subscribed: int = Field(..., alias="duration") # Cumulative months
    created_at: datetime.datetime # Start of current period
    expires_at: Optional[datetime.datetime] = None # End of current period

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
    created_at: datetime.datetime # Top-level created_at for the event wrapper itself
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
    created_at: datetime.datetime # Timestamp from Kick
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

# Using RootModel for discriminated union if Pydantic v2
# For Pydantic v1, a Union type hint and parse_obj_as is more typical.
# Let's define a Union type that can be used with parse_obj_as.
AnyKickEvent = Union[
    FollowEvent,
    SubscriptionEventKick, # Use the KickEventBase derived version in the Union
    GiftedSubscriptionEvent,
    SubscriptionRenewalEvent
]

# Helper to parse any incoming payload
# RootModel is useful here for parsing based on the 'event' discriminator if pydantic version supports it well
# For now, a simple try-except chain with parse_obj_as is fine.
_event_model_map = {
    "channel.followed": FollowEvent,
    "channel.subscription.new": SubscriptionEventKick, # Map to the KickEventBase derived version
    "channel.subscription.gifts": GiftedSubscriptionEvent,
    "channel.subscription.renewal": SubscriptionRenewalEvent,
}

def parse_kick_event_payload(payload: dict) -> Optional[AnyKickEvent]:
    event_type = payload.get("event")
    model = _event_model_map.get(event_type)
    if model:
        try:
            return model.model_validate(payload)
        except ValidationError as e:
            # Consider logging the validation error details here
            # import logging # Re-comment import
            # logger = logging.getLogger(__name__) # Re-comment logger get
            # logger.warning(f"Pydantic validation error for event {event_type}: {e}") # Re-commented
            return None
    return None

# Remove the old BaseEvent and specific events that wrapped it,
# as KickEventBase now serves as the top-level structure.
# class BaseEvent(BaseModel): ... (OLD - REMOVE)
# class FollowEvent(BaseEvent): ... (OLD - REMOVE)
# class SubscriptionEvent(BaseEvent): ... (OLD - REMOVE)
# class GiftedSubscriptionEvent(BaseEvent): ... (OLD - REMOVE) 