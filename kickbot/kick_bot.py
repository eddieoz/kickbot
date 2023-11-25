import asyncio
import json
import logging
from urllib.parse import quote_plus, urlencode
import aiohttp
import requests
import websockets

from datetime import timedelta
from typing import Callable, Optional

from .constants import KickBotException
from .kick_client import KickClient
from .kick_message import KickMessage
from .kick_moderator import Moderator
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
from typing import List, Tuple

logger = logging.getLogger(__name__)

with open('settings.json') as f:
    settings = json.load(f)

class KickBot:
    """
    Main class for interacting with the Bot API.
    """
    def __init__(self, username: str, password: str) -> None:
        self.client: KickClient = KickClient(username, password)
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

        # Markov Chain
        self.prev_message_t = 0
        self._enabled = True
        # This regex should detect similar phrases as links as Twitch does
        self.link_regex = re.compile("\w+\.[a-z]{2,}")
        # List of moderators used in blacklist modification, includes broadcaster
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
        try:
            asyncio.run(self._poll())
        except KeyboardInterrupt:
            logger.info("Bot stopped.")
            return

    def set_streamer(self, streamer_name: str) -> None:
        """
        Set the streamer for the bot to monitor.

        :param streamer_name: Username of the streamer for the bot to monitor
        """
        if self.streamer_name is not None:
            raise KickBotException("Streamer already set. Only able to set one streamer at a time.")
        self.streamer_name = streamer_name
        self.streamer_slug = streamer_name.replace('_', '-')
        get_streamer_info(self)
        get_chatroom_settings(self)
        get_bot_settings(self)
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
        logger.debug(f"Sending reply: {reply_message!r}")
        r = send_reply_in_chat(self, original_message, reply_message)
        if r.status_code != 200:
            raise KickBotException(f"An error occurred while sending reply {reply_message!r}")
        
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
                    # alert = requests.get(url)
                    # logging.info(alert.text)
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

    ########################################################################################
    #    INTERNAL FUNCTIONS
    ########################################################################################

    async def _poll(self) -> None:
        """
        Main internal function to poll the streamers chat and respond to messages/commands.
        Create a task for each timed event in self.timed_events.
        """
        for frequency, func in self.timed_events:
            try: 
                asyncio.create_task(self._run_timed_event(frequency, func))
            except:
                logger.warning(f"Error creating task for timed event {func.__name__}")

        async with websockets.connect(self._ws_uri) as self.sock:
            connection_response = await self._recv()
            await self._handle_first_connect(connection_response)
            await self._join_chatroom(self.chatroom_id)
            while True:
                try:
                    response = await self._recv()
                    
                    if response.get('event') == 'App\\Events\\UserBannedEvent':
                        await self._handle_ban(response)
                    if response.get('event') == 'App\\Events\\ChatMessageEvent':
                        await self._handle_chat_message(response)
                    if response.get('event') == 'App\\Events\\GiftedSubscriptionsEvent':
                        # {'event': 'App\\Events\\GiftedSubscriptionsEvent', 
                        # 'data': '{"chatroom_id":1164726,"gifted_usernames":["Khalek"],"gifter_username":"eddieoz"}', 'channel': 'chatrooms.1164726.v2'}
                        await self._handle_gifted_subscriptions(response)
                except asyncio.exceptions.CancelledError:
                    break
        logger.info(f"Disconnected from websocket {self._socket_id}")
        self._is_active = False

    async def _handle_gifted_subscriptions(self, inbound_message: dict) -> None:
        """
        Handles incoming gifted subscriptions events, adds blokitos to the gifter's account and logs the event.

        :param inbound_message: Raw inbound message from socket
        """
        gifter = json.loads(inbound_message.get('data')).get('gifter_username')
        gifted_usernames = json.loads(inbound_message.get('data')).get('gifted_usernames')
        chatroom_id = json.loads(inbound_message.get('data')).get('chatroom_id')

        if settings['GiftBlokitos'] != 0:
            blokitos = len(gifted_usernames) * settings['GiftBlokitos']
            message = f'!points add @{gifter} {blokitos}'
            r = send_message_in_chat(self, message)
            if r.status_code != 200:
                raise KickBotException(f"An error occurred while sending message {message!r}")
            logger.info(f"Added {blokitos} to user {gifter} for sub_gifts ({gifted_usernames})")

    async def _handle_ban(self, inbound_message: dict) -> None:
        """
        Handles incoming ban events, from the banned user's account and logs the event.

        :param inbound_message: Raw inbound message from socket
        # 'App\\Events\\UserBannedEvent'
        # '{"id":"da55e408-c421-40a3-a274-07b031ebe715","user":{"id":20886158,"username":"RicardoBotoshi","slug":"ricardobotoshi"},"banned_by":{"id":0,"username":"mzinha","slug":"mzinha"},"expires_at":"2023-10-10T07:56:22+00:00"}'
        # '{"id":"8fa06ed7-f2cf-4210-8ddb-d497ee661e38","user":{"id":20886158,"username":"RicardoBotoshi","slug":"ricardobotoshi"},"banned_by":{"id":0,"username":"mzinha","slug":"mzinha"}}'
        # 'App\\Events\\UserUnbannedEvent'
        # '{"id":"7a38feef-b052-4870-8f1a-fd55bbffe38e","user":{"id":20886158,"username":"RicardoBotoshi","slug":"ricardobotoshi"},"unbanned_by":{"id":6914823,"username":"mzinha","slug":"mzinha"}}'
        # '{"id":"9f863fae-a2cc-4124-9ee1-ac56e3ae1569","user":{"id":20886158,"username":"RicardoBotoshi","slug":"ricardobotoshi"},"unbanned_by":{"id":6914823,"username":"mzinha","slug":"mzinha"}}'await self._handle_ban(response)
        """
        expired = json.loads(inbound_message.get('data')).get('expires_at')
        if expired != None:
            user = json.loads(inbound_message.get('data')).get('user').get('username')
            ban_by = json.loads(inbound_message.get('data')).get('banned_by').get('username')
            chatroom_id = json.loads(inbound_message.get('data')).get('chatroom_id')
            # message = f'!points remove @{user} {settings["BanBlokitos"]}'
            message = f'#tabanido @{user}'
            r = send_message_in_chat(self, message)
            if r.status_code != 200:
                raise KickBotException(f"An error occurred while sending message {message!r}")
            await self.send_alert('https://media3.giphy.com/media/up8eu7XYylMrPmLwY4/giphy.gif','https://www.myinstants.com/media/sounds/cartoon-hammer.mp3', message.replace('#', ''), message.replace('#', ''))
            
            logger.info(f"Ban user {user} by {ban_by}")
        else:
            user = json.loads(inbound_message.get('data')).get('user').get('username')
            ban_by = json.loads(inbound_message.get('data')).get('banned_by').get('username')
            chatroom_id = json.loads(inbound_message.get('data')).get('chatroom_id')
            # message = f'!points remove @{user} {settings["BanBlokitos"]}'
            message = f'#AVADAA_KEDAVRAA  @{user}'
            r = send_message_in_chat(self, message)
            if r.status_code != 200:
                raise KickBotException(f"An error occurred while sending message {message!r}")
            await self.send_alert('https://media4.giphy.com/media/54Q8WBE4zDN5e/giphy.gif','https://www.myinstants.com/media/sounds/avadaa-kedavraa.mp3', message.replace('#', ''), message.replace('#', ''))
            
            logger.info(f"Ban user {user} by {ban_by}")

    async def _handle_chat_message(self, inbound_message: dict) -> None:
        """
        Handles incoming messages, checks if the message.content is in dict of handled commands / messages

        :param inbound_message: Raw inbound message from socket
        """
        message: KickMessage = message_from_data(inbound_message)
        if message.sender.username == self.client.bot_name:
            return

        content = message.content.casefold()
        command = message.args[0].casefold()
        logger.debug(f"New Message from {message.sender.username} | MESSAGE: {content!r}")

        # create a variable in the format var['message'] = content
        
        MarkovChain.message_handler(self, content)

        if content in self.handled_messages:
            message_func = self.handled_messages[content]
            await message_func(self, message)
            logger.info(f"Handled Message: {content!r} from user {message.sender.username} ({message.sender.user_id})")

        elif command in self.handled_commands:
            command_func = self.handled_commands[command]
            await command_func(self, message)
            logger.info(f"Handled Command: {command!r} from user {message.sender.username} ({message.sender.user_id})")
        
        else:
            # verify if self.handled_messages is contained in the content variable
            for msg in self.handled_messages:
                # if it is, then call the function
                if msg in content:
                    message_func = self.handled_messages[msg]
                    await message_func(self, message)
                    logger.info(f"Handled Message: {content!r} from user {message.sender.username} ({message.sender.user_id})")

    async def _join_chatroom(self, chatroom_id: int) -> None:
        """
         Join the chatroom websocket.

         :param chatroom_id: ID of the chatroom, mainly the streamer to monitor
         """
        join_command = {'event': 'pusher:subscribe', 'data': {'auth': '', 'channel': f"chatrooms.{chatroom_id}.v2"}}
        await self._send(join_command)
        join_response = await self._recv()
        if join_response.get('event') != "pusher_internal:subscription_succeeded":
            raise KickBotException(f"Error when attempting to join chatroom {chatroom_id}. Response: {join_response}")
        logger.info(f"Bot Joined chatroom {chatroom_id} ({self.streamer_name})")

    async def _handle_first_connect(self, connection_response: dict) -> None:
        """
        Handle the initial response received from the websocket.

        :param connection_response: Initial response when connecting to the socket
        """
        if connection_response.get('event') != 'pusher:connection_established':
            raise Exception('Error establishing connection to socket.')
        self._socket_id = json.loads(connection_response.get('data')).get('socket_id')
        logger.info(f"Successfully Connected to socket...")

    async def _run_timed_event(self, frequency_time: timedelta, timed_function: Callable):
        """
        Launched in a thread when a user calls bot.add_timed_event, runs until bot is inactive

        :param frequency_time: Frequency to call the timed function
        :param timed_function: timed function to be called
        """
        try:
            while self._is_active:
                await asyncio.sleep(frequency_time.total_seconds())
                await timed_function(self)
                logger.info(f"Timed Event Called")
        except:
            logger.warning(f"Error running timed event {timed_function.__name__}")

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
