import aiohttp
from aiohttp import web
import json
import logging
from typing import Dict, Callable, Optional, Any, Coroutine, Union
import datetime # Added for created_at timestamp
import requests
import asyncio

from pydantic import ValidationError
from .event_models import FollowEvent, SubscriptionEventKick, GiftedSubscriptionEvent, SubscriptionRenewalEvent, AnyKickEvent, parse_kick_event_payload, ChatMessageSentEventAdjusted

# Forward reference for type hinting
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .kick_bot import KickBot

# Set up logging
# logging.basicConfig(level=logging.INFO) # This is often configured at the application entry point
logger = logging.getLogger(__name__) # Changed to __name__ for best practice

class KickWebhookHandler:
    """
    Handler for Kick API webhook events.
    
    This class provides an HTTP server to receive webhook events from Kick's API,
    validate them, and dispatch them to registered event handlers.
    """
    
    def __init__(self,
                 kick_bot_instance: 'KickBot', # Added KickBot instance
                 webhook_path: str = "/",  # Changed default to "/"
                 port: int = 8000, 
                 log_events: bool = True, 
                 signature_verification: bool = False,
                 enable_new_webhook_system: bool = True,
                 disable_legacy_gift_handling: bool = False,
                 handle_follow_event_actions: Optional[Dict[str, bool]] = None,
                 handle_subscription_event_actions: Optional[Dict[str, Any]] = None,
                 handle_gifted_subscription_event_actions: Optional[Dict[str, Any]] = None,
                 handle_subscription_renewal_event_actions: Optional[Dict[str, Any]] = None): # Added new config
        """
        Initialize the webhook handler.
        
        Args:
            kick_bot_instance: The KickBot instance
            webhook_path: The URL path where webhook events will be received
            port: The port to run the HTTP server on
            log_events: Whether to log received events for debugging
            signature_verification: Whether to verify signatures on incoming webhooks
            enable_new_webhook_system: Feature flag to enable the new webhook system processing.
            disable_legacy_gift_handling: Feature flag to disable old gift handling if new system is active.
            handle_follow_event_actions: Configuration for follow event actions.
            handle_subscription_event_actions: Configuration for new subscription event actions.
            handle_gifted_subscription_event_actions: Configuration for gifted subscription event actions.
            handle_subscription_renewal_event_actions: Configuration for subscription renewal event actions.
        """
        self.kick_bot_instance = kick_bot_instance # Store the KickBot instance
        self.webhook_path = webhook_path
        self.port = port
        self.log_events = log_events
        self.signature_verification = signature_verification
        self.enable_new_webhook_system = enable_new_webhook_system
        self.disable_legacy_gift_handling = disable_legacy_gift_handling
        # self.signature_verifier = None # Assuming this would be set up if signature_verification is True
        
        # Configuration for follow event actions
        self.send_chat_message_for_follow = True # Default
        if handle_follow_event_actions and isinstance(handle_follow_event_actions.get("SendChatMessage"), bool):
            self.send_chat_message_for_follow = handle_follow_event_actions["SendChatMessage"]
        elif handle_follow_event_actions is not None: # If the dict is provided but key is missing/invalid
            logger.warning("Invalid or missing 'SendChatMessage' in handle_follow_event_actions. Defaulting to True.")

        # Configuration for new subscription event actions
        self.send_chat_message_for_new_sub = True # Default
        self.award_points_for_new_sub = True # Default
        self.points_to_award_for_new_sub = 100 # Default

        if handle_subscription_event_actions:
            if isinstance(handle_subscription_event_actions.get("SendChatMessage"), bool):
                self.send_chat_message_for_new_sub = handle_subscription_event_actions["SendChatMessage"]
            else:
                logger.warning("Invalid or missing 'SendChatMessage' in handle_subscription_event_actions. Using default.")
            
            if isinstance(handle_subscription_event_actions.get("AwardPoints"), bool):
                self.award_points_for_new_sub = handle_subscription_event_actions["AwardPoints"]
            else:
                logger.warning("Invalid or missing 'AwardPoints' in handle_subscription_event_actions. Using default.")
            
            if isinstance(handle_subscription_event_actions.get("PointsToAward"), int):
                self.points_to_award_for_new_sub = handle_subscription_event_actions["PointsToAward"]
            else:
                logger.warning("Invalid or missing 'PointsToAward' in handle_subscription_event_actions. Using default.")

        # Configuration for gifted subscription event actions
        self.send_thank_you_chat_message_for_gifted_sub = True # Default
        self.award_points_to_gifter_for_gifted_sub = True # Default
        self.points_to_gifter_per_sub_for_gifted_sub = 50 # Default
        self.award_points_to_recipients_for_gifted_sub = True # Default
        self.points_to_recipient_for_gifted_sub = 25 # Default

        if handle_gifted_subscription_event_actions:
            if isinstance(handle_gifted_subscription_event_actions.get("SendThankYouChatMessage"), bool):
                self.send_thank_you_chat_message_for_gifted_sub = handle_gifted_subscription_event_actions["SendThankYouChatMessage"]
            else:
                logger.warning("Invalid or missing 'SendThankYouChatMessage' in handle_gifted_subscription_event_actions. Using default.")
            
            if isinstance(handle_gifted_subscription_event_actions.get("AwardPointsToGifter"), bool):
                self.award_points_to_gifter_for_gifted_sub = handle_gifted_subscription_event_actions["AwardPointsToGifter"]
            else:
                logger.warning("Invalid or missing 'AwardPointsToGifter' in handle_gifted_subscription_event_actions. Using default.")

            if isinstance(handle_gifted_subscription_event_actions.get("PointsToGifterPerSub"), int):
                self.points_to_gifter_per_sub_for_gifted_sub = handle_gifted_subscription_event_actions["PointsToGifterPerSub"]
            else:
                logger.warning("Invalid or missing 'PointsToGifterPerSub' in handle_gifted_subscription_event_actions. Using default.")

            if isinstance(handle_gifted_subscription_event_actions.get("AwardPointsToRecipients"), bool):
                self.award_points_to_recipients_for_gifted_sub = handle_gifted_subscription_event_actions["AwardPointsToRecipients"]
            else:
                logger.warning("Invalid or missing 'AwardPointsToRecipients' in handle_gifted_subscription_event_actions. Using default.")

            if isinstance(handle_gifted_subscription_event_actions.get("PointsToRecipient"), int):
                self.points_to_recipient_for_gifted_sub = handle_gifted_subscription_event_actions["PointsToRecipient"]
            else:
                logger.warning("Invalid or missing 'PointsToRecipient' in handle_gifted_subscription_event_actions. Using default.")

        # Configuration for subscription renewal event actions
        self.send_chat_message_for_renewal_sub = True  # Default
        self.award_points_for_renewal_sub = True  # Default
        self.points_to_award_for_renewal_sub = 100  # Default

        if handle_subscription_renewal_event_actions:
            if isinstance(handle_subscription_renewal_event_actions.get("SendChatMessage"), bool):
                self.send_chat_message_for_renewal_sub = handle_subscription_renewal_event_actions["SendChatMessage"]
            else:
                logger.warning("Invalid or missing 'SendChatMessage' in handle_subscription_renewal_event_actions. Using default.")
            
            if isinstance(handle_subscription_renewal_event_actions.get("AwardPoints"), bool):
                self.award_points_for_renewal_sub = handle_subscription_renewal_event_actions["AwardPoints"]
            else:
                logger.warning("Invalid or missing 'AwardPoints' in handle_subscription_renewal_event_actions. Using default.")
            
            if isinstance(handle_subscription_renewal_event_actions.get("PointsToAward"), int):
                self.points_to_award_for_renewal_sub = handle_subscription_renewal_event_actions["PointsToAward"]
            else:
                logger.warning("Invalid or missing 'PointsToAward' in handle_subscription_renewal_event_actions. Using default.")

        # Dictionary to store event handlers
        # Key: event name (e.g., "channel.subscribed")
        # Value: async function that takes a parsed Pydantic event model as argument
        self.event_handlers: Dict[str, Callable[[AnyKickEvent], Coroutine[Any, Any, None]]] = {}

        # Register specific event handlers
        self.register_event_handler("channel.followed", self.handle_follow_event)
        self.register_event_handler("channel.subscription.new", self.handle_subscription_event)
        self.register_event_handler("channel.subscription.gifts", self.handle_gifted_subscription_event)
        self.register_event_handler("channel.subscription.renewal", self.handle_subscription_renewal_event)
        self.register_event_handler("chat.message.sent", self.handle_chat_message_event)
        self.register_event_handler("livestream.status.updated", self.handle_livestream_status_updated)
    
    def run_server(self):
        """Start the HTTP server to listen for webhook events."""
        app = web.Application()
        app.router.add_post('/', self.handle_webhook)
        app.router.add_get('/health', self.health_check)  # Add health check endpoint
        
        logger.info(f"Starting webhook server on port {self.port}, path: {self.webhook_path}")
        web.run_app(app, port=self.port)
    
    async def handle_webhook(self, request: web.Request) -> web.Response:
        """
        Handle incoming webhook requests.
        
        Args:
            request: The HTTP request
            
        Returns:
            HTTP response
        """
        try:
            raw_payload_bytes = await request.read()
            raw_payload_str = raw_payload_bytes.decode('utf-8')

            # Optional: Signature verification would go here
            
            try:
                payload_dict_original = json.loads(raw_payload_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse webhook JSON payload: {raw_payload_str}. Error: {e}")
                return web.Response(status=200, text=f"Received but couldn't parse JSON payload: {e}")
            
            if self.log_events:
                logger.info(f"Received raw webhook event dictionary: {json.dumps(payload_dict_original, indent=2)}")

            # Enhanced event type detection from multiple sources
            kick_event_type_header = request.headers.get("Kick-Event-Type")
            event_type = kick_event_type_header
            
            # Also check payload for event type if header is missing
            if not event_type:
                event_type = payload_dict_original.get("event") or payload_dict_original.get("type")
                
            logger.info(f"Processing webhook event of type: {event_type or 'unknown'}")

            # Process the webhook asynchronously to return 200 immediately
            # This prevents Kick from retrying due to slow processing
            asyncio.create_task(self._process_webhook_payload(payload_dict_original, kick_event_type_header))
            
            # Return 200 immediately to acknowledge receipt
            return web.Response(status=200, text="Event received successfully")
            
        except Exception as e:
            logger.exception(f"Unhandled error handling webhook: {e}") # Use logger.exception to include stack trace
            # Still return 200 to prevent Kick from retrying - we've logged the error
            return web.Response(status=200, text="Event received but processing error occurred")

    async def _process_webhook_payload(self, payload_dict_original, kick_event_type_header):
        """
        Process the webhook payload asynchronously after returning 200 to Kick.
        
        Args:
            payload_dict_original: The parsed JSON payload
            kick_event_type_header: The event type from the header
        """
        try:
            # DIRECT CHAT MESSAGE PROCESSING:
            # Enhanced detection for chat messages - look for multiple possible formats
            is_chat_message = any([
                # Header-based detection
                kick_event_type_header == "chat.message.sent",
                # Direct webhook format
                payload_dict_original.get("message_id") and 
                payload_dict_original.get("content") and 
                payload_dict_original.get("sender"),
                # Event wrapper format
                payload_dict_original.get("event") == "chat.message.sent",
                # Legacy format with 'data' wrapper
                payload_dict_original.get("data") and 
                isinstance(payload_dict_original.get("data"), dict) and
                payload_dict_original.get("data").get("content") and
                payload_dict_original.get("data").get("sender")
            ])
                
            if is_chat_message:
                logger.info(f"Processing chat message directly: '{payload_dict_original.get('content') or payload_dict_original.get('data', {}).get('content')}'")
                
                # If message is in data field, extract it
                actual_message_data = payload_dict_original
                if not payload_dict_original.get("content") and payload_dict_original.get("data") and isinstance(payload_dict_original.get("data"), dict):
                    actual_message_data = payload_dict_original.get("data")
                
                # Process the message directly
                await self._process_chat_message_directly(actual_message_data)
                return

            # For other event types, continue with standard pydantic model processing
            
            # Prepare the payload for parsing
            payload_to_parse = payload_dict_original
            event_type_for_parser = payload_dict_original.get("event") # Default way to get event type

            # If 'event' field is missing in payload, but header is present, use header
            if not event_type_for_parser and kick_event_type_header:
                logger.debug(f"Using Kick-Event-Type header '{kick_event_type_header}' as event type for parser.")
                payload_to_parse['event'] = kick_event_type_header # Add it to the dict if not present
                event_type_for_parser = kick_event_type_header

            # Parse the payload dictionary into a Pydantic model
            parsed_event = parse_kick_event_payload(payload_to_parse)

            if not parsed_event:
                logger.warning(f"Could not parse webhook payload into a known event model. Original Payload: {payload_dict_original}")
                return

            # Dispatch the event using the parsed Pydantic model and raw payload (for debugging)
            await self.dispatch_event(event_type_for_parser, parsed_event, payload_dict_original)
        except Exception as e:
            logger.exception(f"Error processing webhook payload: {e}")
            # Since we've already responded with 200, just log the error

    async def _process_chat_message_directly(self, message_data: dict):
        """
        Process chat messages directly without requiring them to pass through Pydantic model validation.
        This method handles raw message data from Kick's webhook.
        
        Args:
            message_data: The raw chat message data from the webhook
        """
        bot = self.kick_bot_instance
        if not bot:
            logger.error("KickBot instance not available in WebhookHandler for direct chat message processing.")
            return
            
        try:
            # Check if message content contains 'gerard' and send to endpoint
            message_content = message_data.get('content', '')
            sender_username = message_data.get('sender', {}).get('username', '')
            
            if message_content and 'gerard' in message_content.casefold():
                try:
                    req = requests.post("http://192.168.0.30:7862/update_chat", 
                                       json={'nickname': sender_username, 'context': message_content})
                    if req.status_code == 200:
                        logger.info("Webhook: Context updated successfully for gerard message.")
                    else:
                        logger.warning(f"Webhook: Failed to update context: {req.status_code}")
                except Exception as e:
                    logger.error(f"Webhook: Error updating context for gerard message: {e}")
            
            # Structure the message in the format expected by KickMessage class
            sender_identity_badges = []
            sender = message_data.get("sender", {})
            
            if sender.get("identity") and sender.get("identity", {}).get("badges"):
                for b in sender.get("identity", {}).get("badges", []):
                    sender_identity_badges.append({
                        'type': b.get('type', ''),
                        'text': b.get('text', ''),
                        'count': b.get('count', 0)
                    })
            
            # Extract message ID with fallback options for different formats
            message_id = None
            if message_data.get("message_id"):
                message_id = message_data.get("message_id")
            elif message_data.get("id"):
                message_id = message_data.get("id")
            else:
                # Generate a pseudo-unique ID if none is provided
                # This helps with deduplication in case the same message comes through websocket and webhook
                content_hash = hash(message_content + sender_username)
                timestamp = int(datetime.datetime.now().timestamp())
                message_id = f"generated_{content_hash}_{timestamp}"
                
            # Create a properly formatted message that KickMessage class can understand
            formatted_message = {
                "id": message_id,  # Use our extracted/generated ID
                "chatroom_id": str(message_data.get("broadcaster", {}).get("user_id", bot.chatroom_id)),
                "content": message_content,
                "type": "message",
                "created_at": message_data.get("created_at", datetime.datetime.utcnow().isoformat() + "Z"),
                "sender": {
                    "id": str(sender.get("user_id", sender.get("id", "unknown"))),
                    "username": sender.get("username", "unknown"),
                    "slug": sender.get("channel_slug", sender.get("slug", "unknown")),
                    "identity": {
                        "color": sender.get("identity", {}).get("username_color", "#FFFFFF"),
                        "badges": sender_identity_badges
                    }
                }
            }
            
            logger.info(f"Directly processing chat message: '{formatted_message.get('content')}' from {formatted_message.get('sender', {}).get('username')}")
            
            # Use KickBot's _handle_chat_message method for consistent message handling
            # This will also take advantage of the message deduplication mechanism
            try:
                await bot._handle_chat_message(formatted_message)
                logger.debug(f"Webhook: Successfully processed message with KickBot._handle_chat_message")
            except Exception as e:
                logger.error(f"Webhook: Error processing message with KickBot._handle_chat_message: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Webhook: Error directly processing message: {e}", exc_info=True)

    def register_event_handler(self, event_type: str, handler: Callable[[AnyKickEvent], Coroutine[Any, Any, None]]):
        """
        Register a handler for a specific event type.
        
        Args:
            event_type: The event type to handle (e.g., "channel.subscribed")
            handler: Async function that takes the parsed Pydantic event model as argument
        """
        self.event_handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")
    
    async def dispatch_event(self, event_type: str, parsed_event: AnyKickEvent, raw_payload: dict = None): # Added raw_payload parameter
        """
        Dispatch an event to the registered handler.
        
        Args:
            event_type: The type of the event (e.g., "channel.followed")
            parsed_event: The parsed Pydantic model for the event
            raw_payload: The original raw webhook payload (for debugging)
        """
        if event_type in self.event_handlers:
            handler_coro = self.event_handlers[event_type]
            # Use getattr for mock's 'name' attribute, fallback to __name__ for real functions
            handler_display_name = getattr(handler_coro, 'name', None) or handler_coro.__name__

            logger.info(f"Dispatching event {event_type} to {handler_display_name}")
            try:
                # Special handling for gifted subscription handler that needs raw payload for debugging
                if event_type == "channel.subscription.gifts" and handler_coro == self.handle_gifted_subscription_event:
                    await handler_coro(parsed_event, raw_payload)
                else:
                    await handler_coro(parsed_event) # Pass the whole parsed event model
            except Exception as e:
                # Log error from specific handler and re-raise to be caught by handle_webhook for 500 response
                # Use event_type from argument to match test expectation more directly.
                logger.error(f"Error in event handler {handler_display_name} for event {event_type} ({parsed_event.id}): {e}", exc_info=True)
                raise # Re-raise the exception to be caught by the main handler
        else:
            logger.warning(f"No handler registered for event type: {event_type}")

    # --- Specific Event Handler Methods (Task 4.3) ---
    async def handle_follow_event(self, event: FollowEvent):
        if not self.enable_new_webhook_system:
            logger.info(f"New webhook system disabled. Skipping detailed processing for FollowEvent: {event.id}")
            return

        logger.info(
            f"CHANNEL: {event.channel_id} - EVENT: {event.event} - FOLLOWER: {event.data.follower.username} (ID: {event.data.follower.user_id}) followed at {event.data.followed_at}. Event ID: {event.id}"
        )
        
        # Send chat message if new system is enabled and specific flag is true
        if self.send_chat_message_for_follow:
            try:
                await self.kick_bot_instance.send_text(f"Thanks for following, {event.data.follower.username}!")
                logger.info(f"Sent follow thank you message for {event.data.follower.username}")
            except Exception as e:
                logger.error(f"Failed to send follow thank you message for {event.data.follower.username}: {e}", exc_info=True)
        else:
            logger.info(f"'SendChatMessage' for follow event is disabled. Skipping message for {event.data.follower.username}.")

        # (Optional Future) Implement stat update logic if a stats system is introduced.

    async def handle_subscription_event(self, event: SubscriptionEventKick): # Changed type hint
        if not self.enable_new_webhook_system:
            logger.info(f"New webhook system disabled. Skipping detailed processing for SubscriptionEvent: {event.id}")
            return
            
        # Corrected access to fields based on SubscriptionEventData used by SubscriptionEventKick
        subscriber_username = event.data.subscriber.username
        subscriber_id = event.data.subscriber.user_id
        tier = event.data.subscription_tier
        months = event.data.months_subscribed # This is duration (int)
        # created_at for subscription data, not top-level event wrapper
        subscription_time = event.data.created_at 

        logger.info(
            f"CHANNEL: {event.channel_id} - EVENT: {event.event} - SUBSCRIBER: {subscriber_username} (ID: {subscriber_id}) subscribed. \
            Tier: {tier or 'N/A'}, Months Subscribed: {months}, \
            Subscription Time: {subscription_time}. Event ID: {event.id}"
        )

        # Action 2: Send chat message if configured
        if self.send_chat_message_for_new_sub:
            try:
                message = f"Welcome to the sub club, {subscriber_username}! Thanks for subscribing."
                # Potentially add tier and months if desired, e.g.:
                # message = f"Welcome {subscriber_username} to Tier {tier if tier else ''} of the sub club for {months} month(s)!"
                await self.kick_bot_instance.send_text(message)
                logger.info(f"Sent new subscription thank you message for {subscriber_username}")
            except Exception as e:
                logger.error(f"Failed to send new subscription thank you message for {subscriber_username}: {e}", exc_info=True)
        else:
            logger.info(f"'SendChatMessage' for new subscription event is disabled. Skipping message for {subscriber_username}.")

        # Action 3: Award points if configured
        if self.award_points_for_new_sub:
            points_to_award = self.points_to_award_for_new_sub
            try:
                # Assuming self.bot.db.add_points(user_id_str, points_int) or similar exists
                # We need the user_id (string) from the event for the points system.
                # For now, we'll log that we would award points. The actual implementation
                # of add_points would be in KickBot or a DB manager.
                # await self.bot.db_manager.add_points(str(subscriber_id), points_to_award)
                logger.info(f"AWARD_POINTS_PLACEHOLDER: Would award {points_to_award} points to {subscriber_username} (ID: {subscriber_id}) for new subscription.")
                # Example of how it might look if db interaction is directly on bot or via a manager:
                # if hasattr(self.bot, 'database_manager') and hasattr(self.bot.database_manager, 'add_points'):
                #     await self.bot.database_manager.add_points(str(subscriber_id), points_to_award)
                #     logger.info(f"Awarded {points_to_award} points to {subscriber_username} (ID: {subscriber_id}) for new subscription.")
                # else:
                #     logger.warning(f"Points system (e.g., bot.database_manager.add_points) not available. Skipping point award for {subscriber_username}.")

            except Exception as e:
                logger.error(f"Failed to award points to {subscriber_username} for new subscription: {e}", exc_info=True)
        else:
            logger.info(f"'AwardPoints' for new subscription event is disabled. Skipping points for {subscriber_username}.")

    async def handle_gifted_subscription_event(self, event: GiftedSubscriptionEvent, raw_payload: dict = None):
        if not self.enable_new_webhook_system:
            logger.info(f"New webhook system disabled. Skipping detailed processing for GiftedSubscriptionEvent: {event.id}")
            return

        gifter_info = event.data.gifter
        
        # Robust gifter information extraction with multiple fallback strategies
        gifter_username = "Anonymous"
        gifter_id = "N/A"
        
        # CRITICAL DEBUG: Log the complete event structure first
        logger.info(f"DEBUG: ===== COMPLETE GIFTED SUBSCRIPTION EVENT ANALYSIS =====")
        
        # Log the raw webhook payload BEFORE Pydantic processing
        if raw_payload:
            logger.info(f"DEBUG: RAW WEBHOOK PAYLOAD (before Pydantic validation): {json.dumps(raw_payload, indent=2)}")
            
            # Check if gifter data exists in raw payload
            raw_gifter = None
            if 'data' in raw_payload and 'gifter' in raw_payload['data']:
                raw_gifter = raw_payload['data']['gifter']
            elif 'gifter' in raw_payload:
                raw_gifter = raw_payload['gifter']
                
            logger.info(f"DEBUG: RAW GIFTER DATA from webhook: {json.dumps(raw_gifter, indent=2) if raw_gifter else 'NOT FOUND'}")
        else:
            logger.warning(f"DEBUG: raw_payload not provided to handler")
        
        logger.info(f"DEBUG: Full event data (after Pydantic): {event.dict()}")
        logger.info(f"DEBUG: Event data gifter field: {event.data.gifter}")
        logger.info(f"DEBUG: Event data giftees field: {event.data.giftees}")
        
        if gifter_info:
            # Enhanced debug logging to see actual gifter data structure
            logger.info(f"DEBUG: Gifter info structure: {gifter_info}")
            logger.info(f"DEBUG: Gifter type: {type(gifter_info)}")
            
            # Check if it's a Pydantic model and log all fields
            if hasattr(gifter_info, 'dict'):
                logger.info(f"DEBUG: Gifter Pydantic dict: {gifter_info.dict()}")
            if hasattr(gifter_info, '__dict__'):
                logger.info(f"DEBUG: Gifter __dict__: {gifter_info.__dict__}")
            
            # Check all defined fields from GifterInfo model
            pydantic_fields = ['user_id', 'username', 'is_verified', 'profile_picture', 'channel_slug', 'is_anonymous']
            logger.info(f"DEBUG: Checking all GifterInfo model fields:")
            for field in pydantic_fields:
                try:
                    value = getattr(gifter_info, field, 'FIELD_NOT_FOUND')
                    logger.info(f"DEBUG:   {field} = {value} (type: {type(value)})")
                except Exception as e:
                    logger.error(f"DEBUG:   {field} = ERROR: {e}")
        else:
            logger.warning(f"DEBUG: gifter_info is None/falsy - indicates anonymous gift or missing data")
        
        if gifter_info:
            # Try multiple ways to extract username
            username_candidates = [
                getattr(gifter_info, 'username', None),
                getattr(gifter_info, 'name', None),
                getattr(gifter_info, 'user_name', None),
                getattr(gifter_info, 'display_name', None)
            ]
            
            # Try dict-style access if it's a dict-like object
            if hasattr(gifter_info, '__getitem__'):
                try:
                    username_candidates.extend([
                        gifter_info.get('username'),
                        gifter_info.get('name'),
                        gifter_info.get('user_name'),
                        gifter_info.get('display_name')
                    ])
                except:
                    pass
            
            # Find the first non-empty username
            for candidate in username_candidates:
                if candidate and str(candidate).strip() and str(candidate).strip().lower() != 'none':
                    gifter_username = str(candidate).strip()
                    break
            
            # Try multiple ways to extract user_id
            id_candidates = [
                getattr(gifter_info, 'user_id', None),
                getattr(gifter_info, 'id', None),
                getattr(gifter_info, 'userId', None)
            ]
            
            # Try dict-style access for user_id
            if hasattr(gifter_info, '__getitem__'):
                try:
                    id_candidates.extend([
                        gifter_info.get('user_id'),
                        gifter_info.get('id'),
                        gifter_info.get('userId')
                    ])
                except:
                    pass
            
            # Find the first valid user_id
            for candidate in id_candidates:
                if candidate is not None and str(candidate).strip() and str(candidate).strip().lower() != 'none':
                    gifter_id = str(candidate).strip()
                    break
            
            logger.info(f"DEBUG: EXTRACTION RESULT - gifter_username='{gifter_username}', gifter_id='{gifter_id}'")
            
            # Log all candidate results for troubleshooting
            logger.info(f"DEBUG: All username candidates checked: {username_candidates}")
            logger.info(f"DEBUG: All ID candidates checked: {id_candidates}")
            
            # Log all available attributes for debugging
            if hasattr(gifter_info, '__dict__'):
                logger.info(f"DEBUG: Gifter attributes: {list(gifter_info.__dict__.keys())}")
                logger.info(f"DEBUG: Gifter values: {gifter_info.__dict__}")
                
            # Additional analysis: check if the model validation might be stripping data
            logger.info(f"DEBUG: Model validation check - seeing if raw webhook data is being lost:")
            logger.info(f"DEBUG: gifter_info repr: {repr(gifter_info)}")
        else:
            logger.info("DEBUG: Gifter info is None - this is an anonymous gift")
        
        # Override to Anonymous if we couldn't extract a valid username
        if not gifter_username or gifter_username.lower() in ['none', 'null', '']:
            gifter_username = "Anonymous"
        
        recipients = event.data.giftees
        recipient_usernames = [rec.username for rec in recipients]
        recipient_ids = [rec.user_id for rec in recipients]
        num_gifted = len(recipients)

        logger.info(
            f"CHANNEL: {event.channel_id} - EVENT: {event.event} - GIFTER: {gifter_username} (ID: {gifter_id}) gifted {num_gifted} sub(s) to {', '.join(recipient_usernames)}. \
            Tier: {event.data.subscription_tier or 'N/A'}, Time: {event.data.created_at}. Event ID: {event.id}"
        )

        # Action 2: Send chat message thanking the gifter
        if self.send_thank_you_chat_message_for_gifted_sub:
            try:
                # Construct message carefully based on number of recipients
                recipients_display_str = ", ".join(recipient_usernames)
                if num_gifted == 1:
                    message = f"Huge thanks to {gifter_username} for gifting a sub to {recipients_display_str}! Welcome to the club!"
                elif num_gifted > 1:
                    message = f"Wow! {gifter_username} just gifted {num_gifted} subs to the community! Thanks so much! Welcome {recipients_display_str}!"
                else: # Should not happen if event is valid
                    message = f"Thanks {gifter_username} for the support!"
                
                await self.kick_bot_instance.send_text(message)
                logger.info(f"Sent gifted sub thank you message for {gifter_username} gifting to {num_gifted} user(s).")
            except Exception as e:
                logger.error(f"Failed to send gifted sub thank you message for {gifter_username}: {e}", exc_info=True)
        else:
            logger.info(f"'SendThankYouChatMessage' for gifted subs is disabled. Skipping message for gifter {gifter_username}.")

        # Action 3: Award points to gifter using existing _handle_gifted_subscriptions method
        if self.award_points_to_gifter_for_gifted_sub and gifter_username != "Anonymous":
            try:
                # Call the existing _handle_gifted_subscriptions method that sends !subgift_add command
                if hasattr(self.kick_bot_instance, '_handle_gifted_subscriptions'):
                    await self.kick_bot_instance._handle_gifted_subscriptions(gifter_username, num_gifted)
                    logger.info(f"Awarded points to {gifter_username} for gifting {num_gifted} subs via webhook integration")
                else:
                    logger.error(f"_handle_gifted_subscriptions method not available on bot instance")
                    # Fallback to placeholder logging
                    points_per_sub = self.points_to_gifter_per_sub_for_gifted_sub
                    total_points_for_gifter = points_per_sub * num_gifted
                    logger.info(f"FALLBACK_AWARD_POINTS_PLACEHOLDER: Would award {total_points_for_gifter} points ({points_per_sub} per sub * {num_gifted} subs) to gifter {gifter_username} (ID: {gifter_id}).")
            except Exception as e:
                logger.error(f"Failed to award points to {gifter_username} for gifted subs via webhook: {e}", exc_info=True)
                # Continue processing - don't let points failure break webhook acknowledgment
        elif gifter_username == "Anonymous" and self.award_points_to_gifter_for_gifted_sub:
            logger.info(f"Cannot award points to gifter as they are Anonymous. Gifter points awarding for gifted subs is enabled.")
        else:
            logger.info(f"'AwardPointsToGifter' for gifted subs is disabled. Skipping points for gifter {gifter_username}.")

        # Action 4: Award points to recipients
        if self.award_points_to_recipients_for_gifted_sub:
            points_per_recipient = self.points_to_recipient_for_gifted_sub
            for i, recipient_username in enumerate(recipient_usernames):
                recipient_id = recipient_ids[i]
                try:
                    # Placeholder for actual points awarding
                    logger.info(f"AWARD_POINTS_PLACEHOLDER: Would award {points_per_recipient} points to recipient {recipient_username} (ID: {recipient_id}) from gifted sub.")
                except Exception as e:
                    logger.error(f"Failed to process point award (recipient) for {recipient_username} from gifted sub: {e}", exc_info=True)
        else:
            logger.info(f"'AwardPointsToRecipients' for gifted subs is disabled. Skipping points for recipients.")

        if self.disable_legacy_gift_handling:
            logger.info(f"Legacy gift handling is disabled. This GiftedSubscriptionEvent (ID: {event.id}) is being processed solely by the new system.")
        else:
            logger.info(f"Legacy gift handling may still be active. This GiftedSubscriptionEvent (ID: {event.id}) is processed by new system; ensure no double actions.")
        # TODO: Implement further bot logic for gifted subs

    async def handle_subscription_renewal_event(self, event: SubscriptionRenewalEvent):
        if not self.enable_new_webhook_system:
            logger.info(f"New webhook system disabled. Skipping detailed processing for SubscriptionRenewalEvent: {event.id}")
            return

        logger.info(
            f"CHANNEL: {event.channel_id} - EVENT: {event.event} - SUBSCRIBER: {event.data.subscriber.username} (ID: {event.data.subscriber.user_id}) "
            f"renewed subscription for {event.data.months_subscribed} months. "
            f"Tier: {event.data.subscription_tier if event.data.subscription_tier else 'Unknown'}. "
            f"Current period: {event.data.created_at} to {event.data.expires_at}. Event ID: {event.id}"
        )

        # Send chat message if new system is enabled and specific flag is true
        if self.send_chat_message_for_renewal_sub:
            try:
                # Example: "Thanks USERNAME for renewing your Tier TIER_NAME sub for DURATION months!"
                # Tier might be None, handle that.
                tier_message_part = f" Tier {event.data.subscription_tier}" if event.data.subscription_tier else ""
                await self.kick_bot_instance.send_text(
                    f"Thanks {event.data.subscriber.username} for renewing your{tier_message_part} sub for {event.data.months_subscribed} months!"
                )
                logger.info(f"Sent subscription renewal thank you message for {event.data.subscriber.username}.")
            except Exception as e:
                logger.error(f"Failed to send subscription renewal thank you message for {event.data.subscriber.username}: {e}", exc_info=True)
        else:
            logger.info(f"'SendChatMessage' for subscription renewal event is disabled. Skipping message for {event.data.subscriber.username}.")

        # Award points if new system is enabled and specific flag is true
        if self.award_points_for_renewal_sub:
            try:
                # Placeholder for awarding points.
                # This would interact with self.bot.db or a points service.
                # user_id = event.data.subscriber.id
                # points_to_add = self.points_to_award_for_renewal_sub
                # await self.bot.award_points_to_user(user_id, points_to_add) # Example call
                logger.info(
                    f"Placeholder: Awarded {self.points_to_award_for_renewal_sub} points to {event.data.subscriber.username} (ID: {event.data.subscriber.user_id}) for subscription renewal."
                )
            except Exception as e:
                logger.error(f"Failed to award points to {event.data.subscriber.username} for subscription renewal: {e}", exc_info=True)
        else:
            logger.info(f"'AwardPoints' for subscription renewal event is disabled. Skipping point award for {event.data.subscriber.username}.")

    # Placeholder for the new chat message event handler
    async def handle_chat_message_event(self, event: ChatMessageSentEventAdjusted):
        if not self.enable_new_webhook_system:
            logger.info(f"New webhook system disabled. Skipping detailed processing for ChatMessageSentEvent: {event.id}")
            return

        # event.data here is ChatMessageSentData (the actual chat message payload from Kick)
        chat_data = event.data 

        logger.info(
            f"Webhook received CHAT MESSAGE: User {chat_data.sender.username} said '{chat_data.content}' in channel {chat_data.broadcaster.username}"
        )

        # Check if message content contains 'gerard' and send to endpoint
        if chat_data.content and 'gerard' in chat_data.content.casefold():
            try:
                req = requests.post("http://192.168.0.30:7862/update_chat", 
                                   json={'nickname': chat_data.sender.username, 'context': chat_data.content})
                if req.status_code == 200:
                    logger.info("Webhook event handler: Context updated successfully for gerard message.")
                else:
                    logger.warning(f"Webhook event handler: Failed to update context: {req.status_code}")
            except Exception as e:
                logger.error(f"Webhook event handler: Error updating context for gerard message: {e}")

        bot = self.kick_bot_instance
        if not bot:
            logger.error("KickBot instance not available in WebhookHandler for chat message.")
            return

        # Construct the dictionary for KickMessage in the same format as _process_chat_message_directly
        sender_identity_badges = []
        if chat_data.sender.identity and chat_data.sender.identity.badges:
            for b in chat_data.sender.identity.badges:
                sender_identity_badges.append({
                    'type': b.type,
                    'text': b.text,
                    'count': b.count if b.count is not None else 0 # Ensure count is present, default to 0 if None
                })
        
        # Format the message in the same way as _process_chat_message_directly
        message_data_for_km = {
            "id": chat_data.message_id, # This is the actual message_id
            "chatroom_id": str(chat_data.broadcaster.user_id), # Use broadcaster user_id as chatroom_id
            "content": chat_data.content,
            "type": "message", # Original WebSocket messages had this
            "created_at": event.created_at.isoformat() if event.created_at else datetime.datetime.utcnow().isoformat() + "Z",
            "sender": {
                "id": str(chat_data.sender.user_id),
                "username": chat_data.sender.username,
                "slug": chat_data.sender.channel_slug,
                "identity": {
                    "color": chat_data.sender.identity.username_color if chat_data.sender.identity else "#FFFFFF",
                    "badges": sender_identity_badges
                }
            }
        }

        try:
            # Use the KickBot's _handle_chat_message method directly
            # This leverages the message deduplication mechanism
            await bot._handle_chat_message(message_data_for_km)
            logger.debug(f"Webhook handler: Successfully processed message with KickBot._handle_chat_message")
        except Exception as e:
            logger.error(f"Webhook handler: Error processing message with KickBot._handle_chat_message: {e}", exc_info=True)

    async def handle_livestream_status_updated(self, event):
        """
        Handle the livestream.status.updated webhook event to update the bot's is_live flag.
        """
        is_live = getattr(event, 'is_live', None)
        if is_live is not None:
            self.kick_bot_instance.is_live = is_live
            logger.info(f"[Webhook] Updated bot.is_live to {is_live} from livestream.status.updated event.")
        else:
            logger.warning("[Webhook] livestream.status.updated event received without is_live field.")

    async def health_check(self, request: web.Request) -> web.Response:
        """
        Simple health check endpoint to verify webhook server is running.
        
        Returns:
            HTTP response with status information
        """
        status = {
            "status": "ok",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "service": "Sr_Botoshi Webhook Server",
            "webhook_path": self.webhook_path,
            "event_handlers_registered": len(self.event_handlers)
        }
        return web.json_response(status)

# Example usage:
if __name__ == "__main__":
    # Create a handler
    handler = KickWebhookHandler()
    
    # Define an example event handler
    async def on_subscription(data):
        username = data.get("user", {}).get("username", "unknown")
        print(f"New subscription from {username}!")
    
    # Register the handler
    handler.register_event_handler("channel.subscribed", on_subscription)
    
    # Start the server
    handler.run_server() 