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

class KickBot:
    """
    Main class for interacting with the Bot API.
    """
    def __init__(self, username: str, password: str) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        # Avoid adding handler if already present (e.g. during tests with multiple instances or re-init)
        if not any(isinstance(h, logging.StreamHandler) for h in self.logger.handlers):
            self.logger.addHandler(handler)

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
            logger.info("Help message sent.")
            try:
                self.ws.send_message("Learn how this bot generates sentences here: https://github.com/CubieDev/TwitchMarkovChain#how-it-works")
            except socket.OSError as error:
                logger.warning(f"[OSError: {error}] upon sending help message. Ignoring.")
    
    def send_automatic_generation_message(self) -> None:
        """Send an automatic generation message to the connected chat.
        
        As long as the bot wasn't disabled, just like if someone typed "!g" in chat.
        """
        if self._enabled:
            sentence, success = self.generate()
            if success:
                logger.info(sentence)
                # Try to send a message. Just log a warning on fail
                try:
                    self.ws.send_message(sentence)
                except socket.OSError as error:
                    logger.warning(f"[OSError: {error}] upon sending automatic generation message. Ignoring.")
            else:
                logger.info("Attempted to output automatic generation message, but there is not enough learned information yet.")

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

            while self._is_active:
                try:
                    message = await asyncio.wait_for(self._recv(), timeout=1.0)
                    if message:
                        event_type = message.get("event")
                        data = message.get("data")

                        if data and isinstance(data, str):
                            try:
                                data = json.loads(data)
                            except json.JSONDecodeError:
                                self.logger.warning(f"Could not decode JSON data: {data}")
                                continue

                        if event_type == "App\\Events\\SocketMessageEvent":
                            self.logger.debug(f"Received SocketMessageEvent: {message}")
                            if data:
                                if isinstance(data, str):
                                    try:
                                        inner_data = json.loads(data)
                                    except json.JSONDecodeError:
                                        self.logger.error(f"Failed to parse inner JSON data from SocketMessageEvent: {data}")
                                else:
                                    inner_data = data

                                if inner_data:
                                    if inner_data.get('type') == 'message':
                                        await self._handle_chat_message(inner_data)
                                    elif inner_data.get('type') == 'App\\Events\\FollowEvent':
                                        pass
                                    elif inner_data.get('type') == 'gifted_subscriptions':
                                        pass
                        elif event_type == "pusher:connection_established":
                            await self._handle_first_connect(message)
                        elif event_type == "App\\Events\\UserBannedEvent":
                            if data:
                                await self._handle_ban(data)
                        else:
                            self.logger.info(f"Received unhandled WebSocket event type: {event_type}")
                            self.logger.debug(f"Full unhandled message: {message}")

                except asyncio.TimeoutError:
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

    async def _recv(self) -> dict:
        """
        Json loads command received from socket.

        :return: dict / json inbound socket command
        """
        return json.loads(await self.ws_connection.recv())

    async def _handle_first_connect(self, message):
        """
        Handle the 'pusher:connection_established' event from the websocket.
        Currently a no-op.
        """
        self.logger.info("WebSocket connection established (pusher:connection_established event).")
        # Optionally, parse the message or update state if needed.
        pass
