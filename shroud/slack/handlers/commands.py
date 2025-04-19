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

    # Extract the user ID from the format <@U1234|user>
    if target_user.startswith("<@") and "|" in target_user:
        target_user = target_user[2:].split("|")[0]
    else:
        respond("Unable to extract user ID.")
        return

    # Check if the user is in the allowlist channel
    try:
        members = client.conversations_members(channel=allowlist_channel)["members"]
        if user_id not in members:
            respond("You are not authorized to use this command.")
            return
    except Exception as e:
        respond(f"Failed to verify authorization: {e}")
        return

    # Fetch all members in the allowlist channel
    try:
        members = client.conversations_members(channel=allowlist_channel)["members"]
    except Exception as e:
        respond(f"Failed to fetch members of the allowlist channel: {e}")
        return

    # Create a DM with the target user and all allowlist members
    try:
        dm_users = [target_user] + members
        dm_channel = client.conversations_open(users=",".join(dm_users))["channel"]["id"]
        respond(f"Created a DM with the target user and allowlist members: <#{dm_channel}>")
        client.chat_postMessage(
            channel=allowlist_channel,
            text=f"A new DM has been created: <#{dm_channel}>",
        )
    except Exception as e:
        respond(f"Failed to create DM: {e}")

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