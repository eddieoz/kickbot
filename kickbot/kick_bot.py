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
from .kick_auth_manager import KickAuthManager
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
        self.timed_events: list[tuple[timedelta, Callable]] = []
        self._is_active = True

        # Webhook Handler
        self.webhook_handler: Optional[KickWebhookHandler] = None
        self.webhook_runner: Optional[web.AppRunner] = None
        self.webhook_site: Optional[web.TCPSite] = None
        self.webhook_enabled: bool = False
        self.webhook_path: str = "/kick/events"
        self.webhook_port: int = 8080

        # Event Subscription Config
        self.kick_events_to_subscribe: List[Dict[str, Any]] = []

        # Markov Chain
        self.prev_message_t = 0
        self._enabled = True
        self.link_regex = re.compile("\w+\.[a-z]{2,}")
        self.mod_list = []
        self.set_blacklist()

        # Fill previously initialised variables with data from the settings.txt file
        Settings(self)
        self.db = Database(self.chan)

        # Set up daemon Timer to send help messages
        if self.help_message_timer > 0:
            if self.help_message_timer < 300:
                raise ValueError("Value for \"HelpMessageTimer\" in must be at least 300 seconds, or a negative number for no help messages.")
            t = LoopingTimer(self.help_message_timer, self.send_help_message)
            t.start()
        
        # Set up daemon Timer to send automatic generation messages
        if self.automatic_generation_timer > 0:
            if self.automatic_generation_timer < 30:
                raise ValueError("Value for \"AutomaticGenerationMessage\" in must be at least 30 seconds, or a negative number for no automatic generations.")
            t = LoopingTimer(self.automatic_generation_timer, self.send_automatic_generation_message)
            t.start()

        self.ws = TwitchWebsocket(host=self.host, 
                                  port=self.port,
                                  chan=self.chan,
                                  nick=self.nick,
                                  auth=self.auth,
                                  callback=MarkovChain.message_handler,
                                  capability=["commands", "tags"],
                                  live=True)

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
        self.webhook_port = settings.get("KickWebhookPort", 8080)

        # Load Event Subscription settings
        raw_events = settings.get("KickEventsToSubscribe", [])
        # Basic validation for event structure
        self.kick_events_to_subscribe = [
            event for event in raw_events 
            if isinstance(event, dict) and "name" in event and "version" in event
        ]
        if len(self.kick_events_to_subscribe) != len(raw_events):
            self.logger.warning("Some configured Kick events to subscribe were invalid and have been filtered out.")

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

    async def run(self):
        """Main async method to run bot components."""
        self.http_session = aiohttp.ClientSession()
        self.logger.info("aiohttp.ClientSession created.")

        # Initialize KickClient with the session
        # Assuming KickBot's username and password are for KickClient
        kick_email = settings.get("KickEmail") # Get from global settings loaded at module level
        kick_pass = settings.get("KickPass")
        if not kick_email or not kick_pass:
            self.logger.error("KickEmail or KickPass not found in settings.json. Cannot initialize KickClient.")
            await self.shutdown() # Or raise an exception
            return
        self.client = KickClient(kick_email, kick_pass, session=self.http_session)

        # Initialize KickAuthManager
        # KickAuthManager loads its core OAuth parameters (client_id, client_secret, redirect_uri, scopes)
        # directly from environment variables (e.g., populated by a .env file).
        # The constructor can take overrides if needed, or a custom token_file path.
        try:
            # The `KickAuthManager` provided does not take `client` in its actual __init__ signature shown.
            # It manages its own aiohttp.ClientSession for its specific token requests.
            # Allow overriding default token file via settings.json if desired.
            token_file_override = settings.get("KICK_TOKEN_FILE_PATH", None) 
            
            # Scopes and redirect_uri can also be overridden from settings if desired,
            # otherwise KAM uses .env values. For this example, we assume .env is primary for them.
            # If you want settings.json to override .env for redirect_uri or scopes:
            # kam_redirect_uri = settings.get("KICK_REDIRECT_URI_OVERRIDE", None)
            # kam_scopes_list = settings.get("KICK_SCOPES_OVERRIDE", None)
            # kam_scopes_str = " ".join(kam_scopes_list) if kam_scopes_list else None
            # self.auth_manager = KickAuthManager(
            #    redirect_uri=kam_redirect_uri,
            #    scopes=kam_scopes_str,
            #    token_file=token_file_override
            # )
            
            self.auth_manager = KickAuthManager(token_file=token_file_override)
            self.logger.info("KickAuthManager initialized (credentials and core config expected from .env).")

        except ValueError as e: # KickAuthManager raises ValueError if KICK_CLIENT_ID or KICK_REDIRECT_URI is missing from .env and not passed
            self.logger.error(f"Failed to initialize KickAuthManager: {e}. Ensure KICK_CLIENT_ID and KICK_REDIRECT_URI are set in .env.")
            await self.shutdown()
            return
        except Exception as e: # Catch any other unexpected init errors from KickAuthManager
            self.logger.error(f"Unexpected error initializing KickAuthManager: {e}", exc_info=True)
            await self.shutdown()
            return
        # self.logger.info("KickAuthManager initialized.") # Redundant due to log message in try block

        # Perform initial token acquisition or validation
        try:
            initial_token = await self.auth_manager.get_valid_token()
            if not initial_token:
                self.logger.error("Failed to obtain initial valid token. Event subscriptions will likely fail. Manual OAuth grant may be required.")
                # Depending on bot's design, either stop or continue with warnings.
                # For User Story 3, we need this token.
            else:
                self.logger.info("Successfully obtained/validated initial access token.")
        except Exception as e:
            self.logger.error(f"Error during initial token validation: {e}. Event subscriptions may fail.", exc_info=True)
            # Handle critical failure, perhaps shutdown if token is essential for all operations

        # Start Webhook Server (needs to be up before subscribing to events)
        await self._start_webhook_server()

        # Initialize KickEventManager if streamer_info is available
        # set_streamer is usually called before poll/run. If not, this needs adjustment.
        # For now, let's assume set_streamer has been called and streamer_info is populated.
        if self.streamer_info and self.streamer_info.get('id') and self.auth_manager and self.client:
            self.event_manager = KickEventManager(
                auth_manager=self.auth_manager,
                client=self.client,
                broadcaster_user_id=self.streamer_info['id']
            )
            self.logger.info(f"KickEventManager initialized for broadcaster ID: {self.streamer_info['id']}.")
            
            # Subscribe to configured events
            if self.webhook_enabled and self.kick_events_to_subscribe:
                self.logger.info(f"Attempting to subscribe to configured Kick events: {self.kick_events_to_subscribe}")
                await self.event_manager.resubscribe_to_configured_events(self.kick_events_to_subscribe)
            elif not self.webhook_enabled:
                self.logger.info("Webhook server is not enabled, skipping Kick event subscriptions.")
            else:
                self.logger.info("No Kick events configured to subscribe to.")
        else:
            self.logger.warning("Streamer info not set or AuthManager/Client not ready. Cannot initialize KickEventManager or subscribe to events yet.")
            # This implies set_streamer() must be called before run() can fully set up event subscriptions.

        await self._poll()

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
        
        if hasattr(self, 'ws') and isinstance(self.ws, TwitchWebsocket):
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

    def set_streamer(self, streamer_name: str) -> None:
        """
        Set the streamer for the bot to monitor.

        :param streamer_name: Username of the streamer for the bot to monitor
        """
        if self.streamer_name is not None:
            # If changing streamer, existing event subscriptions for old streamer should be cleared.
            # This simple implementation doesn't handle streamer changes gracefully for event manager yet.
            # For now, it assumes set_streamer is called once.
            raise KickBotException("Streamer already set. Changing streamer during runtime is not fully supported for event subscriptions yet.")
        
        self.streamer_name = streamer_name
        self.streamer_slug = streamer_name.replace('_', '-')
        
        # Ensure client is available for these helper calls if they use it
        if not self.client:
            # This is a problem if set_streamer is called before run() initializes self.client
            # This indicates a potential design issue in initialization order.
            # For now, log an error. A robust solution would ensure client is ready.
            self.logger.error("KickClient not initialized when set_streamer was called. API calls in set_streamer might fail.")
            # Ideally, `get_streamer_info` etc. should take the client as an argument or use one from `self`
            # that is guaranteed to be initialized.
        
        get_streamer_info(self) # This populates self.streamer_info, including id
        get_chatroom_settings(self)
        get_bot_settings(self)

        # Initialize EventManager here if all dependencies are met
        # This makes more sense than in run(), as broadcaster_id is now known.
        if self.streamer_info and self.streamer_info.get('id') and self.auth_manager and self.client:
            if self.event_manager is None: # Initialize only once
                self.event_manager = KickEventManager(
                    auth_manager=self.auth_manager,
                    client=self.client,
                    broadcaster_user_id=self.streamer_info['id']
                )
                self.logger.info(f"KickEventManager initialized within set_streamer for broadcaster ID: {self.streamer_info['id']}.")
                # Subscription logic will be handled in run() after token validation and webhook server start.
            else:
                 # If event_manager exists, and streamer_id changes, it needs re-initialization or update.
                 # Current check for self.streamer_name prevents this path for now.
                 pass 
        elif not (self.auth_manager and self.client):
            self.logger.warning("AuthManager or KickClient not ready during set_streamer. EventManager not initialized.")

        if self.is_mod:
            self.moderator = Moderator(self)
            logger.info(f"Bot is confirmed as a moderator for {self.streamer_name}...")
        else:
            logger.warning("Bot is not a moderator in the stream. To access moderator functions, make the bot a mod."
                           "(You can still send messages and reply's, bot moderator status is recommended)")

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
        self.timed_events.append((frequency_time, timed_function))

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
        self.timed_events.remove((frequency_time, timed_function))

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
            self.logger.info("Webhook server is disabled in settings.")
            return

        if self.webhook_handler is None:
            self.webhook_handler = KickWebhookHandler(
                webhook_path=self.webhook_path,
                port=self.webhook_port,
                log_events=True
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

        timed_event_tasks = []
        for time, func in self.timed_events:
            timed_event_tasks.append(asyncio.create_task(self._run_timed_event(time, func)))
        
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
        return json.loads(await self.sock.recv())
