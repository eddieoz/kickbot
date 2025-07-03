#!/usr/bin/env python3
"""
OAuth webhook server for KickBot Docker container
This server handles OAuth callbacks on port 8080 and exchanges codes for tokens
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
except ImportError:
    # Add current directory to path if import fails
    sys.path.insert(0, '.')
    from kickbot.kick_auth_manager import KickAuthManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global variables
auth_manager = None

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
    """Handle Kick API webhook events"""
    logger.info(f"Received Kick event webhook: {request.url}")
    
    try:
        # Get the request body
        body = await request.read()
        
        # Parse JSON payload
        try:
            event_data = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse webhook JSON: {e}")
            return web.Response(status=400, text="Invalid JSON")
        
        # Log the event for debugging
        event_type = event_data.get('event', {}).get('type', 'unknown')
        logger.info(f"Received Kick event: {event_type}")
        logger.debug(f"Event data: {event_data}")
        
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
                # For now, just log chat messages - command handling could be added here
                username = event_data.get('data', {}).get('sender', {}).get('username', 'Unknown')
                content = event_data.get('data', {}).get('content', '')
                logger.info(f"💬 Chat: {username}: {content}")
            else:
                logger.warning(f"Unhandled event type: {event_type}")
        except Exception as e:
            logger.error(f"Error processing event {event_type}: {e}")
        
        return web.Response(status=200, text="Event received")
        
    except Exception as e:
        logger.error(f"Error handling Kick event: {e}")
        return web.Response(status=500, text="Internal server error")

async def main():
    """Main function to start the webhook server"""
    global auth_manager
    
    # Initialize auth manager
    try:
        auth_manager = KickAuthManager()
        logger.info("KickAuthManager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize KickAuthManager: {e}")
        return
    
    # Create web application
    app = web.Application()
    app.router.add_get('/callback', handle_oauth_callback)
    app.router.add_post('/events', handle_kick_events)  # Kick API events
    app.router.add_get('/health', handle_health)
    app.router.add_get('/', handle_health)  # Root endpoint for basic health check
    
    # Start the server on port 8080 (container internal port)
    port = 8080
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🚀 OAuth webhook server started on port {port}")
    logger.info(f"Callback endpoint: http://0.0.0.0:{port}/callback")
    logger.info(f"External URL (via nginx): https://webhook.botoshi.sats4.life/callback")
    logger.info("Server is ready to receive OAuth callbacks...")
    
    # Keep the server running
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour at a time
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())