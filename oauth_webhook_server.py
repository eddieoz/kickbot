#!/usr/bin/env python3
"""
Unified Webhook Server for KickBot (Story 2)
This server handles OAuth callbacks and Kick API webhook events on port 8080
Integrates with bot instance for command processing and includes signature verification
"""

import asyncio
import os
import sys
from pathlib import Path
from aiohttp import web
from urllib.parse import parse_qs, quote_plus
import logging
import json
import aiohttp
from typing import Optional, Dict, Any

# Load .env manually since python-dotenv might not be available
def load_env_file(env_path='.env'):
    """Manually load environment variables from .env file"""
    env_file = Path(env_path)
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Load environment variables
load_env_file()

try:
    from kickbot.kick_auth_manager import KickAuthManager
    from kickbot.kick_signature_verifier import KickSignatureVerifier
    from kickbot.kick_message import KickMessage
except ImportError:
    # Add current directory to path if import fails
    sys.path.insert(0, '.')
    from kickbot.kick_auth_manager import KickAuthManager
    from kickbot.kick_signature_verifier import KickSignatureVerifier
    from kickbot.kick_message import KickMessage

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global variables
auth_manager = None
signature_verifier = None
bot_instance = None
enable_signature_verification = False

# Message deduplication system
import time
processed_messages = {}  # message_id -> timestamp
DEDUP_WINDOW_SECONDS = 30  # Ignore duplicates within 30 seconds

# Load settings for alerts
try:
    with open('settings.json', 'r') as f:
        settings = json.load(f)
except Exception as e:
    logger.error(f"Failed to load settings.json: {e}")
    settings = {}

async def send_alert(img, audio, text, tts):
    """Send alert to the alert system"""
    if settings.get('Alerts', {}).get('Enable', False):
        try:
            async with aiohttp.ClientSession() as session:
                width = '300px'
                fontFamily = 'Arial'
                fontSize = 30
                color = 'gold'
                borderColor = 'black'
                borderWidth = 2
                duration = 9000
                parameters = f'/trigger_alert?gif={img}&audio={quote_plus(audio)}&text={text}&tts={tts}&width={width}&fontFamily={fontFamily}&fontSize={fontSize}&borderColor={borderColor}&borderWidth={borderWidth}&color={color}&duration={duration}'
                url = settings['Alerts']['Host'] + parameters + '&api_key=' + settings['Alerts']['ApiKey']
                async with session.get(url) as response:
                    response_text = await response.text()
                    logger.info(f"Alert sent successfully: {response.status}")
        except Exception as e:
            logger.error(f'Error sending alert: {e}')

async def handle_follow_event(event_data):
    """Handle follow events"""
    try:
        follower_name = event_data.get('follower', {}).get('username', 'Unknown')
        logger.info(f"🎉 New follower: {follower_name}")
        
        # Send follow alert
        await send_alert(
            'https://media.giphy.com/media/3o6Zt6MLxUZV2LlqWc/giphy.gif',
            'https://www.myinstants.com/media/sounds/aplausos-efecto-de-sonido.mp3',
            f'Novo seguidor: {follower_name}!',
            f'Obrigado por seguir, {follower_name}!'
        )
    except Exception as e:
        logger.error(f"Error handling follow event: {e}")

async def handle_subscription_event(event_data):
    """Handle subscription events"""
    try:
        subscriber_name = event_data.get('subscriber', {}).get('username', 'Unknown')
        tier = event_data.get('tier', 1)
        logger.info(f"🎉 New subscription: {subscriber_name} (Tier {tier})")
        
        # Send subscription alert
        await send_alert(
            'https://media.tenor.com/0rEqnyTyZToAAAAC/eu-sou-rica-im-rich.gif',
            'https://www.myinstants.com/media/sounds/eu-sou-rica_1.mp3',
            f'Nova assinatura Tier {tier}: {subscriber_name}!',
            f'Obrigado pela assinatura, {subscriber_name}!'
        )
    except Exception as e:
        logger.error(f"Error handling subscription event: {e}")

async def handle_gift_subscription_event(event_data):
    """Handle gifted subscription events"""
    try:
        gifter_name = event_data.get('gifter', {}).get('username', 'Unknown')
        quantity = event_data.get('quantity', 1)
        logger.info(f"🎁 Gifted subscriptions: {gifter_name} gifted {quantity} subs")
        
        # Send gift subscription alert
        await send_alert(
            'https://media1.tenor.com/m/1Nr6H8HTWfUAAAAC/jim-chewing.gif',
            'https://www.myinstants.com/media/sounds/aplausos-efecto-de-sonido.mp3',
            f'{gifter_name} presenteou {quantity} assinatura(s)!',
            f'Muito obrigado pela generosidade, {gifter_name}!'
        )
    except Exception as e:
        logger.error(f"Error handling gift subscription event: {e}")

async def handle_chat_message_event(event_data):
    """Handle chat message events and process bot commands"""
    global bot_instance, processed_messages
    
    try:
        # Extract message information
        message_id = event_data.get('message_id', 'unknown')
        sender_data = event_data.get('sender', {})
        username = sender_data.get('username', 'Unknown')
        content = event_data.get('content', '')
        
        # Deduplication: Check if we've already processed this message recently
        current_time = time.time()
        if message_id in processed_messages:
            time_diff = current_time - processed_messages[message_id]
            if time_diff < DEDUP_WINDOW_SECONDS:
                logger.info(f"🔄 Ignoring duplicate message (ID: {message_id}, {time_diff:.1f}s ago): {username}: {content}")
                return
        
        # Clean old entries from deduplication cache (keep only last hour)
        cutoff_time = current_time - 3600  # 1 hour
        processed_messages = {msg_id: timestamp for msg_id, timestamp in processed_messages.items() if timestamp > cutoff_time}
        
        # Mark this message as processed
        processed_messages[message_id] = current_time
        
        logger.info(f"💬 Chat: {username}: {content}")
        
        # If we have a bot instance, process the message for commands
        if bot_instance:
            try:
                # Create a KickMessage-like object from the webhook data
                # This mimics the structure that the bot expects
                message_data = {
                    'id': event_data.get('message_id', 'webhook-msg'),
                    'chatroom_id': getattr(bot_instance, 'chatroom_id', 1164726),
                    'content': content,
                    'type': 'message',
                    'created_at': event_data.get('created_at', ''),
                    'sender': {
                        'id': sender_data.get('user_id', 0),
                        'username': username,
                        'slug': sender_data.get('channel_slug', username.lower()),
                        'identity': sender_data.get('identity', {})
                    }
                }
                
                # Create KickMessage instance
                kick_message = KickMessage(message_data)
                
                # Process the message through the bot's handlers
                await process_bot_message(kick_message)
                
            except Exception as e:
                logger.error(f"Error processing chat message through bot: {e}")
        
    except Exception as e:
        logger.error(f"Error handling chat message event: {e}")

async def process_bot_message(message: KickMessage):
    """Process a chat message through the bot's command and message handlers"""
    global bot_instance
    
    if not bot_instance:
        return
    
    try:
        # Check for command handlers
        content = message.content.strip()
        if content.startswith('!'):
            command = content.split()[0].lower()
            
            # Check if we have a handler for this command
            if hasattr(bot_instance, 'handled_commands') and command in bot_instance.handled_commands:
                handler = bot_instance.handled_commands[command]
                logger.info(f"🤖 Executing command handler for: {command}")
                
                # Execute the command handler
                if asyncio.iscoroutinefunction(handler):
                    await handler(bot_instance, message)
                else:
                    handler(bot_instance, message)
                    
                logger.info(f"✅ Command {command} executed successfully")
            else:
                logger.warning(f"❌ No handler found for command: {command}")
                if hasattr(bot_instance, 'handled_commands'):
                    logger.info(f"📋 Available commands: {list(bot_instance.handled_commands.keys())}")
        
        # Check for message handlers (pattern matching)
        if hasattr(bot_instance, 'handled_messages'):
            for pattern, handler in bot_instance.handled_messages.items():
                if pattern.lower() in content.lower():
                    logger.info(f"🔍 Executing message handler for pattern: {pattern}")
                    
                    if asyncio.iscoroutinefunction(handler):
                        await handler(bot_instance, message)
                    else:
                        handler(bot_instance, message)
                    break  # Only execute first matching handler
                    
    except Exception as e:
        logger.error(f"Error processing bot message: {e}")

def set_bot_instance(bot):
    """Set the bot instance for command processing"""
    global bot_instance
    bot_instance = bot
    logger.info("Bot instance set for webhook command processing")

async def handle_oauth_callback(request):
    """Handle the OAuth callback from Kick"""
    global auth_manager
    
    logger.info(f"Received OAuth callback: {request.url}")
    
    # Extract code from query parameters
    params = request.rel_url.query
    if 'code' in params:
        auth_code = params['code']
        state = params.get('state', 'N/A')
        
        logger.info(f"Received authorization code: {auth_code[:20]}...")
        logger.info(f"State: {state}")
        
        # We need the code_verifier that was used to generate the authorization URL
        # For now, let's try to get it from a temporary file or regenerate the auth flow
        try:
            # Check if we have a stored code_verifier
            verifier_file = Path('oauth_verifier.txt')
            if verifier_file.exists():
                with open(verifier_file, 'r') as f:
                    code_verifier = f.read().strip()
                logger.info("Using stored code verifier")
            else:
                # Generate a new auth flow to get the verifier
                logger.warning("No stored code verifier found. This might cause issues.")
                # For now, let's store the code and let the user complete the process manually
                with open('oauth_code.txt', 'w') as f:
                    f.write(auth_code)
                logger.info(f"Stored authorization code to oauth_code.txt: {auth_code}")
                
                return web.Response(
                    text=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Code Received</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
        .info {{ color: #0066cc; font-size: 18px; }}
        .code {{ background: #f0f0f0; padding: 10px; margin: 20px; font-family: monospace; }}
    </style>
</head>
<body>
    <h1 class="info">✅ Authorization Code Received</h1>
    <p>Your authorization code has been received and stored.</p>
    <div class="code">Code: {auth_code}</div>
    <p>Please run the manual token exchange process.</p>
</body>
</html>
                    """,
                    content_type='text/html'
                )
            
            # Exchange code for tokens
            logger.info("Exchanging authorization code for tokens...")
            tokens = await auth_manager.exchange_code_for_tokens(auth_code, code_verifier)
            logger.info("✅ Tokens received and stored successfully!")
            
            # Clean up temporary files
            try:
                verifier_file.unlink(missing_ok=True)
                Path('oauth_code.txt').unlink(missing_ok=True)
            except:
                pass
            
            return web.Response(
                text="""
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Successful</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 50px; text-align: center; }
        .success { color: green; font-size: 18px; }
        .info { color: #666; margin-top: 20px; }
    </style>
</head>
<body>
    <h1 class="success">✅ Authorization Successful!</h1>
    <p>Your KickBot has been successfully authorized with OAuth tokens.</p>
    <p class="info">You can now close this window and start your bot.</p>
</body>
</html>
                """,
                content_type='text/html'
            )
            
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            return web.Response(
                text=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Failed</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
        .error {{ color: red; font-size: 18px; }}
        .info {{ color: #666; margin-top: 20px; }}
        .code {{ background: #f0f0f0; padding: 10px; margin: 20px; font-family: monospace; }}
    </style>
</head>
<body>
    <h1 class="error">❌ Authorization Failed</h1>
    <p>Error: {e}</p>
    <div class="code">Code received: {auth_code}</div>
    <p class="info">The code has been stored. Please check the server logs and try manual token exchange.</p>
</body>
</html>
                """,
                content_type='text/html',
                status=500
            )
    else:
        error = params.get('error', 'Unknown error')
        error_description = params.get('error_description', 'No description provided')
        logger.error(f"Authorization failed: {error} - {error_description}")
        
        return web.Response(
            text=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Failed</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
        .error {{ color: red; font-size: 18px; }}
    </style>
</head>
<body>
    <h1 class="error">❌ Authorization Failed</h1>
    <p>Error: {error}</p>
    <p>Description: {error_description}</p>
</body>
</html>
            """,
            content_type='text/html',
            status=400
        )

async def handle_health(request):
    """Simple health check endpoint"""
    return web.Response(text="OK", status=200)

async def handle_kick_events(request):
    """Handle Kick API webhook events with signature verification"""
    global signature_verifier, enable_signature_verification
    
    logger.info(f"Received Kick event webhook: {request.url}")
    
    try:
        # Get the request body
        body = await request.read()
        
        # Signature verification if enabled
        if enable_signature_verification and signature_verifier:
            signature_header = request.headers.get('X-Kick-Signature')
            if not signature_header:
                logger.warning("Missing signature header for webhook verification")
                return web.Response(status=401, text="Missing signature")
            
            # Verify the signature
            is_valid = await signature_verifier.verify_signature(body, signature_header)
            if not is_valid:
                logger.error("Invalid webhook signature")
                return web.Response(status=401, text="Invalid signature")
            
            logger.info("Webhook signature verified successfully")
        
        # Parse JSON payload
        try:
            event_data = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse webhook JSON: {e}")
            return web.Response(status=400, text="Invalid JSON")
        
        # Get event type from Kick-Event-Type header (standard Kick webhook approach)
        event_type = request.headers.get('Kick-Event-Type', 'unknown')
        event_version = request.headers.get('Kick-Event-Version', '1')
        
        logger.info(f"Received Kick event: {event_type} (version: {event_version})")
        
        # Fallback detection for events without proper headers
        if event_type == 'unknown':
            # Check for direct chat message structure
            if all(key in event_data for key in ['message_id', 'broadcaster', 'sender', 'content']):
                event_type = 'chat.message.sent'
                logger.info(f"✅ Detected chat message from structure: {event_data.get('sender', {}).get('username', 'unknown')} -> {event_data.get('content', '')}")
            # Check for follow structure
            elif 'follower' in event_data and 'followed_at' in event_data:
                event_type = 'channel.followed'
            # Check for subscription structure
            elif 'subscriber' in event_data and ('subscribed_at' in event_data or 'gifted_subscriptions' in event_data):
                if 'gifted_subscriptions' in event_data:
                    event_type = 'channel.subscription.gifts'
                else:
                    event_type = 'channel.subscription.new'
        
        # Dispatch events to appropriate handlers
        try:
            if event_type == 'channel.followed':
                await handle_follow_event(event_data.get('data', {}))
            elif event_type == 'channel.subscription.new':
                await handle_subscription_event(event_data.get('data', {}))
            elif event_type == 'channel.subscription.gifts':
                await handle_gift_subscription_event(event_data.get('data', {}))
            elif event_type == 'channel.subscription.renewal':
                await handle_subscription_event(event_data.get('data', {}))  # Reuse subscription handler
            elif event_type == 'chat.message.sent':
                # Process chat messages and execute bot commands
                # For direct message payload structure, pass the entire event_data
                await handle_chat_message_event(event_data)
            else:
                logger.warning(f"Unhandled event type: {event_type}")
        except Exception as e:
            logger.error(f"Error processing event {event_type}: {e}")
        
        return web.Response(status=200, text="Event received")
        
    except Exception as e:
        logger.error(f"Error handling Kick event: {e}")
        return web.Response(status=500, text="Internal server error")

async def create_app() -> web.Application:
    """Create and configure the webhook application"""
    global auth_manager, signature_verifier, enable_signature_verification
    
    # Initialize auth manager
    try:
        auth_manager = KickAuthManager()
        logger.info("KickAuthManager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize KickAuthManager: {e}")
        # Don't return here, allow app to start without auth manager for basic functionality
    
    # Initialize signature verifier if enabled
    if enable_signature_verification:
        try:
            signature_verifier = KickSignatureVerifier()
            logger.info("KickSignatureVerifier initialized")
        except Exception as e:
            logger.error(f"Failed to initialize KickSignatureVerifier: {e}")
            enable_signature_verification = False
    
    # Create web application
    app = web.Application()
    app.router.add_get('/callback', handle_oauth_callback)
    app.router.add_post('/events', handle_kick_events)  # Kick API events
    app.router.add_get('/health', handle_health)
    app.router.add_get('/', handle_health)  # Root endpoint for basic health check
    
    return app

async def main():
    """Main function to start the unified webhook server"""
    global enable_signature_verification
    
    # Read signature verification setting from environment or settings
    enable_signature_verification = os.environ.get('KICK_WEBHOOK_SIGNATURE_VERIFICATION', 'false').lower() == 'true'
    if enable_signature_verification:
        logger.info("Webhook signature verification is ENABLED")
    else:
        logger.info("Webhook signature verification is DISABLED")
    
    # Create the application
    app = await create_app()
    
    # Start the server on port 8080 (unified port for both OAuth and webhooks)
    port = int(os.environ.get('KICK_WEBHOOK_PORT', 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🚀 Unified Webhook Server started on port {port}")
    logger.info(f"📋 Available endpoints:")
    logger.info(f"  - OAuth Callback: http://0.0.0.0:{port}/callback")
    logger.info(f"  - Webhook Events: http://0.0.0.0:{port}/events")
    logger.info(f"  - Health Check: http://0.0.0.0:{port}/health")
    logger.info(f"🌐 External URL (via nginx): https://webhook.botoshi.sats4.life/")
    logger.info("✅ Server is ready to receive OAuth callbacks and webhook events...")
    
    # Keep the server running
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour at a time
    except KeyboardInterrupt:
        logger.info("Shutting down unified webhook server...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())