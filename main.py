"""
Discord bot for my private Valheim server. Periodically pings server to check if it's up and updates status accordingly
on the appropriate server channel in Discord. Also handles a number of chat commands (with prefix '!')
Author: Saku Aaltonen, saku.aaltonen12@gmail.com
"""

# TODO: make everything more scalable (change hardcoded channels into a dynamic list)
# TODO: save configuration in a file
# TODO: add moderator privileges instead of admin for stuff like sethost
#  ---- add moderator list, list editable by server owner via chat command
# TODO: add chat command for getting all available commands
# use caching(?)


import discord
from discord.ext import tasks, commands
import platform    # For getting the operating system name
import subprocess  # For executing a shell command
import time


# Add token in deployment
TOKEN = ''
HOST = 0
CHANNELS = {'server-info': 813821310437949521,
            'server-status': 813477087041028096,
            'runestone': 813444963316138054,
            'bot': 953615976723791902}
SERVER_STATUS = 'UP'
VALHEIM_PLAYERS = {}


intents = discord.Intents.all()
intents.members = True  # Needed for member activity update event
client = commands.Bot(command_prefix='!', intents=intents)


def get_host():
    global HOST
    return HOST


def ping(ip):
    """
    NEEDS REFACTORING
    Pings 'ip'. Returns True if ping went through, False otherwise. Works on win and unix.
    """

    # param = '-n' if platform.system().lower() == 'windows' else '-c'
    # Building the command. Ex: "ping -c 1 google.com"
    command = ['nc', '-z', '-u', str(ip), 2456]
    status = True if subprocess.call(command, stdout=subprocess.DEVNULL) == 0 else False
    return status


"""
SCHEDULED TASKS
"""
# Check server status periodically
# NOT IN USE UNTIL PING IS REFACTORED
@tasks.loop(minutes=1)
async def server_status_check(channelID=CHANNELS['bot']):
    """
    Pings HOST. Updates SERVER_STATUS and posts a message to channel (channelID)
    if status changes.
    """
    host = get_host()
    channel = client.get_channel(channelID)

    status = "UP" if ping(host) else "DOWN"

    # If status has changed, post it to channel and update global variable
    global SERVER_STATUS
    if status != SERVER_STATUS:
        await channel.send('Server ' + status)
        SERVER_STATUS = status
        print('SERVER STATUS CHANGED TO', SERVER_STATUS)


# Notify if someone has been playing Valheim alone for half an hour
@tasks.loop(minutes=1)
async def valheim_session_check(channelID=CHANNELS['runestone']):
    player_count = 0
    player_name = ''
    global VALHEIM_PLAYERS

    for member in VALHEIM_PLAYERS:
        if VALHEIM_PLAYERS[member][0]: 
            player_count += 1
            player_name = member
    
    if player_count > 1:
        # If more than one player, reset logging (to prevent notifying right after player count drops to one)
        VALHEIM_PLAYERS = {}

    elif player_count == 1 and (time.time() - VALHEIM_PLAYERS[member][0] > 1800) and not VALHEIM_PLAYERS[member][1]:
        channel = client.get_channel(channelID)
        await channel.send(f"{player_name} has been fighting trolls alone for hours, go help him! @here")
        VALHEIM_PLAYERS[member][1] = True
        print(f"{time.asctime(time.localtime())} {player_name} is lonely")


"""
EVENTS
"""
@client.event
async def on_ready():
    print("YmirBot running")
    valheim_session_check.start()
#    server_status_check.start()


# Log when someone starts playing Valheim
# TODO: implement member_prefs file to save data in (e.g. opt out of this)
@client.event
async def on_member_update(before, after):
    # Only trigger on activity change
    if before.activity != after.activity:
        if after.activity and after.activity.name == 'Valheim':
            # Log time started playing for the member [unix epoch : float, chat notif sent : bool]
            global VALHEIM_PLAYERS
            VALHEIM_PLAYERS[after.name] = [time.time(), False]
            print(f"{time.asctime(time.localtime())} {before.name} started playing")
        else:
            # Reset logging for member if not playing valheim
            VALHEIM_PLAYERS[after.name] = [None, False]

"""
CHAT COMMANDS
"""
# Test chat command
@client.command(pass_context=True, name='skål')
async def skal(ctx):
    await ctx.send('Skål!')


# Update server host address
# TODO: Save address in a file
@client.command(pass_context=True)
@commands.has_permissions(administrator=True)
async def sethost(ctx, new_host):
    """
    Try to reach new host by pinging. If ping is successful, change host.
    """
    print("Attempting to set host as " + new_host + "...")
    global HOST
    if HOST == new_host:
        await ctx.send("Host already set as " + HOST)
        return
    if ping(new_host):
        HOST = new_host
        await ctx.send("Host changed")
        print("NEW HOST SET: " + HOST)
    else:
        await ctx.send("Error: Could not ping new host")
        print("Ping failed")


client.run(TOKEN)
