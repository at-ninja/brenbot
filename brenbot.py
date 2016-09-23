import os
import sys
import time
import random
import threading
from slackclient import SlackClient

# Get the bot's token
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')

# Start Slack client
slack_client = SlackClient(SLACK_BOT_TOKEN)

# define delay for reading from the socket
READ_WEBSOCKET_DELAY = 1

# define the array used for reacting to users
REACT_TO_USERS = []
REACTIONS = []


def main():
    global REACTIONS, REACT_TO_USERS

    REACTIONS = get_emojis("emoji_filter.txt")
    REACT_TO_USERS = get_users_id("react_to.txt")

    if slack_client.rtm_connect():
        print("Brenbot connected and running!")

        reactions = threading.Thread(group=None, target=reactions_loop, name="Reactions")
        motd = threading.Thread(group=None, target=motd_loop, name="MotD")
        reactions.start()
        motd.start()

        # Wait for threads to join back to main before stopping the program
        # Todo implement a better method of stopping the program
        reactions.join()
        motd.join()
    else:
        print("Connection failed. Invalid Slack token?")


def reactions_loop():
    while threading.main_thread().is_alive():
        parse_slack_output(slack_client.rtm_read())
        time.sleep(READ_WEBSOCKET_DELAY)


def motd_loop():
    while threading.main_thread().is_alive():
        current_time = time.localtime()
        # Once a day at noon, post a MotD
        if current_time[3] == 12 and current_time[4] == 0 and current_time[5] == 0:
            post_motd()
        time.sleep(1)


def post_motd():
    with open("MotD.txt") as fp:
        lines = fp.read().strip().split("\n")

    main_message = lines[random.randrange(0, len(lines))]

    with open("MotD_random.txt") as fp:
        lines = fp.read().strip().split("\n")

    random_message = lines[random.randrange(0, len(lines))]

    with open("MotD_channels.txt") as fp:
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

    with open(file_name) as fp:
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
        Reacts to messages by a user
    """
    slack_client.api_call('reactions.add', name=REACTIONS[random.randrange(0, len(REACTIONS))],
                          timestamp=ts, channel=channel)


def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events fire-hose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'user' in output and output['user'] in REACT_TO_USERS and 'ts' in output:
                react_to_user(output['channel'], output['ts'])

    return


def get_emojis(file_name):
    with open(file_name) as fp:
        key_filter = fp.read().strip()
    api_call = slack_client.api_call("emoji.list")
    emojis = api_call.get("emoji")
    return [key for key in emojis.keys() if key_filter in key]

if __name__ == "__main__":
    sys.exit(main())
