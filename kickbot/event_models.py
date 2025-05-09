from typing import Optional, List, Literal, Union
from pydantic import BaseModel, Field, RootModel, ValidationError, parse_obj_as
import datetime

class UserInfo(BaseModel):
    """Represents basic user information commonly found in events."""
    id: str # Assuming user IDs are strings, adjust if they are integers
    username: str
    # slug: Optional[str] = None # Kick often uses slugs for user profiles

class FollowerInfo(UserInfo):
    """Specific information for a follower."""
    pass

class SubscriberInfo(UserInfo):
    """Specific information for a subscriber."""
    pass

class GifterInfo(UserInfo):
    """Specific information for a gifter."""
    pass

class RecipientInfo(UserInfo):
    """Specific information for a gift recipient."""
    pass

class BaseEventData(BaseModel):
    """Base class for the 'data' field in events, can be empty or have common fields if any."""
    pass

class FollowEventData(BaseEventData):
    """Data specific to a 'channel.followed' event."""
    follower: FollowerInfo
    followed_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class SubscriptionEventData(BaseEventData):
    """Data specific to a 'channel.subscribed' event."""
    subscriber: SubscriberInfo
    subscription_tier: str = Field(..., alias="tier") # e.g., "Tier 1", "Tier 2"
    is_gift: bool = Field(default=False) # Explicitly default is_gift
    months_subscribed: Optional[int] = Field(None, alias="streak_months") # How many consecutive months
    subscribed_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class GiftedSubscriptionEventData(BaseEventData):
    """Data specific to a 'channel.subscription.gifted' event."""
    gifter: Optional[GifterInfo] = None # Gifter might be anonymous or system
    recipients: List[RecipientInfo] # Could be one or more recipients
    subscription_tier: str = Field(..., alias="tier")
    # number_of_gifts: int = Field(1, alias="quantity") # Assuming default 1 if not specified
    gifted_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    # message: Optional[str] = None # Optional message with the gift

# Common structure for the entire webhook payload from Kick
# Assuming Kick's payload has 'event' for type, 'data' for specifics,
# and other metadata like 'id', 'channel_id', 'created_at' at the top level.
class KickEventBase(BaseModel):
    id: str # Assuming this is the event's unique ID from Kick
    event: str # This will be the discriminator, e.g., "channel.followed"
    channel_id: str # ID or slug of the channel
    created_at: datetime.datetime # Timestamp from Kick
    data: BaseEventData # Generic data, will be overridden by specific event types

class FollowEvent(KickEventBase):
    event: Literal["channel.followed"]
    data: FollowEventData

class SubscriptionEvent(KickEventBase):
    event: Literal["channel.subscribed"]
    data: SubscriptionEventData

class GiftedSubscriptionEvent(KickEventBase):
    event: Literal["channel.subscription.gifted"]
    data: GiftedSubscriptionEventData

# Using RootModel for discriminated union if Pydantic v2
# For Pydantic v1, a Union type hint and parse_obj_as is more typical.
# Let's define a Union type that can be used with parse_obj_as.
AnyKickEvent = Union[FollowEvent, SubscriptionEvent, GiftedSubscriptionEvent]

# Example helper function (can be moved to handler or used directly)
def parse_kick_event_payload(payload: dict) -> Optional[AnyKickEvent]:
    try:
        # Pydantic v2's parse_obj_as can automatically handle discriminated unions
        # if the models are set up correctly with Literal discriminators.
        return parse_obj_as(AnyKickEvent, payload)
    except ValidationError as e:
        # Log the validation error for debugging
        # logger.error(f"Pydantic validation error parsing Kick event: {e.json()}")
        # Consider re-raising or returning None based on desired error handling
        print(f"Pydantic validation error: {e}") # Placeholder for logging
        return None

# Remove the old BaseEvent and specific events that wrapped it,
# as KickEventBase now serves as the top-level structure.
# class BaseEvent(BaseModel): ... (OLD - REMOVE)
# class FollowEvent(BaseEvent): ... (OLD - REMOVE)
# class SubscriptionEvent(BaseEvent): ... (OLD - REMOVE)
# class GiftedSubscriptionEvent(BaseEvent): ... (OLD - REMOVE) 