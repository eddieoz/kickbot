from time import sleep
import requests

from kickbot import KickBot, KickMessage
from datetime import datetime, timedelta

import sys
sys.path.append('utils/TwitchMarkovChain/')

# Load configurations from settings.json file
import json
with open('settings.json') as f:
    settings = json.load(f)


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


async def ban_if_says_gay(bot: KickBot, message: KickMessage):
    """ Ban user for 20 minutes if they say 'your gay' """
    sender_username = message.sender.username
    ban_time = 20
    bot.moderator.timeout_user(sender_username, ban_time)


async def send_links_in_chat(bot: KickBot):
    """ Timed event to send social links every 30 mins """
    links = "Youtube: https://youtube.com/eddieoz\n\nKick: https://kick.com/eddieoz"
    await bot.send_text(links)


async def github_link(bot: KickBot, message: KickMessage):
    """ Reply to '!github' command with link to github"""
    reply = "Github: 'https://github.com/eddieoz'"
    await bot.reply_text(message, reply)

import random

async def morning_greeting(bot: KickBot, message: KickMessage):
    # randomize reply among a list of replies
    replies = ["Bom dia!", "Good morning!", "Bonjour!", "Guten Morgen!", "GM!", "Buenos dias!", "Buongiorno!"]
    reply = f"{random.choice(replies)} @{message.sender.username}"
    await bot.reply_text(message, reply)

async def afternoon_greeting(bot: KickBot, message: KickMessage):
    # randomize reply among a list of replies
    replies = ["Boa tarde!", "Good afternoon!", "Bonjour!", "Guten Tag!", "GT!", "Buenas tardes!", "Buon pomeriggio!"]
    reply = f"{random.choice(replies)} @{message.sender.username}"
    await bot.reply_text(message, reply)

async def night_greeting(bot: KickBot, message: KickMessage):
    # randomize reply among a list of replies
    replies = ["Boa noite!", "Good night!", "Bonsoir!", "Gute Nacht!", "GN!", "Buenas noches!", "Buona notte!"]
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

    bot.add_message_handler('bom dia', morning_greeting)
    bot.add_message_handler('boa tarde', afternoon_greeting)
    bot.add_message_handler('boa noite', night_greeting)

    bot.add_timed_event(timedelta(minutes=30), send_links_in_chat)
    bot.add_timed_event(timedelta(minutes=15), say_hello)
    bot.add_timed_event(timedelta(seconds=1), im_back)
    
    bot.poll()
    