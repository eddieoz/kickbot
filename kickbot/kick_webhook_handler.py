import aiohttp
from aiohttp import web
import json
import logging
from typing import Dict, Callable, Optional, Any, Coroutine, Union

from pydantic import ValidationError
from .event_models import FollowEvent, SubscriptionEventKick, GiftedSubscriptionEvent, SubscriptionRenewalEvent, AnyKickEvent, parse_kick_event_payload

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
                 webhook_path: str = "/kick/events", 
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
        self.bot = kick_bot_instance # Store the KickBot instance
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
    
    def run_server(self):
        """Start the HTTP server to listen for webhook events."""
        app = web.Application()
        app.router.add_post(self.webhook_path, self.handle_webhook)
        
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
            raw_payload = await request.read()
            
            # Optional: Signature verification would go here if enabled and implemented
            # if self.signature_verification and self.signature_verifier:
            # ... verification logic ...
            
            try:
                payload_dict = json.loads(raw_payload.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse webhook JSON payload: {e}")
                return web.Response(status=400, text=f"Invalid JSON payload: {e}")
            
            if self.log_events:
                # Log the raw dict before parsing for easier debugging if parsing fails
                logger.info(f"Received raw webhook event: {json.dumps(payload_dict, indent=2)}") 

            # Parse the payload dictionary into a Pydantic model
            parsed_event = parse_kick_event_payload(payload_dict)

            if not parsed_event:
                logger.warning(f"Could not parse webhook payload into a known event model. Payload: {payload_dict}")
                # Depending on policy, might return 400 or 200 if we don't want Kick to retry unknown structures.
                # For now, let's acknowledge receipt but log it as unhandled.
                return web.Response(status=200, text="Event received but not processed due to unknown structure or validation error.")

            event_type = parsed_event.event # The discriminator field, e.g., "channel.followed"
            
            # Dispatch the event using the parsed Pydantic model
            # The dispatch_event method itself will use this event_type to find the handler
            await self.dispatch_event(event_type, parsed_event) 
            
            return web.Response(status=200, text="Event received and processed")
            
        except Exception as e:
            logger.exception(f"Unhandled error handling webhook: {e}") # Use logger.exception to include stack trace
            return web.Response(status=500, text=f"Internal server error: {e}")
    
    def register_event_handler(self, event_type: str, handler: Callable[[AnyKickEvent], Coroutine[Any, Any, None]]):
        """
        Register a handler for a specific event type.
        
        Args:
            event_type: The event type to handle (e.g., "channel.subscribed")
            handler: Async function that takes the parsed Pydantic event model as argument
        """
        self.event_handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")
    
    async def dispatch_event(self, event_type: str, parsed_event: AnyKickEvent): # Changed event_data to parsed_event
        """
        Dispatch an event to the registered handler.
        
        Args:
            event_type: The type of the event (e.g., "channel.followed")
            parsed_event: The parsed Pydantic model for the event
        """
        if event_type in self.event_handlers:
            handler_coro = self.event_handlers[event_type]
            # Use getattr for mock's 'name' attribute, fallback to __name__ for real functions
            handler_display_name = getattr(handler_coro, 'name', None) or handler_coro.__name__

            logger.info(f"Dispatching event {event_type} to {handler_display_name}")
            try:
                await handler_coro(parsed_event) # Pass the whole parsed event model
            except Exception as e:
                # Log error from specific handler and re-raise to be caught by handle_webhook for 500 response
                logger.error(f"Error in event handler {handler_display_name} for event {event_type}: {e}", exc_info=True)
                raise # Re-raise the exception to be caught by the main handler
        else:
            logger.warning(f"No handler registered for event type: {event_type}")

    # --- Specific Event Handler Methods (Task 4.3) ---
    async def handle_follow_event(self, event: FollowEvent):
        if not self.enable_new_webhook_system:
            logger.info(f"New webhook system disabled. Skipping detailed processing for FollowEvent: {event.id}")
            return

        logger.info(
            f"CHANNEL: {event.channel_id} - EVENT: {event.event} - FOLLOWER: {event.data.follower.username} (ID: {event.data.follower.id}) followed at {event.data.followed_at}. Event ID: {event.id}"
        )
        
        # Send chat message if new system is enabled and specific flag is true
        if self.send_chat_message_for_follow:
            try:
                await self.bot.send_text(f"Thanks for following, {event.data.follower.username}!")
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
        subscriber_id = event.data.subscriber.id
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
                await self.bot.send_text(message)
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

    async def handle_gifted_subscription_event(self, event: GiftedSubscriptionEvent):
        if not self.enable_new_webhook_system:
            logger.info(f"New webhook system disabled. Skipping detailed processing for GiftedSubscriptionEvent: {event.id}")
            return

        gifter_info = event.data.gifter
        gifter_username = gifter_info.username if gifter_info and gifter_info.username else "Anonymous"
        gifter_id = gifter_info.id if gifter_info and gifter_info.id else "N/A"
        
        recipients = event.data.giftees
        recipient_usernames = [rec.username for rec in recipients]
        recipient_ids = [rec.id for rec in recipients]
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
                
                await self.bot.send_text(message)
                logger.info(f"Sent gifted sub thank you message for {gifter_username} gifting to {num_gifted} user(s).")
            except Exception as e:
                logger.error(f"Failed to send gifted sub thank you message for {gifter_username}: {e}", exc_info=True)
        else:
            logger.info(f"'SendThankYouChatMessage' for gifted subs is disabled. Skipping message for gifter {gifter_username}.")

        # Action 3: Award points to gifter
        if self.award_points_to_gifter_for_gifted_sub and gifter_username != "Anonymous":
            points_per_sub = self.points_to_gifter_per_sub_for_gifted_sub
            total_points_for_gifter = points_per_sub * num_gifted
            try:
                # Placeholder for actual points awarding
                logger.info(f"AWARD_POINTS_PLACEHOLDER: Would award {total_points_for_gifter} points ({points_per_sub} per sub * {num_gifted} subs) to gifter {gifter_username} (ID: {gifter_id}).")
            except Exception as e:
                logger.error(f"Failed to process point award (gifter) for {gifter_username} for gifted subs: {e}", exc_info=True)
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
            f"CHANNEL: {event.channel_id} - EVENT: {event.event} - SUBSCRIBER: {event.data.subscriber.username} (ID: {event.data.subscriber.id}) "
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
                await self.bot.send_text(
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
                    f"Placeholder: Awarded {self.points_to_award_for_renewal_sub} points to {event.data.subscriber.username} (ID: {event.data.subscriber.id}) for subscription renewal."
                )
            except Exception as e:
                logger.error(f"Failed to award points to {event.data.subscriber.username} for subscription renewal: {e}", exc_info=True)
        else:
            logger.info(f"'AwardPoints' for subscription renewal event is disabled. Skipping point award for {event.data.subscriber.username}.")

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