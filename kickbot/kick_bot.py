import asyncio
import json
import logging
from urllib.parse import quote_plus, urlencode
import aiohttp
from aiohttp import web
import requests
import websockets

from datetime import timedelta
from typing import Callable, Optional, Any, Coroutine, List, Dict

from .constants import KickBotException
from .kick_client import KickClient
from .kick_message import KickMessage
from .kick_moderator import Moderator
from .kick_webhook_handler import KickWebhookHandler
from .kick_auth_manager import KickAuthManager, DEFAULT_TOKEN_FILE
from .kick_event_manager import KickEventManager
from .kick_helper import (
    get_ws_uri,
    get_streamer_info,
    get_current_viewers,
    get_chatroom_settings,
    get_bot_settings,
    message_from_data,
    send_message_in_chat,
    send_reply_in_chat
)

from utils.TwitchMarkovChain.MarkovChainBot import MarkovChain
from utils.TwitchMarkovChain.Settings import Settings, SettingsData
from utils.TwitchMarkovChain.Database import Database
from utils.TwitchMarkovChain.Timer import LoopingTimer
from TwitchWebsocket import Message, TwitchWebsocket
import socket, time, logging, re, string
from nltk.tokenize import sent_tokenize

logger = logging.getLogger(__name__)

with open('settings.json') as f:
    settings = json.load(f)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class KickBot:
    """
    Main class for interacting with the Bot API.
    """
    def __init__(self, username: str, password: str) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)  # FORCE DEBUG LEVEL FOR THIS LOGGER INSTANCE
        
        # Ensure there's a handler that can output DEBUG messages
        # This might add a duplicate handler if basicConfig is also working, 
        # but for diagnostics, seeing the message is key.
        if not self.logger.handlers or not any(h.level <= logging.DEBUG for h in self.logger.handlers):
            # Remove existing handlers if they might be filtering out DEBUG
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
            
            handler = logging.StreamHandler() # Outputs to stderr by default
            handler.setLevel(logging.DEBUG) # Handler must also be at DEBUG
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.propagate = False # Avoid duplicate messages from root logger if it also has handlers

        # HTTP Session for all aiohttp requests - to be initialized in run()
        self.http_session: Optional[aiohttp.ClientSession] = None

        # KickClient will be initialized after http_session is ready
        self.client: Optional[KickClient] = None
        # Auth Manager will be initialized after client is ready
        self.auth_manager: Optional[KickAuthManager] = None
        # Event Manager will be initialized after auth_manager and broadcaster_id are ready
        self.event_manager: Optional[KickEventManager] = None

        self._ws_uri = get_ws_uri()
        self._socket_id: Optional[str] = None
        self.streamer_name: Optional[str] = None
        self.streamer_slug: Optional[str] = None
        self.streamer_info: Optional[dict] = None
        self.chatroom_info: Optional[dict] = None
        self.chatroom_settings: Optional[dict] = None
        self.chatroom_id: Optional[int] = None
        self.bot_settings: Optional[dict] = None
        self.is_mod: bool = False
        self.is_super_admin: bool = False
        self.moderator: Optional[Moderator] = None
        self.handled_commands: dict[str, Callable] = {}
        self.handled_messages: dict[str, Callable] = {}
        self.timed_events: list[dict] = []
        self._is_active = True

        # Webhook Handler
        self.webhook_handler: Optional[KickWebhookHandler] = None
        self.webhook_runner: Optional[web.AppRunner] = None
        self.webhook_site: Optional[web.TCPSite] = None
        self.webhook_enabled: bool = False
        self.webhook_path: str = "/kick/events"
        self.webhook_port: int = 8081

        # Event Subscription Config
        self.kick_events_to_subscribe: List[Dict[str, Any]] = []

        # Markov Chain
        self.prev_message_t = 0
        self._enabled = True
        self.link_regex = re.compile(r"\w+\.[a-z]{2,}")
        self.mod_list = []
        self.set_blacklist() # This might be okay if blacklist.txt is static

        # Fill previously initialised variables with data from the settings.txt file
        # Settings(self) # Commented out: settings are applied via set_settings method
        # self.db = Database(self.chan) # Commented out: self.chan not set here; Markov DB init needs review

        # Store credentials passed to __init__ if they are intended for the Kick client
        # These are currently unused in favor of settings.json for KickClient credentials
        self._init_username = username 
        self._init_password = password

        # Set up daemon Timer to send help messages
        # if self.help_message_timer > 0: # Commented out: help_message_timer not set here
        #     self.help_timer = LoopingTimer(self.help_message_timer, self.send_help_message)
        #     self.help_timer.start()
        
        # Set up daemon Timer to send automatic generation messages
        # if self.automatic_generation_timer > 0: # Commented out: automatic_generation_timer not set here
        #     self.autogen_timer = LoopingTimer(self.automatic_generation_timer, self.generate_random_sentence_from_time)
        #     self.autogen_timer.start()

        # self.ws = TwitchWebsocket(host=self.host, # Commented out: Depends on settings
        #                           port=self.port,
        #                           chan=self.chan,
        #                           nick=self.nick,
        #                           auth=self.auth,
        #                           callback=MarkovChain.message_handler,
        #                           capability=["commands", "tags"],
        #                           live=True)

        # Add message ID cache for deduplication
        self.processed_message_ids = set()
        self.max_cache_size = 1000  # Limit cache size to prevent memory issues

    def set_settings(self, settings: SettingsData):
        """Fill class instance attributes based on the settings file.

        Args:
            settings (SettingsData): The settings dict with information from the settings file.
        """
        self.host = settings["Host"]
        self.port = settings["Port"]
        self.chan = settings["Channel"]
        self.nick = settings["Nickname"]
        self.auth = settings["Authentication"]
        self.denied_users = [user.lower() for user in settings["DeniedUsers"]] + [self.nick.lower()]
        self.allowed_users = [user.lower() for user in settings["AllowedUsers"]]
        self.cooldown = settings["Cooldown"]
        self.key_length = settings["KeyLength"]
        self.max_sentence_length = settings["MaxSentenceWordAmount"]
        self.min_sentence_length = settings["MinSentenceWordAmount"]
        self.help_message_timer = settings["HelpMessageTimer"]
        self.automatic_generation_timer = settings["AutomaticGenerationTimer"]
        self.whisper_cooldown = settings["WhisperCooldown"]
        self.enable_generate_command = settings["EnableGenerateCommand"]
        self.sent_separator = settings["SentenceSeparator"]
        self.allow_generate_params = settings["AllowGenerateParams"]
        self.generate_commands = tuple(settings["GenerateCommands"])
        
        # Initialize MarkovChain Database after settings are loaded
        try:
            self.db = Database(self.chan)
            self.logger.info(f"MarkovChain Database initialized for channel: {self.chan}")
        except Exception as e:
            self.logger.error(f"Failed to initialize MarkovChain Database: {e}")
        
        # Set up timers for MarkovChain functionality if enabled
        if hasattr(self, 'help_message_timer') and self.help_message_timer > 0:
            if self.help_message_timer < 300:
                self.logger.warning("Value for \"HelpMessageTimer\" must be at least 300 seconds, or a negative number for no help messages.")
            else:
                try:
                    self.help_timer = LoopingTimer(self.help_message_timer, self.send_help_message)
                    self.help_timer.start()
                    self.logger.info(f"Help message timer started with interval: {self.help_message_timer} seconds")
                except Exception as e:
                    self.logger.error(f"Failed to start help message timer: {e}")
        
        if hasattr(self, 'automatic_generation_timer') and self.automatic_generation_timer > 0:
            if self.automatic_generation_timer < 30:
                self.logger.warning("Value for \"AutomaticGenerationTimer\" must be at least 30 seconds, or a negative number for no automatic generations.")
            else:
                try:
                    self.autogen_timer = LoopingTimer(self.automatic_generation_timer, self.send_automatic_generation_message)
                    self.autogen_timer.start()
                    self.logger.info(f"Automatic generation timer started with interval: {self.automatic_generation_timer} seconds")
                except Exception as e:
                    self.logger.error(f"Failed to start automatic generation timer: {e}")
        
        # Initialize TwitchWebsocket for MarkovChain if not already created
        try:
            self.ws = TwitchWebsocket(host=self.host, 
                                     port=self.port,
                                     chan=self.chan,
                                     nick=self.nick,
                                     auth=self.auth,
                                     callback=MarkovChain.message_handler,
                                     capability=["commands", "tags"],
                                     live=True)
            self.logger.info("TwitchWebsocket for MarkovChain initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize TwitchWebsocket for MarkovChain: {e}")
            
        # Load Webhook settings
        self.webhook_enabled = settings.get("KickWebhookEnabled", False)
        self.webhook_path = settings.get("KickWebhookPath", "/kick/events")
        self.webhook_port = settings.get("KickWebhookPort", 8081)

        # Load Event Subscription settings
        raw_events = settings.get("KickEventsToSubscribe", [])
        # Basic validation for event structure
        self.kick_events_to_subscribe = [
            event for event in raw_events 
            if isinstance(event, dict) and "name" in event and "version" in event
        ]
        if len(self.kick_events_to_subscribe) != len(raw_events):
            self.logger.warning("Some configured Kick events to subscribe were invalid and have been filtered out.")

        # Load Feature Flags
        feature_flags_config = settings.get("FeatureFlags", {})
        self.enable_new_webhook_system = feature_flags_config.get("EnableNewWebhookEventSystem", True) # Default to True
        self.disable_legacy_gift_handling = feature_flags_config.get("DisableLegacyGiftEventHandling", False) # Default to False
        if not isinstance(feature_flags_config, dict) or \
           not isinstance(self.enable_new_webhook_system, bool) or \
           not isinstance(self.disable_legacy_gift_handling, bool):
            self.logger.warning(
                "FeatureFlags configuration is invalid or missing expected boolean flags. Using defaults: "
                f"EnableNewWebhookEventSystem={self.enable_new_webhook_system}, "
                f"DisableLegacyGiftEventHandling={self.disable_legacy_gift_handling}"
            )
            # Ensure defaults are applied if structure was totally wrong
            self.enable_new_webhook_system = True if not isinstance(self.enable_new_webhook_system, bool) else self.enable_new_webhook_system
            self.disable_legacy_gift_handling = False if not isinstance(self.disable_legacy_gift_handling, bool) else self.disable_legacy_gift_handling

        # Load event action configurations
        self.handle_follow_event_actions = settings.get("HandleFollowEventActions", {"SendChatMessage": True}) # Default
        if not isinstance(self.handle_follow_event_actions, dict) or \
           not isinstance(self.handle_follow_event_actions.get("SendChatMessage"), bool):
            self.logger.warning(
                "HandleFollowEventActions configuration is invalid or missing SendChatMessage boolean. Using default: SendChatMessage=True"
            )
            self.handle_follow_event_actions = {"SendChatMessage": True}

        self.handle_subscription_event_actions = settings.get("HandleSubscriptionEventActions", { # Defaults
            "SendChatMessage": True, 
            "AwardPoints": True, 
            "PointsToAward": 100
        })
        if not isinstance(self.handle_subscription_event_actions, dict) or \
           not isinstance(self.handle_subscription_event_actions.get("SendChatMessage"), bool) or \
           not isinstance(self.handle_subscription_event_actions.get("AwardPoints"), bool) or \
           not isinstance(self.handle_subscription_event_actions.get("PointsToAward"), int):
            self.logger.warning(
                "HandleSubscriptionEventActions configuration is invalid or missing expected keys/types. Using defaults."
            )
            self.handle_subscription_event_actions = {
                "SendChatMessage": True, 
                "AwardPoints": True, 
                "PointsToAward": 100
            }

        self.handle_gifted_subscription_event_actions = settings.get("HandleGiftedSubscriptionEventActions", { # Defaults
            "SendThankYouChatMessage": True,
            "AwardPointsToGifter": True,
            "PointsToGifterPerSub": 50,
            "AwardPointsToRecipients": True,
            "PointsToRecipient": 25
        })
        if not isinstance(self.handle_gifted_subscription_event_actions, dict) or \
           not isinstance(self.handle_gifted_subscription_event_actions.get("SendThankYouChatMessage"), bool) or \
           not isinstance(self.handle_gifted_subscription_event_actions.get("AwardPointsToGifter"), bool) or \
           not isinstance(self.handle_gifted_subscription_event_actions.get("PointsToGifterPerSub"), int) or \
           not isinstance(self.handle_gifted_subscription_event_actions.get("AwardPointsToRecipients"), bool) or \
           not isinstance(self.handle_gifted_subscription_event_actions.get("PointsToRecipient"), int):
            self.logger.warning(
                "HandleGiftedSubscriptionEventActions configuration is invalid or missing expected keys/types. Using defaults."
            )
            self.handle_gifted_subscription_event_actions = {
                "SendThankYouChatMessage": True,
                "AwardPointsToGifter": True,
                "PointsToGifterPerSub": 50,
                "AwardPointsToRecipients": True,
                "PointsToRecipient": 25
            }

        self.handle_subscription_renewal_event_actions = settings.get("HandleSubscriptionRenewalEventActions", { # Defaults
            "SendChatMessage": True,
            "AwardPoints": True,
            "PointsToAward": 100 # Default points for renewal
        })
        if not isinstance(self.handle_subscription_renewal_event_actions, dict) or \
           not isinstance(self.handle_subscription_renewal_event_actions.get("SendChatMessage"), bool) or \
           not isinstance(self.handle_subscription_renewal_event_actions.get("AwardPoints"), bool) or \
           not isinstance(self.handle_subscription_renewal_event_actions.get("PointsToAward"), int):
            self.logger.warning(
                "HandleSubscriptionRenewalEventActions configuration is invalid or missing expected keys/types. Using defaults."
            )
            self.handle_subscription_renewal_event_actions = {
                "SendChatMessage": True,
                "AwardPoints": True,
                "PointsToAward": 100
            }

    def send_help_message(self) -> None:
        """Send a Help message to the connected chat, as long as the bot wasn't disabled."""
        if self._enabled:
            self.logger.info("Help message sent.")
            try:
                asyncio.create_task(self.send_text("Learn how this bot generates sentences here: https://github.com/CubieDev/TwitchMarkovChain#how-it-works"))
            except Exception as e:
                self.logger.error(f"Error sending help message: {e}", exc_info=True)
    
    def send_automatic_generation_message(self) -> None:
        """Send an automatic generation message to the connected chat.
        
        As long as the bot wasn't disabled, just like if someone typed "!g" in chat.
        """
        if self._enabled:
            try:
                sentence, success = self.generate()
                if success:
                    self.logger.info(f"Auto-generating: {sentence}")
                    asyncio.create_task(self.send_text(sentence))
                else:
                    self.logger.info("Attempted to output automatic generation message, but there is not enough learned information yet.")
            except Exception as e:
                self.logger.error(f"Error sending automatic generation message: {e}", exc_info=True)

    def write_blacklist(self, blacklist: List[str]) -> None:
        """Write blacklist.txt given a list of banned words.

        Args:
            blacklist (List[str]): The list of banned words to write.
        """
        logger.debug("Writing Blacklist...")
        with open("blacklist.txt", "w") as f:
            f.write("\n".join(sorted(blacklist, key=lambda x: len(x), reverse=True)))
        logger.debug("Written Blacklist.")

    def set_blacklist(self) -> None:
        """Read blacklist.txt and set `self.blacklist` to the list of banned words."""
        logger.debug("Loading Blacklist...")
        try:
            with open("blacklist.txt", "r") as f:
                self.blacklist = [l.replace("\n", "") for l in f.readlines()]
                logger.debug("Loaded Blacklist.")
        
        except FileNotFoundError:
            logger.warning("Loading Blacklist Failed!")
            self.blacklist = ["<start>", "<end>"]
            self.write_blacklist(self.blacklist)

    def poll(self):
        """
        Main function to activate the bot polling.
        """
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.run())
        except KeyboardInterrupt:
            self.logger.info("Bot stopping due to KeyboardInterrupt...")
        finally:
            if loop.is_running():
                 loop.run_until_complete(self.shutdown())
            else:
                 asyncio.run(self.shutdown())
            self.logger.info("Bot stopped.")

    async def _initialize_client_if_needed(self):
        # This method now assumes self.http_session is already set if called from run()
        if not self.client:
            kick_email = settings.get("KickEmail")
            kick_pass = settings.get("KickPass")
            if not kick_email or not kick_pass:
                self.logger.error("Kick email or password not found in settings.json. Cannot initialize KickClient.")
                raise KickBotException("Kick credentials not found in settings.") # Raise to halt
            
            if not self.http_session:
                self.logger.error("aiohttp.ClientSession not available. Cannot initialize KickClient.")
                raise KickBotException("aiohttp.ClientSession not initialized before KickClient.") # Raise to halt

            self.client = KickClient(kick_email, kick_pass, aiohttp_session=self.http_session)
            self.logger.info("KickClient initialized.")
        
        if not self.auth_manager:
            # Always use the default token file as specified by the user.
            token_file_name = DEFAULT_TOKEN_FILE # from kick_auth_manager.py
            self.auth_manager = KickAuthManager(token_file=token_file_name)
            self.logger.info(f"KickAuthManager initialized with token file: {token_file_name}")

    async def run(self):
        """Main async method to run bot components."""
        try:
            async with aiohttp.ClientSession() as session:
                self.http_session = session
                self.logger.info("aiohttp.ClientSession created and active.")

                # Initialize client and auth_manager first
                await self._initialize_client_if_needed()

                # Ensure streamer_name is set before proceeding
                if not self.streamer_name:
                    self.logger.error("Streamer name not set. Call set_streamer() before run().")
                    # Optionally, prompt for streamer name or load from a default if that's desired behavior.
                    raise KickBotException("Streamer name not set.") # Critical to proceed

                # Now that client is initialized, fetch streamer-specific info
                if self.client: # Check if client was successfully initialized
                    get_streamer_info(self) # Populates self.streamer_info, including id
                    get_chatroom_settings(self)
                    get_bot_settings(self)
                    self.logger.info(f"Fetched initial info for streamer: {self.streamer_name}")
                else:
                    # This case should be caught by exceptions in _initialize_client_if_needed
                    self.logger.error("KickClient not available after initialization attempt. Cannot fetch streamer info.")
                    raise KickBotException("KickClient failed to initialize.")

                # Initialize Event Manager and subscribe to events if new system is enabled and streamer info is available
                if self.enable_new_webhook_system and self.webhook_enabled:
                    if self.streamer_info and self.streamer_info.get('id') and self.auth_manager and self.client:
                        broadcaster_id_val = self.streamer_info['id']
                        if not self.event_manager: # Initialize only if not already done
                            self.event_manager = KickEventManager(
                                auth_manager=self.auth_manager,
                                client=self.client,
                                broadcaster_user_id=broadcaster_id_val
                            )
                            self.logger.info(f"KickEventManager initialized for broadcaster ID: {broadcaster_id_val}.")
                            
                            if self.kick_events_to_subscribe:
                                self.logger.info(f"Attempting to subscribe to {len(self.kick_events_to_subscribe)} Kick event(s). GHG")
                                try:
                                    success = await self.event_manager.resubscribe_to_configured_events(self.kick_events_to_subscribe)
                                    if success:
                                        self.logger.info("Successfully (re)subscribed to configured Kick events. GHG")
                                    else:
                                        self.logger.warning("Failed to (re)subscribe to some or all configured Kick events. GHG")
                                except Exception as e:
                                    self.logger.error(f"Error during event resubscription: {e}", exc_info=True)
                            else:
                                self.logger.info("No Kick events configured to subscribe to.")
                    else:
                        missing_deps = []
                        if not (self.streamer_info and self.streamer_info.get('id')): missing_deps.append("streamer_info.id")
                        if not self.auth_manager: missing_deps.append("auth_manager")
                        if not self.client: missing_deps.append("client")
                        self.logger.warning(f"Cannot initialize KickEventManager or subscribe to events. Missing dependencies: {', '.join(missing_deps)}.")
                else:
                    if not self.enable_new_webhook_system:
                        self.logger.info("EnableNewWebhookEventSystem feature flag is false. KickEventManager will not be initialized.")
                    elif not self.webhook_enabled:
                        self.logger.info("KickWebhookEnabled is false. KickEventManager will not be initialized.")

                # Initialize and start Webhook server (moved after EventManager setup that might use auth_manager)
                if self.webhook_enabled and self.enable_new_webhook_system:
                    # WebhookHandler might also need auth_manager or client depending on its internal logic for event processing
                    # Ensure it's initialized here if it has such dependencies, or ensure it gets them correctly.
                    # For now, assuming its current init in _start_webhook_server is sufficient if called at the right time.
                    await self._start_webhook_server() 
                elif self.webhook_enabled and not self.enable_new_webhook_system:
                    self.logger.info("KickWebhookEnabled is true, but EnableNewWebhookEventSystem is false. Webhook server will not start.")
                else:
                    self.logger.info("KickWebhookEnabled is false. Webhook server will not start.")

                # Start polling for chat messages (traditional method)
                if self.client and self.chatroom_id: # Ensure client and chatroom_id are ready for polling
                    await self._poll()
                else:
                    self.logger.error("Cannot start polling: KickClient not initialized or chatroom_id not found.")
        
        except KickBotException as e:
            self.logger.critical(f"A critical KickBotException occurred during run: {e}", exc_info=True)
            # Perform minimal cleanup if possible before exiting
            if self.http_session and not self.http_session.closed:
                await self.http_session.close()
                self.logger.info("aiohttp.ClientSession closed due to critical error.")
            # Depending on the severity, might want to call a more limited shutdown sequence
        except Exception as e:
            self.logger.critical(f"An unexpected critical error occurred during run: {e}", exc_info=True)
            if self.http_session and not self.http_session.closed:
                await self.http_session.close()
                self.logger.info("aiohttp.ClientSession closed due to critical error.")
        finally:
            # This finally block might not be reached if run is awaited and exception propagates up to main loop
            # Consider moving shutdown logic to the main poll() method's finally block or botoshi.py
            self.logger.info("KickBot run method finished or exited due to error.")
            # The self.shutdown() is called from poll() in botoshi.py's main structure

    async def shutdown(self):
        """Gracefully shutdown bot components."""
        self.logger.info("Initiating bot shutdown...")
        self._is_active = False

        # Unsubscribe from Kick events if manager exists
        if self.event_manager:
            self.logger.info("Unsubscribing from Kick events...")
            await self.event_manager.clear_all_my_broadcaster_subscriptions()
            self.event_manager = None

        if hasattr(self, 'ws_connection') and self.ws_connection and not self.ws_connection.closed:
            try:
                await self.ws_connection.close()
                self.logger.info("WebSocket connection closed.")
            except Exception as e:
                self.logger.error(f"Error closing WebSocket connection: {e}", exc_info=True)
        
        if hasattr(self, 'ws') and self.ws and hasattr(self.ws, 'stop') and callable(self.ws.stop):
            try:
                self.ws.stop()
                self.logger.info("MarkovChain TwitchWebsocket stopped.")
            except Exception as e:
                self.logger.error(f"Error stopping MarkovChain TwitchWebsocket: {e}", exc_info=True)

        await self._stop_webhook_server()

        # Close aiohttp.ClientSession
        if self.http_session:
            await self.http_session.close()
            self.logger.info("aiohttp.ClientSession closed.")
            self.http_session = None

        self.logger.info("Bot shutdown complete.")

    async def set_streamer(self, streamer_name: str) -> None:
        """
        Set the streamer for the bot to monitor.
        This method should be called BEFORE run().

        :param streamer_name: Username of the streamer for the bot to monitor
        """
        if not streamer_name or not isinstance(streamer_name, str):
            self.logger.error("Invalid streamer_name provided.")
            raise KickBotException("Streamer name must be a non-empty string.")

        if self.streamer_name is not None and self.streamer_name != streamer_name:
            # Handling streamer changes mid-run can be complex with event subscriptions, tokens, etc.
            # For now, disallow changing if already set to a different streamer to keep it simple.
            # If it's the same streamer, it's a no-op.
            self.logger.warning(f"Streamer is already set to {self.streamer_name}. Re-setting to {streamer_name}.")
            # If re-setting to the same streamer, no actual change needed in streamer_name/slug here.
            # Consider if any re-initialization logic is needed for this case.
        
        self.streamer_name = streamer_name
        self.streamer_slug = streamer_name.replace('_', '-') # Ensure slug is always updated
        self.logger.info(f"Streamer set to: {self.streamer_name} (slug: {self.streamer_slug})")

        # Defer client initialization and data fetching to the run() method
        # as they depend on http_session and correct call order.

        # The following calls are MOVED to the run() method after client initialization:
        # await self._initialize_client_if_needed() # MOVED
        # get_streamer_info(self) # MOVED
        # get_chatroom_settings(self) # MOVED
        # get_bot_settings(self) # MOVED

        # Moderator status check also depends on bot_settings, so it should also be in run() or called after it.
        # if self.is_mod: 
        #     self.moderator = Moderator(self)
        #     logger.info(f"Bot is confirmed as a moderator for {self.streamer_name}...")
        # else:
        #     logger.warning("Bot is not a moderator...")

    def add_message_handler(self, message: str, message_function: Callable) -> None:
        """
        Add a message to be handled, and the asynchronous function to handle that message.

        Message handler will call the function if the entire message content matches (case-insensitive)

        :param message: Message to be handled i.e: 'hello world'
        :param message_function: Async function to handle the message
        """
        if self.streamer_name is None:
            raise KickBotException("Must set streamer name to monitor first.")
        message = message.casefold()
        if self.handled_messages.get(message) is not None:
            raise KickBotException(f"Message: {message} already set in handled messages")
        self.handled_messages[message] = message_function

    def add_command_handler(self, command: str, command_function: Callable) -> None:
        """
        Add a command to be handled, and the asynchronous function to handle that command.

        Command handler will call the function if the first word matches (case-insensitive)

        :param command: Command to be handled i.e: '!time'
        :param command_function: Async function to handle the command
        """
        if self.streamer_name is None:
            raise KickBotException("Must set streamer name to monitor first.")
        command = command.casefold()
        if self.handled_commands.get(command) is not None:
            raise KickBotException(f"Command: {command} already set in handled commands")
        self.handled_commands[command] = command_function

    def add_timed_event(self, frequency_time: timedelta, timed_function: Callable):
        """
        Add an event function to be called with a frequency of frequency_time.
        A tuple containing (time, function) will be added to self.timed_events.
        Once the main event loop is running, a task is created for each tuple.

        :param frequency_time: Time interval between function calls.
        :param timed_function: Async function to be called.
        """
        if self.streamer_name is None:
            raise KickBotException("Must set streamer name to monitor first.")
        if frequency_time.total_seconds() <= 0:
            raise KickBotException("Frequency time must be greater than 0.")
        # Create and store the asyncio task
        task = asyncio.create_task(self._run_timed_event(frequency_time, timed_function))
        self.timed_events.append({
            "interval": frequency_time,
            "func": timed_function,
            "task": task
        })

    def remove_timed_event(self, frequency_time: timedelta, timed_function: Callable):
        """
        Remove an event function to be called with a frequency of frequency_time.
        A tuple containing (time, function) will be added to self.timed_events.
        Once the main event loop is running, a task is created for each tuple.

        :param frequency_time: Time interval between function calls.
        :param timed_function: Async function to be called.
        """
        if self.streamer_name is None:
            raise KickBotException("Must set streamer name to monitor first.")
        if frequency_time.total_seconds() <= 0:
            raise KickBotException("Frequency time must be greater than 0.")
        # Debug: log current timed_events and function IDs
        self.logger.debug(f"Current timed_events: {[ (d['interval'], d['func'].__name__, id(d['func'])) for d in self.timed_events ]}")
        self.logger.debug(f"Attempting to remove: ({frequency_time}, {timed_function.__name__}, id={id(timed_function)})")
        removed = 0
        for event in self.timed_events[:]:
            if event["interval"] == frequency_time and event["func"] == timed_function:
                event["task"].cancel()
                self.timed_events.remove(event)
                removed += 1
        if removed == 0:
            self.logger.warning(f"Tried to remove timed event ({timed_function.__name__}, {frequency_time}) but it was not in the list.")
        else:
            self.logger.info(f"Removed {removed} timed event(s) matching ({timed_function.__name__}, {frequency_time}).")

    async def send_text(self, message: str) -> None:
        """
        Used to send text in the chat.
        reply_text below is used to reply to a specific users message.

        :param message: Message to be sent in the chat
        """
        if not type(message) == str or message.strip() == "":
            raise KickBotException("Invalid message. Must be a non empty string.")
        logger.debug(f"Sending message: {message!r}")
        r = send_message_in_chat(self, message)
        if r.status_code != 200:
            raise KickBotException(f"An error occurred while sending message {message!r}")

    async def reply_text(self, original_message: KickMessage, reply_message: str) -> None:
        """
        Used inside a command/message handler function to reply to the original message / command.

        :param original_message: The original KickMessage argument in the handler function
        :param reply_message: string to reply to the original message
        """
        if not type(reply_message) == str or reply_message.strip() == "":
            raise KickBotException("Invalid reply message. Must be a non empty string.")
        
        if '@@Restream' in reply_message:
            self.logger.warning(f"Skipping reply to avoid breaking: {reply_message!r}")
            return

        # Check if sender exists and has a username, to avoid AttributeError
        if not hasattr(original_message, 'sender') or original_message.sender is None:
            logger.error(f"Cannot reply: Original message has no sender. Message: {original_message}")
            raise KickBotException(f"Cannot reply: Original message has no sender")
            
        if not hasattr(original_message.sender, 'user_id') or original_message.sender.user_id is None:
            logger.error(f"Cannot reply: Sender has no user_id. Sender: {original_message.sender}")
            raise KickBotException(f"Cannot reply: Sender has no user_id")
            
        if not hasattr(original_message.sender, 'username') or original_message.sender.username is None:
            logger.error(f"Cannot reply: Sender has no username. Sender: {original_message.sender}")
            raise KickBotException(f"Cannot reply: Sender has no username")

        logger.debug(f"Sending reply: {reply_message!r}")
        try:
            r = send_reply_in_chat(self, original_message, reply_message)
            if r.status_code != 200:
                raise KickBotException(f"An error occurred while sending reply {reply_message!r}")
        except Exception as e:
            raise KickBotException(f"An error occurred while sending reply {reply_message!r}") from e
        
    async def send_alert(self, img, audio, text, tts):
        if (settings['Alerts']['Enable']):
            try:
                async with aiohttp.ClientSession() as session:
                    width = '300px'
                    fontFamily = 'Arial'
                    fontSize = 30
                    color = 'gold'
                    borderColor = 'black'
                    borderWidth = 2
                    duration = 9000
                    parameters = f'gif={img}&audio={quote_plus(audio)}&text={text}&tts={tts}&width={width}&fontFamily={fontFamily}&fontSize={fontSize}&borderColor={borderColor}&borderWidth={borderWidth}&color={color}&duration={duration}'
                    url = settings['Alerts']['Host'] + '/trigger_alert?' + parameters + '&api_key=' + settings['Alerts']['ApiKey']
                    async with session.get(url) as response:
                        response_text = await response.text()
                        logging.info(response_text)
            except Exception as e:
                print(f'Error sending alert: {e}')
    
    def current_viewers(self) -> int:
        """
        Retrieve current viewer count for the stream

        :return: Viewer count as an integer
        """
        viewer_count = get_current_viewers(self)
        return viewer_count

    @staticmethod
    def set_log_level(log_level: str) -> None:
        """
        Set log level to your desired choice. By default, it is set to INFO.
        Debug will show alot more, including all inbound messages
        """
        log_level = log_level.upper()
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log_level in valid_levels:
            logger.setLevel(log_level)
        else:
            logger.warning(f"Invalid log level: {log_level}")

    async def _start_webhook_server(self):
        if not self.webhook_enabled:
            self.logger.info("Kick Webhook event system is disabled in settings.")
            return

        if not self.http_session:
            self.logger.error("HTTP session is not initialized. Cannot start webhook server.")
            return

        self.webhook_handler = KickWebhookHandler(
            kick_bot_instance=self,  # Pass the KickBot instance
            webhook_path=self.webhook_path,
            port=self.webhook_port,
            log_events=True, # Consider making this configurable
            signature_verification=False, # TODO: Implement and make configurable
            enable_new_webhook_system=self.enable_new_webhook_system,
            disable_legacy_gift_handling=self.disable_legacy_gift_handling,
            handle_follow_event_actions=self.handle_follow_event_actions, # Pass the new config
            handle_subscription_event_actions=self.handle_subscription_event_actions,
            handle_gifted_subscription_event_actions=self.handle_gifted_subscription_event_actions,
            handle_subscription_renewal_event_actions=self.handle_subscription_renewal_event_actions # Pass renewal config
        )

        app = web.Application()
        app.router.add_post(self.webhook_handler.webhook_path, self.webhook_handler.handle_webhook)
        
        self.webhook_runner = web.AppRunner(app)
        await self.webhook_runner.setup()
        self.webhook_site = web.TCPSite(self.webhook_runner, host='0.0.0.0', port=self.webhook_handler.port)
        try:
            await self.webhook_site.start()
            self.logger.info(f"Webhook server started on port {self.webhook_handler.port} at path {self.webhook_handler.webhook_path}")
        except Exception as e:
            self.logger.error(f"Failed to start webhook server: {e}", exc_info=True)
            self.webhook_site = None
            if self.webhook_runner:
                await self.webhook_runner.cleanup()
                self.webhook_runner = None

    async def _stop_webhook_server(self):
        if self.webhook_site:
            try:
                await self.webhook_site.stop()
                self.logger.info("Webhook server stopped.")
            except Exception as e:
                self.logger.error(f"Error stopping webhook site: {e}", exc_info=True)
            self.webhook_site = None
        
        if self.webhook_runner:
            try:
                await self.webhook_runner.cleanup()
                self.logger.info("Webhook runner cleaned up.")
            except Exception as e:
                self.logger.error(f"Error cleaning up webhook runner: {e}", exc_info=True)
            self.webhook_runner = None
        self.webhook_handler = None

    async def _poll(self) -> None:
        """
        Main loop for handling events and messages for the Kick WebSocket.
        This will now run as part of the main `run` method.
        """
        if self.streamer_name is None:
            raise KickBotException("Must set streamer name to monitor first.")

        # Timed event tasks are now managed in add_timed_event
        timed_event_tasks = [event["task"] for event in self.timed_events]

        async with websockets.connect(self._ws_uri) as websocket:
            self.ws_connection = websocket
            self.logger.info(f"Connected to {self.streamer_name}'s chat via WebSocket.")
            await self._join_chatroom(self.chatroom_id)
            self.logger.info(f"Attempted to join chatroom ID: {self.chatroom_id}") # Log chatroom join attempt

            while self._is_active:
                try:
                    # message is now potentially None if _recv failed, renamed to avoid confusion with outer scope message
                    received_message_data = await asyncio.wait_for(self._recv(), timeout=1.0)
                    
                    if received_message_data is None: # If _recv returned None (e.g. on error or clean close)
                        if not self._is_active: # If _is_active was set to False in _recv
                            self.logger.info("Exiting poll loop as _is_active is False (likely due to _recv error/close).")
                            break # Exit the while loop
                        continue # Otherwise, continue to next iteration (e.g. if only JSON decode failed but connection is alive)

                    # Process the successfully received and parsed message data
                    event_type = received_message_data.get("event")
                    data = received_message_data.get("data")

                    # Check for 'gerard' in message content for ChatMessageEvent
                    if event_type == "App\\Events\\ChatMessageEvent" and data:
                        try:
                            if isinstance(data, str):
                                data_obj = json.loads(data)
                            else:
                                data_obj = data
                                
                            message_content = str(data_obj.get('content', ''))
                            sender_username = str(data_obj.get('sender', {}).get('username', ''))
                            
                            if 'gerard' in message_content.casefold():
                                try:
                                    req = requests.post("http://192.168.0.30:7862/update_chat", 
                                                       json={'nickname': sender_username, 'context': message_content})
                                    if req.status_code == 200:
                                        self.logger.info("Context updated successfully.")
                                    else:
                                        self.logger.warning(f"Failed to update context: {req.status_code}")
                                except Exception as e:
                                    self.logger.error(f"Error updating context: {e}")
                        except Exception as e:
                            self.logger.error(f"Error processing 'gerard' detection: {e}")

                    # This data is now the Python dict from json.loads in _recv, or from direct assignment if not string initially.
                    # The initial string check and json.loads for 'data' at this level can be simplified or removed
                    # if _recv guarantees 'data' (when part of received_message_data) is already loaded from JSON string, 
                    # or is the original non-string data.
                    # For now, keeping the existing structure for data handling, but it might need review based on _recv's behavior.

                    if data and isinstance(data, str): # This check might be redundant if _recv always parses JSON strings
                        try:
                            data = json.loads(data) # This might attempt to double-parse if _recv already did.
                        except json.JSONDecodeError:
                            self.logger.warning(f"Could not decode JSON from 'data' field: {data}")
                            continue

                    if event_type == "App\\Events\\SocketMessageEvent":
                        self.logger.debug(f"Received SocketMessageEvent: {received_message_data}")
                        if data:
                            # For SocketMessageEvent, 'data' field can itself be a JSON string.
                            # This needs careful handling if the outer 'data' was already parsed.
                            # Assuming 'inner_data' is the actual payload here.
                            inner_data_payload = data # Start with data as is.
                            if isinstance(data, str):
                                try:
                                    inner_data_payload = json.loads(data)
                                except json.JSONDecodeError:
                                    self.logger.error(f"Failed to parse inner JSON data from SocketMessageEvent: {data}")
                                    continue # Skip this message
                            
                            if inner_data_payload:
                                if inner_data_payload.get('type') == 'message':
                                    await self._handle_chat_message(inner_data_payload)
                                elif inner_data_payload.get('type') == 'App\\Events\\FollowEvent':
                                    # Placeholder for handling FollowEvent if it comes via SocketMessageEvent
                                    self.logger.debug(f"FollowEvent received via SocketMessageEvent: {inner_data_payload}")
                                    pass
                                elif inner_data_payload.get('type') == 'gifted_subscriptions':
                                    # Placeholder for handling gifted_subscriptions if it comes via SocketMessageEvent
                                    self.logger.debug(f"GiftedSubscriptions event received via SocketMessageEvent: {inner_data_payload}")
                                    pass
                    elif event_type == "App\\Events\\ChatMessageSentEvent": 
                        self.logger.debug(f"Received ChatMessageSentEvent: {received_message_data}")
                        # Expect 'data' to be a dict here, as parsed by _recv or passed directly if not string.
                        if data and isinstance(data, dict):
                            await self._handle_chat_message(data)
                        else:
                            self.logger.warning(f"Received ChatMessageSentEvent with invalid or non-dict data: {data}")
                    elif event_type == "pusher:connection_established":
                        await self._handle_first_connect(received_message_data)
                    elif event_type == "App\\Events\\UserBannedEvent":
                        if data:
                            await self._handle_ban(data)
                    elif event_type == "pusher_internal:subscription_succeeded":
                        self.logger.debug(f"Full pusher_internal:subscription_succeeded event: {received_message_data}")
                        # Get channel from the top-level of the event, not from its 'data' field.
                        actual_subscribed_channel = received_message_data.get('channel')
                        self.logger.info(f"Successfully subscribed to Pusher channel: {actual_subscribed_channel}")
                    else:
                        self.logger.info(f"Received unhandled WebSocket event type: {event_type}")
                        self.logger.debug(f"Full unhandled message: {received_message_data}")

                except asyncio.TimeoutError:
                    self.logger.debug("WebSocket receive timed out. No message in 1s.") # More visible log
                    continue
                except websockets.exceptions.ConnectionClosedError as e:
                    self.logger.error(f"WebSocket connection closed unexpectedly: {e}. Attempting to reconnect...")
                    if self._is_active:
                        await asyncio.sleep(5)
                        break
                    else:
                        self.logger.info("WebSocket connection closed during shutdown.")
                        break
                except Exception as e:
                    self.logger.error(f"Error in WebSocket polling loop: {e}", exc_info=True)
                    if self._is_active:
                        await asyncio.sleep(5)
                    else:
                        break

        for task in timed_event_tasks:
            task.cancel()
        await asyncio.gather(*timed_event_tasks, return_exceptions=True)
        self.logger.info("Timed event tasks cancelled.")

    async def _join_chatroom(self, chatroom_id):
        """
        Join the chatroom via websocket.
        """
        join_command = {
            "event": "pusher:subscribe",
            "data": {
                "channel": f"chatrooms.{chatroom_id}"
            }
        }
        await self.ws_connection.send(json.dumps(join_command))
        
    async def _run_timed_event(self, frequency_time: timedelta, timed_function: Callable):
        """
        Wrapper to run timed event. Loop will call the timed_function at specified frequency_time
        """
        while self._is_active:
            try:
                await asyncio.sleep(frequency_time.total_seconds())
                if self._is_active:
                    await timed_function(self)
            except asyncio.CancelledError:
                self.logger.info(f"Timed event {timed_function.__name__} cancelled.")
                break
            except Exception as e:
                self.logger.error(f"Error in timed event {timed_function.__name__}: {e}", exc_info=True)
                await asyncio.sleep(frequency_time.total_seconds())

    async def _send(self, command: dict) -> None:
        """
        Json dumps command and sends over socket.

        :param command: dictionary to convert to json command
        """
        await self.sock.send(json.dumps(command))

    async def _recv(self) -> Optional[dict]:
        """
        Receives raw data, logs it, then tries to parse as JSON.
        Returns None if connection closes, JSON parsing fails, or other critical error.
        """
        raw_data = None # Initialize raw_data to ensure it's available for logging in case of early errors
        try:
            raw_data = await self.ws_connection.recv()
            self.logger.debug(f"Raw WebSocket data received: {raw_data}")
            return json.loads(raw_data)
        except websockets.exceptions.ConnectionClosedOK:
            self.logger.info("WebSocket connection closed normally by remote.")
            self._is_active = False # Stop polling if connection closed
            return None
        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.error(f"WebSocket connection closed with error: {e}")
            self._is_active = False # Stop polling
            return None
        except json.JSONDecodeError as e:
            # Ensure raw_data is a string or can be represented as a string for the log message
            raw_data_str = raw_data if isinstance(raw_data, str) else str(raw_data)
            self.logger.error(f"Failed to decode JSON from WebSocket: {raw_data_str}. Error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in _recv: {e}", exc_info=True)
            self._is_active = False # Stop polling on unexpected errors
            return None

    async def _handle_first_connect(self, message):
        """
        Handle the 'pusher:connection_established' event from the websocket.
        Currently a no-op.
        """
        self.logger.info("WebSocket connection established (pusher:connection_established event).")
        # Optionally, parse the message or update state if needed.
        pass

    async def _handle_chat_message(self, inbound_message: dict) -> None:
        """
        Handles incoming messages from both websocket and webhook, 
        checks if the message.content is in dict of handled commands / messages.

        :param inbound_message: Raw inbound message from socket or webhook
        """
        try:
            message: KickMessage = message_from_data(inbound_message)
            
            # Skip if this is a message from the bot itself
            if message.sender.username == self.client.bot_name:
                return
                
            # Check for message ID deduplication
            message_id = message.id
            if message_id:
                if message_id in self.processed_message_ids:
                    self.logger.debug(f"Skipping duplicate message with ID: {message_id}")
                    return
                
                # Add to processed IDs
                self.processed_message_ids.add(message_id)
                
                # Trim cache if it gets too large
                if len(self.processed_message_ids) > self.max_cache_size:
                    # Remove oldest entries (convert to list, slice, convert back to set)
                    self.processed_message_ids = set(list(self.processed_message_ids)[self.max_cache_size // 2:])

            content = message.content.casefold()
            command = message.args[0].casefold() if message.args and len(message.args) > 0 else ""
            self.logger.debug(f"New Message from {message.sender.username} | MESSAGE: {content!r}")
            
            # Process with Markov Chain if enabled
            if hasattr(self, 'db') and self._enabled:
                try:
                    MarkovChain.message_handler(self, content)
                except Exception as e:
                    self.logger.error(f"Error processing message with MarkovChain: {e}", exc_info=True)
                    
            # Check if the message is a gifted subscription message and sent by 'Kicklet'
            if (message.sender.username == "Kicklet" and 
                "thank you" in content and 
                "for the gifted" in content and 
                "subscriptions" in content):
                try:
                    # Extract the gifter username and the number of subscriptions
                    parts = content.split()
                    gifter = parts[2].rstrip(',')  # The gifter's username is the third word, after "Thank you,"
                    amount_index = parts.index("gifted") + 1  # The amount is the word after "gifted"
                    amount = int(parts[amount_index])  # Convert the amount to an integer
                    
                    # Handle the gifted subscriptions
                    if hasattr(self, '_handle_gifted_subscriptions'):
                        await self._handle_gifted_subscriptions(gifter, amount)
                    else:
                        self.logger.warning("_handle_gifted_subscriptions method not available")
                except (IndexError, ValueError) as e:
                    self.logger.error(f"Error parsing gifted subscription message: {e}")

            # Check for direct message matches
            if content in self.handled_messages:
                message_func = self.handled_messages[content]
                await message_func(self, message)
                self.logger.info(f"Handled Message: {content!r} from user {message.sender.username} ({message.sender.user_id})")
                return

            # Check for commands
            if command and command in self.handled_commands:
                command_func = self.handled_commands[command]
                await command_func(self, message)
                self.logger.info(f"Handled Command: {command!r} from user {message.sender.username} ({message.sender.user_id})")
                return

            # Check for partial message matches
            for msg in self.handled_messages:
                # If message text contains a registered message pattern, call its handler
                if msg in content:
                    message_func = self.handled_messages[msg]
                    await message_func(self, message)
                    self.logger.info(f"Handled Partial Message Match: {content!r} (matched: {msg!r}) from user {message.sender.username} ({message.sender.user_id})")
                    return

            self.logger.debug(f"No handler found for message: {content}")

        except Exception as e:
            self.logger.error(f"Error in _handle_chat_message: {e}", exc_info=True)

    async def _handle_gifted_subscriptions(self, gifter: str, amount: int) -> None:
        """
        Handles incoming gifted subscriptions events, adds blokitos to the gifter's account and logs the event.

        :param gifter: Username of the gifter
        :param amount: Number of subscriptions gifted
        """
        if gifter == "Anonymous":
            self.logger.info(f"Anonymous gifter sent {amount} subscriptions - no points awarded")
            return
            
        try:
            if 'GiftBlokitos' in settings and settings['GiftBlokitos'] != 0:
                blokitos = amount * settings['GiftBlokitos']
                message = f'!subgift_add {gifter} {blokitos}'
                r = send_message_in_chat(self, message)
                if r.status_code != 200:
                    self.logger.error(f"Error sending message for gift subs: {r.status_code} - {r.text}")
                else:
                    self.logger.info(f"Added {blokitos} to user {gifter} for {amount} sub_gifts")
        except Exception as e:
            self.logger.error(f"Error handling gifted subscriptions: {e}", exc_info=True)

    def generate(self, msg: list = None) -> tuple:
        """Generate a Markov chain message.

        Args:
            msg (list, optional): Starting word(s) for generation. Defaults to None.

        Returns:
            tuple: (sentence, success_bool)
        """
        try:
            return MarkovChain.generate(self, msg)
        except Exception as e:
            self.logger.error(f"Error in generate: {e}", exc_info=True)
            return "Error generating message", False

    async def _handle_ban(self, inbound_message: dict) -> None:
        """
        Handles incoming ban events, from the banned user's account and logs the event.
        
        :param inbound_message: Raw inbound message from socket
        """
        try:
            if isinstance(inbound_message, str):
                data = json.loads(inbound_message)
            else:
                data = inbound_message
            
            expired = data.get('expires_at')
            user = data.get('user', {})
            banned_by = data.get('banned_by', {})
            
            user_username = user.get('username', 'unknown')
            ban_by_username = banned_by.get('username', 'unknown')
            
            if expired:
                # Temporary ban
                message = f'#tabanido @{user_username}'
                try:
                    r = send_message_in_chat(self, message)
                    if r.status_code != 200:
                        self.logger.error(f"An error occurred while sending ban message {message!r}")
                    
                    await self.send_alert(
                        'https://media3.giphy.com/media/up8eu7XYylMrPmLwY4/giphy.gif',
                        'https://www.myinstants.com/media/sounds/cartoon-hammer.mp3', 
                        message.replace('#', ''), 
                        message.replace('#', '')
                    )
                except Exception as e:
                    self.logger.error(f"Error in ban message or alert: {e}")
            else:
                # Permanent ban
                message = f'#AVADAA_KEDAVRAA @{user_username}'
                try:
                    r = send_message_in_chat(self, message)
                except Exception as e:
                    self.logger.error(f"Error in permanent ban message: {e}")
            
            self.logger.info(f"Ban user {user_username} by {ban_by_username}")
        except Exception as e:
            self.logger.error(f"Error handling ban event: {e}", exc_info=True)
