# kickbot

Unofficial python package to create bots and interact with the kick.com api

---

## Table of Contents

- [About](#about)
- [Important Setup & Configuration](#important-setup--configuration)
  - [Environment Variables (`.env` file)](#environment-variables-env-file)
  - [Initial OAuth Authorization (One-Time Step)](#initial-oauth-authorization-one-time-step)
  - [Dependencies](#dependencies)
- [Installation](#installation)
- [Features](#features)
- [Example](#example)
- [Command / Message handling](#command-and-message-handling)
- [Sending Messages / Reply's](#sending-messages-and-replys)
- [Streamer / Chat information](#streamer-and-chat-information)
- [Chat Moderation](#chat-moderation)
- [Timed event functions](#timed-events)
- [Kick API OAuth Integration](#kick-api-oauth-integration)
- [Webhooks & Signature Verification](#webhooks-and-signature-verification)
- [Testing](#testing)

---

### Important Update:
> Kick now seems to require Two-factor authentication on all log in's. The bot will now prompt you in the console 
> to enter the verification code kick sends to you via email or text, so the bot can log in using the provided code. 
> This primarily applies to the traditional username/password login for basic chat interaction. The new OAuth method for API events has its own browser-based authorization flow.

## About

This package allows you to create bots (user bots) to monitor a stream. 
It supports traditional chat interaction via a user bot account and is being updated to use Kick's official API with OAuth 2.0 for more advanced features like event subscriptions (gifts, new subs, etc.).

You will need to set up a 'user bot' account (a normal user account to act as a bot) for the bot to be able to log in and handle commands / messages using the traditional method.
For the new API features, you'll need to register an application on Kick and authorize it.

It is reccomended to add the bot user as a moderator for your stream. 
This will also give you access to additional [moderator functions](#chat-moderation).

---

## Important Setup & Configuration

Before running the bot, especially with the new Kick API features, please follow these setup steps.

### Environment Variables (`.env` file)

Create a `.env` file in the root directory of the project. This file will store sensitive credentials and configuration.

**Example `.env` file:**
```
# Credentials for traditional bot login (if used)
USERBOT_EMAIL="your_bot_email@example.com"
USERBOT_PASS="your_bot_password"

# Kick Application Credentials for OAuth 2.0 (New API Integration)
# Get these by registering an application on Kick
KICK_CLIENT_ID="your_kick_application_client_id"
KICK_CLIENT_SECRET="your_kick_application_client_secret"

# Redirect URI configured in your Kick Application (must match exactly)
# Used for the one-time OAuth authorization.
# If using the provided example script for authorization, this is typically:
KICK_REDIRECT_URI="http://localhost:8080/callback"

# OAuth Scopes (space-separated)
# Default: "user:read channel:read chat:write events:subscribe"
KICK_SCOPES="user:read channel:read chat:write events:subscribe"

# Webhook configuration (for receiving API events)
KICK_WEBHOOK_PATH="/kick/events"
KICK_WEBHOOK_PORT="8000"
# You might need a tool like ngrok to expose your local webhook during development/testing.
# The scripts/test_webhook.py script can help with this.
```

Ensure your actual bot script (e.g., `botoshi.py`) loads these environment variables, typically using a library like `python-dotenv` (which should be in `requirements.txt`).

### Initial OAuth Authorization (One-Time Step)

To enable features that use the new Kick API (like subscribing to gift and subscription events), you need to perform a one-time OAuth authorization. This allows Sr_Botoshi (your Kick Application) to access your Kick account data based on the requested scopes.

1.  **Ensure `.env` is configured:** Your `KICK_CLIENT_ID`, `KICK_CLIENT_SECRET`, and `KICK_REDIRECT_URI` must be correctly set in the `.env` file.
2.  **Run the authorization helper script:**
    ```bash
    conda activate kickbot # Or your virtual environment
    # Make sure PYTHONPATH is set if running scripts from the root
    # export PYTHONPATH=$(pwd):$PYTHONPATH 
    python scripts/kick_auth_example.py --authorize
    ```
3.  **Follow browser prompts:** The script will print a URL. Open it in your browser. Log in to Kick if prompted, and then authorize your application.
4.  **Token file creation:** Upon successful authorization, the script will capture the necessary tokens and save them to a file named `kickbot_tokens.json` in the project's root directory.

The bot will then use `kickbot_tokens.json` to authenticate with the Kick API for features requiring OAuth. It will automatically attempt to refresh the access token when needed. If the refresh token becomes invalid, you may need to repeat this authorization step.

### Dependencies

All required Python packages are listed in `requirements.txt`. Install them using:
```bash
pip install -r requirements.txt
```
It's highly recommended to use a virtual environment (like conda or venv) for managing dependencies.

---

## Installation

```console
pip install kickbot
```
*Note: For development, you'll typically clone this repository and install dependencies from `requirements.txt` as described above.*

## Features

Currently supports the following features. More may be added soon, and contributions are more than welcome.

- Command handling: Handle commands, looking for the first word. i.e: ```'!hello'``` 
- Message handling: Handle messages, looking to match the full message. i.e: ```'hello world'```
- Sending messages: Have the bot send a message in chat
- Replying to messages: Reply directly to a users previous message / command.
- Access streamer and chat room information.
- Chat Moderation: Get info on users, ban users, timeout users.
- Timed events: Set a reoccurring event. i.e: Sending links to socials in chat every 30 minutes.

## Example

---

*Note*: For more examples, look in the [Examples Folder](/examples)

```python3
from kickbot import KickBot, KickMessage
from datetime import timedelta


async def send_links_in_chat(bot: KickBot):
    """ Timed event to send social links every 30 mins """
    links = "Youtube: https://youtube.com\n\nTwitch: https://twitch.tv"
    await bot.send_text(links)


async def time_following(bot: KickBot, message: KickMessage):
    """ Reply to '!following' with the amount of time the user has been following for """
    sender_username = message.sender.username
    viewer_info = bot.moderator.get_viewer_info(sender_username)
    following_since = viewer_info.get('following_since')
    if following_since is not None:
        reply = f"You've been following since: {following_since}"
    else:
        reply = "Your not currently following this channel."
    await bot.reply_text(message, reply)


async def github_link(bot: KickBot, message: KickMessage):
    """ Reply to '!github' with github link """
    reply = "Github: 'https://github.com/lukemvc'"
    await bot.reply_text(message, reply)

    
async def ban_if_says_gay(bot: KickBot, message: KickMessage):
    """ Ban user for 20 minutes if they say 'your gay' """
    sender_username = message.sender.username
    ban_time = 20
    bot.moderator.timeout_user(sender_username, ban_time)

    
if __name__ == '__main__':
    USERBOT_EMAIL = "example@domain.com"
    USERBOT_PASS = "Password123"
    STREAMER = "streamer_username"
    
    bot = KickBot(USERBOT_EMAIL, USERBOT_PASS)
    bot.set_streamer(STREAMER)

    bot.add_timed_event(timedelta(minutes=30), send_links_in_chat)
    
    bot.add_command_handler('!following', time_following)
    bot.add_command_handler('!github', github_link)
    
    bot.add_message_handler('your gay', ban_if_says_gay)
    
    bot.poll()
```

<br>

## Command and Message Handling

---

- Handler callback functions must be async
- Command handler looks to match the first word of the message / command.
- Message handler looks to match the full message.

### Paramaters

```python3
bot.add_message_handler('hello world', handle_hello_message)
bot.add_command_handler('!time', handle_time_command)
```

#### Command / Message paramater (type ```str```)

- The command / message to look for 

#### Callback function (type ```Callable```)
 
- Async callback function for the command  / message to trigger


### Handler Callback function parameters:

```python3
async def handle_hello_command(bot: KickBot, message: KickMessage):...
```


#### Bot parameter (type: ```KickBot```) 

- This will give you access to functions for the bot, such as ```bot.send_text```, and ```bot.reply_text```.

#### Message parameter (type: ```KickMessage```)

- This will give you access to all attributes of the message that triggered the handler. See [KickMessage](/kickbot/kick_message.py) for 
a full list of attributes.

Some useful message attributes include:

```python3
async def hello_handler(bot: KickBot, message: KickMessage):
    content = message.content # main message content
    args = message.args # list of arguments, i.e: ['!hello', 'how', 'are', 'you?']
    message_id = message.id # The uuid of the message
    
    # sender attributes
    sender_username = message.sender.username # username of the sender
    sender_user_id = message.sender.user_id # user ID if the sender
    seder_badges = message.sender.badges # badges of the sender
    
    response = f"Hello {sender_username}"
    await bot.reply_text(message, response)
```

<br>

## Sending Messages and Reply's

Functions mainly to be used inside a callback function, to send a message in chat, or reply to a users message.

### Messages:

```python
await bot.send_text(chat_message)
```

#### Chat Message Paramater: (type: ```str```)

- Message to be sent in chat

### Reply's:

```python3
await bot.reply_text(message, reply)
```

#### Message Paramater: (type: ```KickMessage```)

- The Message you want to reply to

#### Reply Paramater: (type: ```str```)

- The Reply to send to the Message

<br>

## Streamer and Chat Information

You can access information about the streamer, and chatroom via the ```bot.streamer_info``` , ```bot.chatroom_info```
and ```bot.chatroom_settings``` dictionaries.


Streamer Info: [Full Example](/examples/streamer_info_example.json)

```python
streamer_name = bot.streamer_name
follower_count = bot.streamer_info.get('followersCount')
streamer_user_id = bot.streamer_info.get('user_id')
```

Chatroom Info: [Full Example](/examples/chatroom_info_example.json)

```python
is_chat_slow_mode = bot.chatroom_info.get('slow_mode')
is_followers_only = bot.chatroom_info.get('followers_only')
is_subscribers_only = bot.chatroom_info.get('subscribers_only')
```

Chatroom Settings: [Full Example](/examples/chatroom_settings_example.json)

```python
links_allowed = bot.chatroom_settings.get('allow_link')
is_antibot_mode = bot.chatroom_settings.get('anti_bot_mode')
gifts_enabled = bot.chatroom_settings.get('gifts_enabled')
```

Bot Settings: [Full Example](examples/bot_settings_example.json)

```python
is_mod = bot.bot_settings.get('is_moderator')
is_admin = bot.bot_settings.get('is_admin')
```

#### Viewer Count

Access the current amount of viewers in the stream as an integer. 

```python
viewers = bot.current_viewers()
```

<br>

## Chat Moderation

*Note*: You must add the bot user as a moderator to access these functions.

All moderator functions are accessed using ```bot.moderator```

### Viewer User Info

```python
viewer_info = bot.moderator.get_viewer_info('user_username')
```
Retrieve information about a viewer.

#### Paramaters:

```username``` type: ```str```

#### Returns:

Dictionary containing viewer user info. [Full Example](examples/viewer_info_example.json)

### Timeout Ban

```python
bot.moderator.timeout_user('username', 20)
```

Ban a user for a certain amount of time.

#### Paramaters:

```username``` type: ```str```: Username to be banned

```minutes``` type: ```int```: Time in minutes to ban the user for

#### Returns:

```None```

### Permaban

```python
bot.moderator.permaban('username')
```

Permanently ban a user.

#### Parameters:

```username``` type: ```str```: Username to ban permanently

#### Returns:

```None```

### Leaderboard

```python
bot.moderator.get_leaderboard()
```

Retrieve the current chat leaderboard. 

#### Parameters:

```None```

#### Returns:

Dictionary containing current chat leaderboard users and stats. [Full Example](examples/leaderboard_example.json)

<br>

## Timed Events

```python3
bot.add_timed_event(timedelta(minutes=30), send_links_in_chat)
```

Set a reoccurring function to be called, and the frequency to call the function.

i.e: Send links for your socials in chat every 30 minutes

### Parameters

#### Frequency parameter (type: ```timedelta```)

- The frequency to call the function

#### Callback function (type: ```Callable```)

- Async callback function to be called with the frequency of the parameter above

### Timed Event Callback parameter

```python3
async def send_links_in_chat(bot: Kickbot):...
```

#### bot parameter (type: ```KickBot```)

- This will give you access to functions for the bot. For timed events, the most useful 
is ```bot.send_text``` to send a reoccurring message in chat

<br>

## Kick API OAuth Integration

Sr_Botoshi is being updated to integrate with the official Kick API using OAuth 2.0 and PKCE. This enables more robust and secure access to Kick features, especially for receiving real-time events like new subscriptions and gifted subs via webhooks.

- **Authentication:** Managed by `kickbot/kick_auth_manager.py`. Requires a one-time [Initial OAuth Authorization](#initial-oauth-authorization-one-time-step).
- **Token Management:** Access and refresh tokens are stored in `kickbot_tokens.json` and automatically managed.
- **Event Subscription:** (Upcoming) The bot will use the OAuth token to subscribe to specific events from the Kick API.

Refer to `docs/authentication.md` for a detailed explanation of the OAuth flow.

## Webhooks & Signature Verification

To receive real-time events from the Kick API (e.g., subscriptions, gifts), the bot implements a webhook endpoint.

- **Webhook Handler:** `kickbot/kick_webhook_handler.py` sets up an HTTP server to listen for events from Kick.
- **Event Parsing:** Incoming webhook payloads for supported events (like `channel.followed`, `channel.subscribed`, `channel.subscription.gifted`) are parsed into Pydantic models defined in `kickbot/event_models.py`. This provides robust data validation and structured access to event data within the handler methods.
- **Testing Webhooks:** The `scripts/test_webhook.py` script can be used with `ngrok` to expose your local webhook endpoint for testing.
- **Signature Verification:** (Planned) Kick sends a signature with webhook events to verify their authenticity. This will be implemented once Kick provides clear documentation on their public key and verification process.

Configuration for the webhook (path, port) is done via the [`.env` file](#environment-variables-env-file).
For more detailed information on webhook handling, Pydantic models, and how to add new event handlers, please refer to `docs/webhooks_and_signature_verification.md`.

## Testing

### Running Tests
The project includes a suite of unit and integration tests. To run all tests:
1. Ensure your conda environment (`kickbot`) is activated.
2. Ensure `PYTHONPATH` is set correctly if running from the project root: `export PYTHONPATH=$(pwd):$PYTHONPATH`
3. Execute the test runner script:
   ```bash
   ./run_tests.sh
   ```
This script handles environment setup and executes `tests/run_tests.py`.

Refer to individual test files in the `tests/` directory for more specific test cases. The `SUMMARY.md` file also contains commands for running specific test modules.

---