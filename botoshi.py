from time import sleep
import requests
from urllib.parse import urlencode, quote_plus

from threading import Lock, Timer
lock = Lock()

import aiohttp

from kickbot import KickBot, KickMessage
from datetime import datetime, timedelta

import sys
sys.path.append('utils/TwitchMarkovChain/')

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
    """ Reply with the current UTC time """
    msg = message.content.split(' ')
    msg.pop(0)
    reply, ret = MarkovChain.generate(bot, msg)
    await bot.reply_text(message, str(reply))


async def ban_for_word(bot: KickBot, message: KickMessage):
    """ Ban user for 20 minutes if they say 'xxxx word' """
    sender_username = message.sender.username
    ban_time = 20
    bot.moderator.timeout_user(sender_username, ban_time)


async def send_links_in_chat(bot: KickBot):
    """ Timed event to send social links every 30 mins """
    links = "Youtube: https://youtube.com/eddieoz\n\nKick: https://kick.com/eddieoz\n\nSite: https://eddieoz.com"
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
    # randomize reply among a list of replies
    replies = ["Oi!", "Hello!", "Salut!", "Hallo!", "Hola!", "Ciao!", "Olá!", "Hi!", "Oi oi oi!", "Oi oi!", "Oi oi oi oi oi!"]
    reply = f"{random.choice(replies)}"
    await bot.send_text(reply)

async def im_back(bot: KickBot):
    # randomize reply among a list of replies
    replies = ["Sr. Botoshi online e se apresentando para o trabalho! 😎"]
    reply = f"{random.choice(replies)}"
    await bot.send_text(reply)
    bot.remove_timed_event(timedelta(seconds=1), im_back)


# Sound alerts
async def aplauso_alert (bot: KickBot, message: KickMessage):
    await send_alert('https://media1.giphy.com/media/YRuFixSNWFVcXaxpmX/giphy.gif', 'https://www.myinstants.com/media/sounds/aplausos-efecto-de-sonido.mp3', '', '')

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

async def msg_alert (bot: KickBot, message: KickMessage):
    msg = ' '.join(message.args[1:])
    sender = message.sender.username.replace('_', '')
    params = {
        'voice': 'Vitoria', 
        'text': f'@{sender} falou: {msg}',
    }
    audio = 'https://www.myinstants.com/media/sounds/drwho.mp3'
    await send_alert('https://media4.giphy.com/media/vs2LP0QZG7Brq/giphy.gif', audio, f'{params["text"]}', f'{params["text"]}')


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
        # Create a new lock object        
        lock.acquire(timeout=15)
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
        finally:
            # Release the lock after x seconds
            Timer(15, lock.release).start()


if __name__ == '__main__':

    USERBOT_EMAIL = settings['KickEmail']
    USERBOT_PASS = settings['KickPass']
    STREAMER = settings['KickStreamer']

    bot = KickBot(USERBOT_EMAIL, USERBOT_PASS)
    bot.set_streamer(STREAMER)

    bot.chatroom_id = settings['KickChatroom']

    bot.add_command_handler('!following', time_following)
    bot.add_command_handler('!leaders', current_leaders)
    bot.add_command_handler('!joke', tell_a_joke)
    bot.add_command_handler('!time', current_time)
    bot.add_command_handler('!github', github_link)
    bot.add_command_handler('!b', markov_chain)

    # Sound alerts
    bot.add_command_handler('!aplauso', aplauso_alert)
    bot.add_command_handler('!burro', burro_alert)
    bot.add_command_handler('!creptomoeda', creptomoeda_alert)
    bot.add_command_handler('!no', no_alert)
    bot.add_command_handler('!nani', nani_alert)
    bot.add_command_handler('!rica', rica_alert)
    bot.add_command_handler('!run', run_alert)
    bot.add_command_handler('!secnagem', secnagem_alert)
    bot.add_command_handler('!tistreza', tistreza_alert)
    bot.add_command_handler('!msg', msg_alert)

    bot.add_message_handler('bom dia', morning_greeting)
    bot.add_message_handler('boa tarde', afternoon_greeting)
    bot.add_message_handler('boa noite', night_greeting)
    bot.add_message_handler('!alert', switch_alert)

    bot.add_timed_event(timedelta(minutes=30), send_links_in_chat)
    bot.add_timed_event(timedelta(minutes=15), say_hello)
    bot.add_timed_event(timedelta(seconds=1), im_back)
    
    bot.poll()
    