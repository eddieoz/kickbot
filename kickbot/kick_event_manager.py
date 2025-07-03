import asyncio
import logging
import aiohttp
from typing import List, Dict, Any, Optional

# Use a forward reference for KickAuthManager if it's in a different module and imported later
# from .kick_auth_manager import KickAuthManager 
from .kick_client import KickClient # Assuming KickClient has an aiohttp.ClientSession

logger = logging.getLogger(__name__)

KICK_API_BASE_URL = "https://api.kick.com/public/v1"

class KickEventManager:
    """
    Manages subscriptions to Kick API events via webhooks.
    """
    def __init__(self, auth_manager: 'KickAuthManager', client: Optional[KickClient], broadcaster_user_id: int):
        """
        Initializes the KickEventManager.

        Args:
            auth_manager: An instance of KickAuthManager to obtain access tokens.
            client: An optional instance of KickClient providing an aiohttp.ClientSession.
            broadcaster_user_id: The user ID of the broadcaster for event subscriptions.
        """
        self.auth_manager = auth_manager
        self.client = client
        self.broadcaster_user_id = broadcaster_user_id
        # Stores IDs of subscriptions successfully made or listed by this manager
        self.active_subscription_ids: List[str] = [] 
        # Direct auth token for fallback authentication
        self.direct_auth_token: str = None
        # HTTP session for OAuth-only mode
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get HTTP session for API calls"""
        if self.client and hasattr(self.client, 'session') and self.client.session:
            return self.client.session
        elif self._session:
            return self._session
        else:
            # Create a new session for OAuth-only mode
            self._session = aiohttp.ClientSession()
            return self._session

    async def _get_headers(self) -> Dict[str, str]:
        """Helper to get authenticated headers for API calls."""
        try:
            # Try using the OAuth token flow first
            token = None
            try:
                # get_valid_token() should be an async method in KickAuthManager returning the token string
                token = await self.auth_manager.get_valid_token()
            except Exception as auth_error:
                logger.warning(f"OAuth token retrieval failed: {auth_error}")
                # Fall back to direct token if available
                if self.direct_auth_token:
                    logger.info("Using direct auth token as fallback for API operations")
                    token = self.direct_auth_token
                else:
                    # No fallback available, re-raise the original error
                    raise
            
            if not token:
                logger.error("Failed to get valid access token for API call. Cannot proceed with event subscriptions.")
                raise Exception("Failed to get valid access token for Kick API.") # Or a custom exception
            
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            # Pass through the original error with more context
            raise Exception(f"Failed to obtain authentication headers for Kick API: {e}")

    async def list_subscriptions(self) -> Optional[List[Dict[str, Any]]]:
        """Lists all current event subscriptions for the authenticated app and broadcaster."""
        url = f"{KICK_API_BASE_URL}/events/subscriptions"
        try:
            # Try to get headers with fallback auth mechanisms
            try:
                headers = await self._get_headers()
            except Exception as auth_e:
                logger.warning(f"Failed to get headers for listing subscriptions: {auth_e}")
                # If we can't authenticate, return empty list rather than None
                # so calling code knows we failed due to auth, not API error
                return []
                
            session = await self._get_session()
            async with session.get(url, headers=headers) as response:
                response_data = await response.json()
                if response.status == 200:
                    logger.info("Successfully listed event subscriptions.")
                    all_subs_for_app = response_data.get("data", [])
                    # Filter for the specific broadcaster this manager is for and update active_subscription_ids
                    broadcaster_subs = [
                        sub for sub in all_subs_for_app 
                        if sub.get("broadcaster_user_id") == self.broadcaster_user_id and sub.get("id")
                    ]
                    self.active_subscription_ids = [sub["id"] for sub in broadcaster_subs]
                    logger.debug(f"Found {len(self.active_subscription_ids)} active subscriptions for broadcaster {self.broadcaster_user_id}: {self.active_subscription_ids}")
                    return broadcaster_subs
                else:
                    logger.error(f"Failed to list event subscriptions: {response.status} - {response_data}")
                    return None
        except Exception as e:
            logger.error(f"Error listing event subscriptions: {e}", exc_info=True)
            return None

    async def subscribe_to_events(self, events_to_subscribe: List[Dict[str, Any]]) -> bool:
        """
        Subscribes to a list of specified events.
        Args:
            events_to_subscribe: A list of event dicts, e.g., [{"name": "channel.subscribed", "version": 1}].
        Returns:
            True if at least one subscription was successful, False otherwise.
        """
        if not events_to_subscribe:
            logger.warning("No events provided to subscribe to.")
            return False

        url = f"{KICK_API_BASE_URL}/events/subscriptions"
        payload = {
            "broadcaster_user_id": self.broadcaster_user_id,
            "events": events_to_subscribe,
            "method": "webhook",
            "webhook_url": "https://webhook.botoshi.sats4.life/events"
        }
        try:
            headers = await self._get_headers()
            session = await self._get_session()
            async with session.post(url, headers=headers, json=payload) as response:
                response_data = await response.json()
                if response.status == 200: # Kick docs indicate 200 OK for successful POST
                    successful_subscriptions = []
                    failed_subscriptions = []
                    newly_added_ids = []
                    for sub_result in response_data.get("data", []):
                        if sub_result.get("subscription_id") and not sub_result.get("error"):
                            successful_subscriptions.append(sub_result)
                            newly_added_ids.append(sub_result["subscription_id"])
                        else:
                            failed_subscriptions.append(sub_result)
                    
                    for sub_id in newly_added_ids:
                        if sub_id not in self.active_subscription_ids:
                            self.active_subscription_ids.append(sub_id)

                    if successful_subscriptions:
                         logger.info(f"Successfully subscribed to events: {[s['name'] for s in successful_subscriptions]}")
                    if failed_subscriptions:
                        logger.error(f"Failed to subscribe to some events for broadcaster {self.broadcaster_user_id}: {failed_subscriptions}")
                    return bool(successful_subscriptions)
                else:
                    logger.error(f"Failed to subscribe to events for broadcaster {self.broadcaster_user_id}: {response.status} - {response_data}")
                    return False
        except Exception as e:
            logger.error(f"Error subscribing to events for broadcaster {self.broadcaster_user_id}: {e}", exc_info=True)
            return False

    async def _unsubscribe_by_ids(self, subscription_ids: List[str]) -> bool:
        """Helper to unsubscribe using a list of subscription IDs."""
        if not subscription_ids:
            logger.info("No subscription IDs provided to unsubscribe.")
            return True

        url = f"{KICK_API_BASE_URL}/events/subscriptions"
        # aiohttp handles list of tuples for params: params=[('id', sub_id1), ('id', sub_id2)]
        params = [("id", sub_id) for sub_id in subscription_ids]
        
        try:
            headers = await self._get_headers()
            session = await self._get_session()
            async with session.delete(url, headers=headers, params=params) as response:
                if response.status == 204: # No Content on successful deletion
                    logger.info(f"Successfully unsubscribed from events: {subscription_ids}")
                    self.active_subscription_ids = [sid for sid in self.active_subscription_ids if sid not in subscription_ids]
                    return True
                else:
                    response_data = await response.text() # Or .json() if it returns a body on error
                    logger.error(f"Failed to unsubscribe from events {subscription_ids}: {response.status} - {response_data}")
                    return False
        except Exception as e:
            logger.error(f"Error unsubscribing from events {subscription_ids}: {e}", exc_info=True)
            return False

    async def clear_all_my_broadcaster_subscriptions(self) -> bool:
        """
        Lists all current subscriptions for this manager's broadcaster_user_id 
        and attempts to delete them. This is useful on shutdown.
        """
        logger.info(f"Attempting to clear all subscriptions for broadcaster ID: {self.broadcaster_user_id}")
        # list_subscriptions will update self.active_subscription_ids with relevant ones
        await self.list_subscriptions() 
        
        if not self.active_subscription_ids: # After listing, if still no relevant IDs
            logger.info(f"No existing subscriptions found for broadcaster ID {self.broadcaster_user_id} to clear.")
            return True
        
        logger.info(f"Found {len(self.active_subscription_ids)} subscriptions to clear for broadcaster {self.broadcaster_user_id}: {self.active_subscription_ids}")
        return await self._unsubscribe_by_ids(list(self.active_subscription_ids)) # Pass a copy

    async def resubscribe_to_configured_events(self, configured_events: List[Dict[str, Any]]):
        """
        Clears all existing subscriptions for the configured broadcaster_user_id 
        and then subscribes to the provided list of events.
        This is the recommended method to call on bot startup.
        """
        logger.info(f"Resubscribing to events for broadcaster ID: {self.broadcaster_user_id}...")
        
        # Clear any existing subscriptions for this broadcaster managed by this app.
        # list_subscriptions within clear_all_my_broadcaster_subscriptions will fetch current state.
        cleared_successfully = await self.clear_all_my_broadcaster_subscriptions()
        
        if not cleared_successfully:
            # Log a warning but attempt to subscribe anyway, as some transient errors might prevent clearing.
            # The subscribe call should ideally handle existing subscriptions gracefully (e.g., Kick API might error or ignore).
            logger.warning(f"Failed to clear all existing subscriptions for broadcaster {self.broadcaster_user_id}. Proceeding with new subscriptions may lead to duplicates or errors.")

        if not configured_events:
            logger.info("No events configured to subscribe to after clearing.")
            # If clearing was successful and no new events, this is a success.
            # If clearing failed, this is still a partial success as no new subscriptions were attempted.
            return cleared_successfully 

        subscribed_successfully = await self.subscribe_to_events(configured_events)
        if subscribed_successfully:
            logger.info(f"Successfully resubscribed to configured events for broadcaster {self.broadcaster_user_id}.")
        else:
            logger.error(f"Failed to subscribe to one or more configured events during resubscription for broadcaster {self.broadcaster_user_id}.")
        
        # The overall success of "resubscribe" depends on the critical step: subscribing to new events.
        # If clearing failed but subscribing succeeded, it's a partial success.
        # If subscribing failed, it's a failure regardless of clearing.
        return subscribed_successfully 