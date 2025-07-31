import os
from dotenv import load_dotenv
load_dotenv()

import logging
from time import sleep
import requests
from urllib.parse import urlencode, quote_plus
import asyncio
import argparse
import sys
from pathlib import Path

from threading import Lock, Timer
lock = Lock()

import aiohttp

from kickbot import KickBot, KickMessage
from datetime import datetime, timedelta

sys.path.append('utils/TwitchMarkovChain/')

from utils.repeat_bot import repeat

# Load configurations from settings.json file
import json
with open('settings.json') as f:
    settings = json.load(f)

import random

from utils.TwitchMarkovChain.MarkovChainBot import MarkovChain

async def time_following(bot: KickBot, message: KickMessage):
    """ Reply with the amount of time the user has been following for """
    sender_username = message.sender.username
    viewer_info = bot.moderator.get_viewer_info(sender_username)
    following_since = viewer_info.get('following_since')
    if following_since is not None:
        reply = f"You've been following since: {following_since}"
    else:
        reply = "Your not currently following this channel."
    await bot.reply_text(message, reply)


async def current_leaders(bot: KickBot, message: KickMessage):
    """ Retrieve usernames of current leaders and send in chat"""
    usernames = []
    leaderboard = bot.moderator.get_leaderboard()
    gift_leaders = leaderboard.get('gifts')
    for user in gift_leaders:
        usernames.append(user['username'])
    leader_message = "Current Leaders: " + ", ".join(usernames)
    await bot.send_text(leader_message)


async def tell_a_joke(bot: KickBot, message: KickMessage):
    """ Reply with a random joke """
    url = "https://v2.jokeapi.dev/joke/Any?type=single"
    joke = requests.get(url).json().get('joke')
    await bot.reply_text(message, joke)


async def current_time(bot: KickBot, message: KickMessage):
    """ Reply with the current UTC time """
    time = datetime.utcnow().strftime("%I:%M %p")
    reply = f"Current UTC time: {time}"
    await bot.reply_text(message, reply)


async def markov_chain(bot: KickBot, message: KickMessage):
    """ Generate text using Markov chain algorithm """
    msg = message.content.split(' ')
    msg.pop(0)  # Remove the command itself
    
    # Use the bot's generate method instead of directly calling MarkovChain.generate
    reply, ret = bot.generate(msg)

    if 'gerard' in reply.casefold():
        try:
            response = requests.post("http://192.168.0.30:7862/update_botoshi", json={'botoshi': reply.casefold().replace("gerard", "Gerrár Aithen")})
            if response.status_code == 200:
                print("Context updated successfully.")
            else:
                print(f"Failed to update context: {response.status_code}")
        except Exception as e:
            print(f"Error updating context: {e}")

    # await bot.reply_text(message, str(reply))
    await bot.send_text(str(reply))

async def repeat_bot_pt(bot: KickBot, message: KickMessage):
    """ Repete as últimas infos faladas na live """
    # await bot.reply_text(message, str(reply))
    # Usar o diretório desejado e o número de linhas
    directory = "..\\..\\eddieoz twitch\\transcripts\\"
    n_lines = 50
    language = 'portuguese'
    reply = repeat(directory, n_lines, language)
    await bot.send_text(str(reply))

async def repeat_bot_en(bot: KickBot, message: KickMessage):
    """ Repete as últimas infos faladas na live """
    # await bot.reply_text(message, str(reply))
    # Usar o diretório desejado e o número de linhas
    directory = "..\\..\\eddieoz twitch\\transcripts\\"
    n_lines = 50
    language = 'english'
    reply = repeat(directory, n_lines, language)
    await bot.send_text(str(reply))


async def ban_for_word(bot: KickBot, message: KickMessage):
    """ Ban user for 20 minutes if they say 'xxxx word' """
    sender_username = message.sender.username
    ban_time = 20
    bot.moderator.permaban(sender_username, ban_time)

async def ban_forever(bot: KickBot, message: KickMessage):
    """ Ban user forever if they say 'xxxx word' """
    sender_username = message.sender.username
    ban_time = 0
    bot.moderator.permaban(sender_username)

async def ban_by_bot_message(bot: KickBot, message: KickMessage):
    """ Ban user forever if they say 'xxxx word' """
    sender_username = message.sender.username
    if sender_username == 'Kicklet':
        content = message.content
        if "Thank you for the follow," in content:
            username = content.split(",")[1].strip().replace("!", "")
            bot.moderator.permaban(username)

async def send_links_in_chat(bot: KickBot):
    if not getattr(bot, "is_live", False):
        return
    links = "Youtube: https://youtube.com/eddieoz\n\nKick: https://kick.com/eddieoz\n\nSite: https://eddieoz.com"
    await bot.send_text(links)

async def send_links_livecoins(bot: KickBot):
    if not getattr(bot, "is_live", False):
        return
    links = "Estamos participando da votação da Livecoins! Vote em nós! https://form.respondi.app/pjSDK4qg "
    await bot.send_text(links)

async def github_link(bot: KickBot, message: KickMessage):
    """ Reply to '!github' command with link to github"""
    reply = "Github: 'https://github.com/eddieoz'"
    await bot.reply_text(message, reply)

async def morning_greeting(bot: KickBot, message: KickMessage):
    # randomize reply among a list of replies
    replies = ["Bom dia!", "Good morning!", "Bonjour!", "Guten Morgen!", "GM!", "Buenos dias!", "Buongiorno!", "Tere Hommikust!"]
    reply = f"{random.choice(replies)} @{message.sender.username}"
    await bot.reply_text(message, reply)
    # send_alert('https://media.giphy.com/media/3o6Zt6MLxUZV2LlqWc/giphy.gif', 'https://www.myinstants.com/media/sounds/oh-my-god.mp3', reply)
    
async def afternoon_greeting(bot: KickBot, message: KickMessage):
    # randomize reply among a list of replies
    replies = ["Boa tarde!", "Good afternoon!", "Bonjour!", "Guten Tag!", "GT!", "Buenas tardes!", "Buon pomeriggio!", "Tere Päevast!"]
    reply = f"{random.choice(replies)} @{message.sender.username}"
    await bot.reply_text(message, reply)

async def night_greeting(bot: KickBot, message: KickMessage):
    # randomize reply among a list of replies
    replies = ["Boa noite!", "Good night!", "Bonsoir!", "Gute Nacht!", "GN!", "Buenas noches!", "Buona notte!", "Head ööd!"]
    reply = f"{random.choice(replies)} @{message.sender.username}"
    await bot.reply_text(message, reply)

async def say_hello(bot: KickBot):
    if not getattr(bot, "is_live", False):
        return
    replies = ["Oi!", "Hello!", "Salut!", "Hallo!", "Hola!", "Ciao!", "Olá!", "Hi!", "Oi oi oi!", "Oi oi!", "Oi oi oi oi oi!"]
    reply = f"{random.choice(replies)}"
    await bot.send_text(reply)

async def im_back(bot: KickBot):
    if not getattr(bot, "is_live", False):
        return
    replies = ["Sr. Botoshi online e se apresentando para o trabalho! 😎"]
    reply = f"{random.choice(replies)}"
    await bot.send_text(reply)
    bot.remove_timed_event(timedelta(seconds=1), im_back)


# Sound alerts
async def sons_alert (bot: KickBot, message: KickMessage):
    reply = "Comandos de som: !aplauso !creptomoeda !nani !secnagem !no !rica !run !tistreza !burro !zero !what !doida !risada !vergonha !certo !triste !cadeira !inveja !didi !elon !safado !viagem !laele !chato !farao !bobtalik"
    await bot.send_text(reply)

async def aplauso_alert (bot: KickBot, message: KickMessage):
    # await send_alert('https://media1.giphy.com/media/YRuFixSNWFVcXaxpmX/giphy.gif', 'https://www.myinstants.com/media/sounds/aplausos-efecto-de-sonido.mp3', '', '')
    await send_alert('https://media1.tenor.com/m/KGz3fTqyJFkAAAAd/elon-musk-barron-trump.gif', 'https://www.myinstants.com/media/sounds/aplausos-efecto-de-sonido.mp3', '', '')

async def burro_alert (bot: KickBot, message: KickMessage):
    await send_alert(' https://media.tenor.com/eRqBfix38e0AAAAC/dumb-youaredumb.gif', 'https://www.myinstants.com/media/sounds/como-voce-e-burro_2.mp3', '', '')

async def creptomoeda_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media.tenor.com/2HaiQQmkMx8AAAAC/leonardo-di-caprio-leo-dicaprio.gif', 'https://www.myinstants.com/media/sounds/creptomoeda.mp3', '', '')

async def no_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media1.giphy.com/media/vyTnNTrs3wqQ0UIvwE/giphy.gif', 'https://www.myinstants.com/media/sounds/no-god-please-no-noooooooooo.mp3', '', '')

async def nani_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media.tenor.com/SqD2xKy43LMAAAAC/what-why.gif', 'https://www.myinstants.com/media/sounds/nani_mkANQUf.mp3', '', '')

async def rica_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media.tenor.com/0rEqnyTyZToAAAAC/eu-sou-rica-im-rich.gif', 'https://www.myinstants.com/media/sounds/eu-sou-rica_1.mp3', '', '')

async def run_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media.tenor.com/5j25wi9o-2YAAAAC/furious-munishkanth.gif', 'https://www.myinstants.com/media/sounds/run-vine-sound-effect_1_8k87k9t.mp3', '', '')

async def secnagem_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media.tenor.com/h9zATR2d9z0AAAAd/elon-musk-%E3%82%A4%E3%83%BC%E3%83%AD%E3%83%B3%E3%83%9E%E3%82%B9%E3%82%AF.gif', 'https://www.myinstants.com/media/sounds/secnagem_ZUkBLxx.mp3', '', '')

async def tistreza_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media.tenor.com/tn2SbVbK4moAAAAC/que-tistreza-felipe-davila-debate-presidencial-globo.gif', 'https://www.myinstants.com/media/sounds/que-tistreza.mp3', '', '')

async def went2zero_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://c.tenor.com/-GEbmhD-ca4AAAAC/tenor.gif', 'https://www.myinstants.com/media/sounds/went2zero.mp3', '', '')

async def what_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media1.tenor.com/m/LomlJOfsbbQAAAAC/vitalik.gif', 'https://www.myinstants.com/media/sounds/vitalik-whaaaat.mp3', '', '')

async def doida_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media1.tenor.com/m/LsWOiOjRbaMAAAAC/sense-marcia.gif', 'https://www.myinstants.com/media/sounds/para-de-ser-doida-marcia-semsitiva.mp3', '', '')

async def risada_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://c.tenor.com/NqTP3bhMQkEAAAAC/tenor.gif', 'https://www.myinstants.com/media/sounds/heres-what-immigrants-think-about-the-wall-original-video-audiotrimmer.mp3', '', '')

async def vergonha_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://c.tenor.com/uWiCz2tqzXAAAAAC/tenor.gif', 'https://www.myinstants.com/media/sounds/jacquin-voce-e-a-vergonha-da-profissao.mp3', '', '')

async def certo_isso (bot: KickBot, message: KickMessage):
    await send_alert('https://media1.tenor.com/m/rEBXmYIAMr0AAAAC/felca-susto.gif', 'https://www.myinstants.com/media/sounds/felca-ta-certo-isso.mp3', '', '')

async def triste_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media1.tenor.com/m/I1R_uwk05DAAAAAC/sad-boys-rain.gif', 'https://www.myinstants.com/media/sounds/naruto-sad-music-instant.mp3', '', '')

async def cadeira_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media1.tenor.com/m/fe0xysTdZz0AAAAC/datena-cadeira.gif', 'https://www.myinstants.com/media/sounds/one-punchhhhh-one-punchhhhh.mp3', '', '')

async def inveja_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media1.tenor.com/m/1Nr6H8HTWfUAAAAC/jim-chewing.gif', 'https://www.myinstants.com/media/sounds/o-a-inveja.mp3', '', '')

async def didi_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media1.tenor.com/m/CtBMikB_xrQAAAAd/didi-didicao.gif', 'https://www.myinstants.com/media/sounds/risada-de-zacarias.mp3', '', '')

async def elon_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://c.tenor.com/dT8haFvTVyEAAAAd/tenor.gif', 'https://www.myinstants.com/media/sounds/elon-musk-1.mp3', '', '')

async def safado_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://i.giphy.com/mK4yuNnIuXKty9GDyW.webp', 'https://www.myinstants.com/media/sounds/cachorro-safado.mp3', '', '')

async def viagem_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media1.tenor.com/m/xXkJHjznKPoAAAAd/elon-musk-tripping.gif', 'https://www.myinstants.com/media/sounds/viagem.mp3', '', '')

async def laele_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media1.tenor.com/m/zJxKn-nsy-wAAAAC/rock-sus.gif', 'https://www.myinstants.com/media/sounds/la-ele-de-novo.mp3', '', '')

async def morrediabo_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media1.tenor.com/m/zJxKn-nsy-wAAAAC/rock-sus.gif', 'https://www.myinstants.com/media/sounds/la-ele-de-novo.mp3', '', '')

async def chato_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://www.eddieoz.com/content/images/2025/05/media.gif', 'https://www.myinstants.com/media/sounds/chato_1CGBysf.mp3', 'Alerta de inconveniencia', 'Chato Chato Chato')

async def pharaoh_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://www.eddieoz.com/content/images/2025/07/faraoh--1-.gif', 'https://www.myinstants.com/media/sounds/pharaoh.mp3', '', '')

async def bobtalik_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://www.eddieoz.com/content/images/2025/07/Bobtalik-1.gif', 'https://www.eddieoz.com/content/media/2025/07/bobtalik.mp3', '', '')



async def msg_alert (bot: KickBot, message: KickMessage):
    reply = 'Use o LivePix e mande sua mensagem! :)'
    await bot.reply_text(message, reply)
    # await bot.send_text("Teste: use o qr-code :)")
    # msg = ' '.join(message.args[1:])
    # sender = message.sender.username.replace('_', '')
    # params = {
    #     'voice': 'Vitoria', 
    #     'text': f'@{sender} falou: {msg}',
    # }
    # audio = 'https://www.myinstants.com/media/sounds/doctor-who-2.mp3'
    # await send_alert('https://media4.giphy.com/media/vs2LP0QZG7Brq/giphy.gif', audio, f'{params["text"]}', f'{params["text"]}')


async def switch_alert(bot: KickBot, message: KickMessage):
    """ Reply with the current UTC time """
    if message.data['sender']['identity']['badges'][0]['type'] == 'broadcaster' or message.data['sender']['identity']['badges'][0]['type'] == 'moderator':
        if message.args[1] == 'on':
            settings['Alerts']['Enable'] = True
            reply = 'Alerts enabled!'
        elif message.args[1] == 'off':
            settings['Alerts']['Enable'] = False
            reply = 'Alerts disabled!'
        await bot.reply_text(message, str(reply))

async def send_alert(img, audio, text, tts):
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
                parameters = f'/trigger_alert?gif={img}&audio={quote_plus(audio)}&text={text}&tts={tts}&width={width}&fontFamily={fontFamily}&fontSize={fontSize}&borderColor={borderColor}&borderWidth={borderWidth}&color={color}&duration={duration}'
                url = settings['Alerts']['Host'] + parameters + '&api_key=' + settings['Alerts']['ApiKey']
                # alert = requests.get(url)
                async with session.get(url) as response:
                    response_text = await response.text()
        except Exception as e:
            print(f'Error sending alert: {e}')

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='KickBot - OAuth Webhook Bot')
    parser.add_argument('--force-reauth', action='store_true', 
                       help='Force re-authentication by clearing existing OAuth tokens')
    parser.add_argument('--clear-tokens', action='store_true',
                       help='Clear OAuth tokens and exit (useful for testing)')
    args = parser.parse_args()
    
    # Handle force re-authentication
    if args.force_reauth or args.clear_tokens:
        token_file = Path('kickbot_tokens.json')
        if token_file.exists():
            token_file.unlink()
            print(f"🗑️  Cleared OAuth tokens from {token_file}")
        else:
            print(f"ℹ️  No token file found at {token_file}")
            
        # Also clear any temporary OAuth files
        for temp_file in ['oauth_verifier.txt', 'oauth_code.txt']:
            temp_path = Path(temp_file)
            if temp_path.exists():
                temp_path.unlink()
                print(f"🗑️  Cleared temporary file: {temp_file}")
        
        if args.clear_tokens:
            print("✅ OAuth tokens cleared. Exiting.")
            return
        
        print("🔄 Forcing re-authentication on next startup...")

    USERBOT_EMAIL = settings.get('KickEmail')
    USERBOT_PASS = settings.get('KickPass')
    STREAMER = settings['KickStreamer']

    # Use OAuth authentication instead of user/pass to avoid rate limiting
    bot = KickBot(use_oauth=True)
    bot.set_settings(settings)
    await bot.set_streamer(STREAMER)

    bot.chatroom_id = settings['KickChatroom']

    bot.add_command_handler('!following', time_following)
    bot.add_command_handler('!leaders', current_leaders)
    bot.add_command_handler('!joke', tell_a_joke)
    bot.add_command_handler('!time', current_time)
    bot.add_command_handler('!github', github_link)
    bot.add_command_handler('!b', markov_chain)
    bot.add_command_handler('!repete', repeat_bot_pt)
    bot.add_command_handler('!repeat', repeat_bot_en)

    # Sound alerts
    bot.add_command_handler('!sons', sons_alert)
    bot.add_command_handler('!aplauso', aplauso_alert)
    bot.add_command_handler('!burro', burro_alert)
    bot.add_command_handler('!creptomoeda', creptomoeda_alert)
    bot.add_command_handler('!no', no_alert)
    bot.add_command_handler('!nani', nani_alert)
    bot.add_command_handler('!rica', rica_alert)
    bot.add_command_handler('!run', run_alert)
    bot.add_command_handler('!secnagem', secnagem_alert)
    bot.add_command_handler('!tistreza', tistreza_alert)
    bot.add_command_handler('!zero', went2zero_alert)
    bot.add_command_handler('!what', what_alert)
    bot.add_command_handler('!msg', msg_alert)
    bot.add_command_handler('!doida', doida_alert)
    bot.add_command_handler('!risada', risada_alert)
    bot.add_command_handler('!vergonha', vergonha_alert)
    bot.add_command_handler('!certo', certo_isso)
    bot.add_command_handler('!triste', triste_alert)
    # bot.add_command_handler('!cadeira', cadeira_alert)
    bot.add_command_handler('!inveja', inveja_alert)
    bot.add_command_handler('!didi', didi_alert)
    bot.add_command_handler('!elon', elon_alert)
    bot.add_command_handler('!safado', safado_alert)
    bot.add_command_handler('!viagem', viagem_alert)
    bot.add_command_handler('!laele', laele_alert)
    bot.add_command_handler('!chato', chato_alert)
    bot.add_command_handler('!farao', pharaoh_alert)
    bot.add_command_handler('!bobtalik', bobtalik_alert)

    bot.add_message_handler('bom dia', morning_greeting)
    bot.add_message_handler('boa tarde', afternoon_greeting)
    bot.add_message_handler('boa noite', night_greeting)
    bot.add_message_handler('thsch', ban_by_bot_message)
    bot.add_message_handler('rabb', ban_by_bot_message)
    bot.add_message_handler('ytlive', ban_by_bot_message)
    bot.add_message_handler('adolp', ban_by_bot_message)
    bot.add_message_handler('hate', ban_by_bot_message)
    bot.add_message_handler('etler', ban_by_bot_message)

    bot.add_message_handler('abra e não feche a torneira', ban_forever)
    bot.add_message_handler('adicione água sanitária', ban_forever)

    bot.add_timed_event(timedelta(minutes=35), send_links_in_chat)
    #bot.add_timed_event(timedelta(minutes=25), send_links_livecoins)
    bot.add_timed_event(timedelta(minutes=15), say_hello)
    bot.add_timed_event(timedelta(seconds=1), im_back)

    # Check if we should use webhook mode instead of traditional WebSocket
    webhook_enabled = settings.get('KickWebhookEnabled', True)
    disable_internal_webhook = settings.get('FeatureFlags', {}).get('DisableInternalWebhookServer', True)
    
    if webhook_enabled and disable_internal_webhook:
        print("🚀 Starting KickBot with Unified Webhook Server (Story 2)")
        print("📋 This replaces WebSocket polling with OAuth webhook events")
        
        # Import the unified webhook server
        import oauth_webhook_server
        
        # Set the bot instance for webhook command processing
        oauth_webhook_server.set_bot_instance(bot)
        print("✅ Bot instance integrated with webhook server")
        
        # Initialize basic bot components for webhook mode
        async with aiohttp.ClientSession() as session:
            bot.http_session = session
            print("✅ HTTP session created")
            
            # Start webhook server FIRST so it can handle OAuth callbacks
            print("🌐 Starting unified webhook server on port 8080...")
            
            # Import and start the webhook server in background
            webhook_server_task = asyncio.create_task(oauth_webhook_server.main())
            print("✅ Webhook server started and ready to handle OAuth callbacks")
            
            # Add a small delay to ensure server is fully up
            await asyncio.sleep(2)
            
            # Now initialize authentication (which may trigger OAuth flow)
            try:
                await bot._initialize_oauth_authentication()
                print("✅ Authentication initialized")
            except Exception as e:
                print(f"❌ Authentication failed: {e}")
                print("⚠️  Webhook server remains running for OAuth callbacks")
                # Let the webhook server continue running for OAuth callbacks
                await webhook_server_task
            
            # Get streamer info for moderator functions
            try:
                from kickbot.kick_helper import get_streamer_info, get_chatroom_settings, get_bot_settings
                await get_streamer_info(bot)
                await get_chatroom_settings(bot)
                await get_bot_settings(bot)
                print("✅ Streamer info loaded")
            except Exception as e:
                print(f"⚠️  Using fallback streamer info: {e}")
                # Use fallback info from settings
                bot.streamer_info = {'id': 1139843, 'user': {'id': 1139843}}
                bot.chatroom_info = {'id': int(settings.get('KickChatroom', 1164726))}
                bot.chatroom_id = int(settings.get('KickChatroom', 1164726))
                bot.is_mod = True
            
            # Initialize moderator if needed (OAuth-only mode)
            if not bot.moderator and bot.auth_manager:
                from kickbot.kick_moderator import Moderator
                bot.moderator = Moderator(bot)
                print("✅ Moderator initialized")
            
            # Initialize Event Manager and subscribe to events
            if bot.auth_manager and bot.streamer_info and bot.streamer_info.get('id'):
                from kickbot.kick_event_manager import KickEventManager
                
                broadcaster_id = bot.streamer_info['id']
                webhook_url = os.environ.get('KICK_WEBHOOK_URL', 'https://webhook.botoshi.sats4.life/events')
                bot.event_manager = KickEventManager(
                    auth_manager=bot.auth_manager,
                    client=None,  # OAuth-only mode - no client needed
                    broadcaster_user_id=broadcaster_id,
                    webhook_url=webhook_url
                )
                
                # No direct auth token in OAuth-only mode - using OAuth tokens instead
                print("✅ Event manager initialized with OAuth authentication")
                
                print(f"✅ Event manager initialized for broadcaster ID: {broadcaster_id}")
                
                # Subscribe to configured events
                if bot.kick_events_to_subscribe:
                    print(f"🔔 Subscribing to {len(bot.kick_events_to_subscribe)} event types...")
                    try:
                        # Retry logic for event subscription
                        max_retries = 3
                        retry_delay = 5
                        success = False
                        
                        for attempt in range(1, max_retries + 1):
                            print(f"📡 Event subscription attempt {attempt}/{max_retries}")
                            success = await bot.event_manager.resubscribe_to_configured_events(bot.kick_events_to_subscribe)
                            
                            if success:
                                print("✅ Successfully subscribed to all configured Kick events")
                                print(f"📋 Subscribed events: {[event['name'] for event in bot.kick_events_to_subscribe]}")
                                break
                            elif attempt < max_retries:
                                print(f"⚠️  Subscription attempt {attempt} failed, retrying in {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2
                        
                        if not success:
                            print("❌ Failed to subscribe to events after all retries")
                            print("⚠️  Bot will continue but may not receive webhook events")
                            
                    except Exception as e:
                        print(f"❌ Error during event subscription: {e}")
                        print("⚠️  Bot will continue but may not receive webhook events")
                
                # Set up periodic subscription verification
                verification_interval = timedelta(minutes=30)
                # Create a wrapper function that matches the timed event signature
                async def subscription_verification_wrapper(bot_instance):
                    await bot_instance.verify_event_subscriptions()
                
                bot.add_timed_event(verification_interval, subscription_verification_wrapper)
                print(f"✅ Subscription verification scheduled every {verification_interval}")
            else:
                print("⚠️  Event manager not initialized - missing auth manager or streamer info")
            
            print("🌐 Webhook server already running, waiting for events...")
            
            # Wait for the webhook server task that was started earlier
            await webhook_server_task
    else:
        print("🔌 Starting KickBot with traditional WebSocket mode")
        await bot.run()

if __name__ == '__main__':
    asyncio.run(main())
    
