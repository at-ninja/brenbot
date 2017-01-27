#!/usr/bin/env python3

import sys

sys.path.append('/usr/local/lib/python3.5/site-packages')

import logging
import logging.handlers
import os

import time
import random
import threading
import subprocess
from slackclient import SlackClient



__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

# Get the bot's token
SLACK_BOT_TOKEN = ""
with open(os.path.join(__location__, 'secret.txt')) as fp:
    SLACK_BOT_TOKEN = fp.read().strip()

BOT_ID = ""
AT_BOT = ""

# Start Slack client
slack_client = SlackClient(SLACK_BOT_TOKEN)

# define delay for reading from the socket
READ_WEBSOCKET_DELAY = 1

# define the array used for reacting to users
REACT_TO_USERS = []
REACTIONS = []

# Create the running var
IS_RUNNING = True

# Deafults for logging
LOG_FILENAME = os.path.join(__location__, "logs/Brenbot.log")
LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"

# Configure logging to log to a file, making a new file at midnight and keeping the last 3 day's data
# Give the logger a unique name (good practice)
logger = logging.getLogger(__name__)
# Set the log level to LOG_LEVEL
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)

# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
        def __init__(self, logger, level):
                """Needs a logger and a logger level."""
                self.logger = logger
                self.level = level

        def write(self, message):
                # Only log if there is a message (not just a new line)
                if message.rstrip() != "":
                        self.logger.log(self.level, message.rstrip())

# Replace stdout with logging to file at INFO level
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)


def main():
    global REACTIONS, REACT_TO_USERS, IS_RUNNING, BOT_ID, AT_BOT, __location__
    try:
        if slack_client.rtm_connect():

            REACTIONS = get_emojis("emoji_filter.txt")
            REACT_TO_USERS = get_users_id("react_to.txt")

            with open(os.path.join(__location__, "my_name.txt")) as fp:
                BOT_ID = get_user_id(fp.readline().strip())
            AT_BOT = "<@" + BOT_ID + ">"

            print("Brenbot connected and running!")

            reactions = threading.Thread(group=None, target=reactions_loop, name="Reactions")
            motd = threading.Thread(group=None, target=motd_loop, name="MotD")
            reactions.start()
            motd.start()

            reactions.join()
            motd.join()
        else:
            print("Connection failed. Invalid Slack token?")
    except Exception as exception:
        IS_RUNNING = False
        print(str(exception))



def reactions_loop():
    global IS_RUNNING
    try:
        while IS_RUNNING and threading.main_thread().is_alive():
            parse_slack_output(slack_client.rtm_read())
            time.sleep(READ_WEBSOCKET_DELAY)
    except:
        IS_RUNNING = False


def motd_loop():
    global IS_RUNNING
    try:
        while IS_RUNNING and threading.main_thread().is_alive():
            current_time = time.localtime()
            # Once a day at noon, post a MotD
            if current_time[3] == 12 and current_time[4] == 0 and current_time[5] == 0:
                post_motd()
            time.sleep(1)
    except:
        IS_RUNNING = False


def post_motd():
    global __location__
    with open(os.path.join(__location__, "MotD.txt")) as fp:
        lines = fp.read().strip().split("\n")

    main_message = lines[random.randrange(0, len(lines))]

    with open(os.path.join(__location__, "MotD_random.txt")) as fp:
        lines = fp.read().strip().split("\n")

    random_message = lines[random.randrange(0, len(lines))]

    with open(os.path.join(__location__, "MotD_channels.txt")) as fp:
            channels = fp.read().strip().split("\n")

    for channel in channels:
        slack_client.api_call("chat.postMessage", channel=channel,
                              text=main_message + random_message, as_user=True)


def get_user_id(name):
    api_call = slack_client.api_call("users.list")
    if api_call.get('ok'):
        # retrieve all users so we can find our bot
        users = api_call.get('members')
        for user in users:
            if 'name' in user and user.get('name') == name:
                return user.get('id')
        return None
    else:
        raise Exception("API call 'users.list' was unsuccessful")


def get_users_id(file_name):
    global __location__
    with open(os.path.join(__location__, file_name)) as fp:
        names = fp.read().strip().split("\n")

    api_call = slack_client.api_call("users.list")
    if api_call.get('ok'):
        # retrieve all users so we can find our bot
        users = api_call.get('members')
        results = []
        for user in users:
            if 'name' in user and user.get('name') in names:
                results = results + [user.get('id')]
        return results
    else:
        raise Exception("API call 'users.list' was unsuccessful")


def react_to_user(channel, ts):
    """
        Reacts to messages by a user by using reactions (emoji)
    """
    slack_client.api_call('reactions.add', name=REACTIONS[random.randrange(0, len(REACTIONS))],
                          timestamp=ts, channel=channel)


def react_to_message(channel, user, text):
    """
        Reacts to a command (message) from a user by posting a response.
    """
    # If fortune is in the text, we will assume the user wants a brenbot fortune
    if 'fortune' in text and 'wild' in text:
        fortune = subprocess.check_output(['fortune']).decode('utf-8')
        fortune = "<@" + user + ">: " + fortune
        slack_client.api_call('chat.postMessage', channel=channel, text=fortune, as_user=True)
    elif 'fortune' in text and 'cow' in text:
        fortune = subprocess.check_output(['fortune | cowsay']).decode('utf-8')
        fortune = "<@" + user + ">: " + fortune
        slack_client.api_call('chat.postMessage', channel=channel, text=fortune, as_user=True)
    elif 'fortune' in text:
        fortune = subprocess.check_output(['fortune']).decode('utf-8')
        fortune = "<@" + user + ">: " + fortune
        slack_client.api_call('chat.postMessage', channel=channel, text=fortune, as_user=True)
    elif user in REACT_TO_USERS and 'say:' in text:
        # TODO make this command cleaner execution-wise
        say_to_channel = ''.join(text.split('say:')[1:]).strip()
        channel_to_send = '#' + say_to_channel.split(' ')[0].strip()
        say_to_channel = ' '.join(say_to_channel.split(' ')[1:]).strip()
        slack_client.api_call('chat.postMessage', channel=channel_to_send, text=say_to_channel, as_user=True)


def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events fire-hose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'user' in output and output['user'] in REACT_TO_USERS \
                    and 'type' in output and output['type'] == 'message' \
                    and 'channel' in output \
                    and 'ts' in output:
                react_to_user(output['channel'], output['ts'])
            if output and 'type' in output and output['type'] == 'message' \
                    and 'text' in output and AT_BOT in output['text'] \
                    and 'channel' in output \
                    and 'user' in output:
                react_to_message(output['channel'], output['user'], output['text'])


def get_emojis(file_name):
    global __location__
    with open(os.path.join(__location__, file_name)) as fp:
        key_filter = fp.read().strip()
    api_call = slack_client.api_call("emoji.list")
    emojis = api_call.get("emoji")
    return [key for key in emojis.keys() if key_filter in key]

if __name__ == "__main__":
    sys.exit(main())
