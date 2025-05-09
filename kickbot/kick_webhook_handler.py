import aiohttp
from aiohttp import web
import json
import logging
from typing import Dict, Callable, Optional, Any, Coroutine, Union

from pydantic import ValidationError
from .event_models import FollowEvent, SubscriptionEvent, GiftedSubscriptionEvent, AnyKickEvent, parse_kick_event_payload

# Set up logging
# logging.basicConfig(level=logging.INFO) # This is often configured at the application entry point
logger = logging.getLogger(__name__) # Changed to __name__ for best practice

class KickWebhookHandler:
    """
    Handler for Kick API webhook events.
    
    This class provides an HTTP server to receive webhook events from Kick's API,
    validate them, and dispatch them to registered event handlers.
    """
    
    def __init__(self, webhook_path: str = "/kick/events", port: int = 8000, log_events: bool = True, signature_verification: bool = False):
        """
        Initialize the webhook handler.
        
        Args:
            webhook_path: The URL path where webhook events will be received
            port: The port to run the HTTP server on
            log_events: Whether to log received events for debugging
            signature_verification: Whether to verify signatures on incoming webhooks
        """
        self.webhook_path = webhook_path
        self.port = port
        self.log_events = log_events
        self.signature_verification = signature_verification
        # self.signature_verifier = None # Assuming this would be set up if signature_verification is True
        
        # Dictionary to store event handlers
        # Key: event name (e.g., "channel.subscribed")
        # Value: async function that takes a parsed Pydantic event model as argument
        self.event_handlers: Dict[str, Callable[[AnyKickEvent], Coroutine[Any, Any, None]]] = {}

        # Register specific event handlers
        self.register_event_handler("channel.followed", self.handle_follow_event)
        self.register_event_handler("channel.subscribed", self.handle_subscription_event)
        self.register_event_handler("channel.subscription.gifted", self.handle_gifted_subscription_event)
    
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
        logger.info(
            f"CHANNEL: {event.channel_id} - EVENT: {event.event} - FOLLOWER: {event.data.follower.username} (ID: {event.data.follower.id}) followed at {event.data.followed_at}. Event ID: {event.id}"
        )
        # TODO: Implement further bot logic for follow events (e.g., send chat message, update stats)

    async def handle_subscription_event(self, event: SubscriptionEvent):
        logger.info(
            f"CHANNEL: {event.channel_id} - EVENT: {event.event} - SUBSCRIBER: {event.data.subscriber.username} (ID: {event.data.subscriber.id}) subscribed. \
            Tier: {event.data.subscription_tier}, Months: {event.data.months_subscribed or 'N/A'}, IsGift: {event.data.is_gift}, Time: {event.data.subscribed_at}. Event ID: {event.id}"
        )
        # TODO: Implement further bot logic for subscription events

    async def handle_gifted_subscription_event(self, event: GiftedSubscriptionEvent):
        gifter_name = event.data.gifter.username if event.data.gifter else "Anonymous/System"
        gifter_id = event.data.gifter.id if event.data.gifter else "N/A"
        recipient_details = [f"{rec.username} (ID: {rec.id})" for rec in event.data.recipients]
        recipients_str = ", ".join(recipient_details)
        
        logger.info(
            f"CHANNEL: {event.channel_id} - EVENT: {event.event} - GIFTER: {gifter_name} (ID: {gifter_id}) gifted {len(event.data.recipients)} sub(s) to {recipients_str}. \
            Tier: {event.data.subscription_tier}, Time: {event.data.gifted_at}. Event ID: {event.id}"
        )
        # TODO: Implement further bot logic for gifted subs

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