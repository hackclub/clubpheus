import yaml
import importlib.resources
from slack_sdk.web.client import WebClient
from slack_bolt.context.respond import Respond
from shroud.slack import app
from shroud.utils import db, utils
from shroud import settings

@app.command(utils.apply_command_prefix("clean-db"))
def clean_db(ack, respond: Respond, client: WebClient):
    print("Cleaning database")
    ack()
    db.clean_database(client)
    respond(
        "Removed any records where the DM or the forwarded message no longer exists."
    )
    print("Cleaned database")

@app.command(utils.apply_command_prefix("create-dm"))
def create_dm(ack, respond: Respond, client: WebClient, command):
    ack()
    allowlist_channel = settings.channel
    user_id = command["user_id"]
    target_user = command["text"].strip()

    # Check if user is in the allowlist channel
    try:
        members = client.conversations_members(channel=allowlist_channel)["members"]
        if user_id not in members:
            respond("You must be a member of the allowlist channel to use this command.")
            return
    except Exception as e:
        respond(f"Failed to verify channel membership: {e}")
        return

    # Extract the user ID from the format <@U1234|user>
    if target_user.startswith("<@") and "|" in target_user:
        target_user = target_user[2:].split("|")[0]
    else:
        respond("Unable to extract user ID.")
        return

    # Create a ~~DM~~ private channel with the target user and the person who ran the command
    try:
        invite_users = [user_id, target_user]
        channel_name= f"{settings.app_name}-{target_user.lower()}"
        private_channel = client.conversations_create(
            name=channel_name,
            is_private=True,
        )["channel"]["id"]
        existed = False
    except Exception as e:
        if e.response["error"] == "name_taken":
            respond("A DM with this name already exists.")
        else:
            respond(f"Failed to create DM: {e}")
        # Get the channel ID from channel_name
        private_channel = client.conversations_list(types="private_channel")["channels"]
        # next function retrieves the first matching channel from the generator.
        # If no match is found, it returns None.
        private_channel = next(
            (channel for channel in private_channel if channel["name"] == channel_name),
            None,
        )
        if private_channel is None:
            respond("Unable to find the private channel.")
            return
        private_channel = private_channel["id"]
        existed = True
    else:
        respond(f"Created a prviate channel <#{private_channel}>")
    try:
        client.conversations_invite(
            channel=private_channel, users=",".join(invite_users)
        )
    except Exception as e:
        if e.response["error"] == "already_in_channel":
            respond("You are already in this DM.")
        else:
            respond(f"Failed to invite users to the DM: {e}")
        # Send a message to the allowlist channel with a button to join the DM
        client.chat_postMessage(
            channel=allowlist_channel,
            text=f"A private channel has been created: <#{private_channel}> with <@{target_user}>. Click the button below to join.",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"A private channel has been created: <#{private_channel}> with <@{target_user}>. Click the button below to join.",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Join private channel",
                            },
                            "action_id": "join_private_channel",
                            "value": private_channel,
                        }
                    ],
                },
            ],
        )

@app.action("join_private_channel")
def join_dm(ack, body, client: WebClient):
    ack()
    user_id = body["user"]["id"]
    private_channel = body["actions"][0]["value"]

    try:
        # Invite the user to the DM channel
        client.conversations_invite(channel=private_channel, users=user_id)
        client.chat_postEphemeral(
            channel=private_channel,
            user=user_id,
            text="You have been added to the channel.",
        )
    except Exception as e:
        if e.response["error"] == "already_in_channel":
            client.chat_postEphemeral(
                channel=private_channel,
                user=user_id,
                text="You are already in this DM.",
            )
        else:
            # Send an error message to the user
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=user_id,
                text=f"Failed to join channel: {e}",
            )

@app.command(utils.apply_command_prefix("help"))
def help_command(ack, respond: Respond):
    ack()
    # The package looks like shroud.slack and we only want shroud/manifest.yml
    manifest_path = importlib.resources.files(__package__.split(".")[0]).parent / "manifest.yml"
    with open(manifest_path, "r") as f:
        features = yaml.safe_load(f)["features"]

    help_text = "Commands:" if not settings.leading_help_text else settings.leading_help_text + "\nCommands:"
    slash_commands = features.get("slash_commands", [])
    for command in slash_commands:
        try:
            help_text += f"\n`{command['command']} {command['usage_hint']}`: {command['description']}"
        except KeyError:
            # Most likely means that usage_hint is not defined
            help_text += f"\n`{command['command']}`: {command['description']}"
    if len(slash_commands) == 0:
        help_text += "\nNo commands available.\n"
    else:
        help_text += "\n"

    shortcuts = features.get("shortcuts", [])
    help_text += "\nShortcuts:"
    message_shortcuts_text = "Message shortcuts:"
    global_shortcuts_text = "Global shortcuts:"
    for shortcut in shortcuts:
        if shortcut["type"] == "message":
            message_shortcuts_text += (
                f"\n`{shortcut["name"]}`: {shortcut['description']}"
            )
        elif shortcut["type"] == "global":
            global_shortcuts_text += (
                f"\n`{shortcut["name"]}`: {shortcut['description']}"
            )
    if len(shortcuts) == 0:
        help_text += "\nNo shortcuts available."
    else:
        if message_shortcuts_text != "Message shortcuts:":
            help_text += f"\n{message_shortcuts_text}"
        if global_shortcuts_text != "Global shortcuts:":
            help_text += f"\n{global_shortcuts_text}"

    respond(help_text)