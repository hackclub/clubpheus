from slack_bolt.context.say import Say
from slack_sdk import WebClient
from shroud import settings
from shroud.slack import app
from shroud.utils import db, utils
from slack_bolt.context.respond import Respond


# https://api.slack.com/events/message.im
@app.event("message")
def handle_message(event, say: Say, client: WebClient, respond: Respond):
  
    if event.get("thread_ts") is not None:
        lookup_ts = event["thread_ts"]
    elif event.get("previous_message", {}).get("thread_ts") is not None:
        lookup_ts = event["previous_message"]["thread_ts"]
    else:
        lookup_ts = event["ts"]
     # Get the record from the database. Only notify the user if the event is a DM
    record = db.get_message_by_ts(
        lookup_ts
    )
    if record is None:
        if event.get("channel_type") == "im" and event.get("subtype") is None:
            if event.get("thread_ts") is None:
                utils.begin_forward(event, client)
            else:
                client.chat_postEphemeral(
                channel=event["channel"],
                user=event["user"],
                text="No relay found for this thread.",
            )
        else:
            print("No relay found for this ts.")
        # Return, don't error, since the bot might not be in a channel solely for relays
        return
    record = record["fields"]
  
    # If the event is a subtype, ignore it
    # If it's message_changed, send an ephemeral message to the user stating that the bot doesn't support edits and deletions
    if (
        event.get("subtype") == "message_changed"
        or event.get("subtype") == "message_deleted"
    ):
        client.chat_postEphemeral(
            channel=event["channel"],
            user=event["previous_message"]["user"],
            text="It seems you might have updated a message. This bot only supports forwarding messages, at the moment. Thus, edits and deletions will not be forwarded.",
        )
        return
    elif event.get("subtype") is not None:
        print(f"Received an event with subtype: {event.get('subtype')}; ignoring it.")
        return
    # If there is no ts at all and the subtype is none, something has definitely gone wrong
    if event.get("ts") is None:
        print(f"Received an event without a timestamp; ignoring: {event}")
        raise ValueError("Event does not have a timestamp")


    # Handle incoming DMs
    if event.get("channel_type") == "im":
        # Existing conversation
        # Really no need for a conditional since if it was a top-level message, it would have been caught and a relay would have been started
        if event.get("thread_ts") is not None:
            if record.get("forwarded_ts") is None:
                client.chat_postEphemeral(
                    channel=event["channel"],
                    user=event["user"],
                    thread_ts=event["thread_ts"],
                    text="This message isn't a relay. This might be because you haven't selected how to forward it, the bot didn't catch the message, or the message is invalid.",
                )
                return
            to_send = f"{event['text']}"
            client.chat_postMessage(
                channel=settings.channel,
                text=to_send,
                thread_ts=record["forwarded_ts"],
            )
    # Handle incoming messages in channels
    # A group is a private channel and a channel is a public channel
    elif event.get("channel_type") == "group" or event.get("channel_type") == "channel":
        client.chat_postMessage(
            channel=record["dm_channel"],
            text=event["text"],
            thread_ts=record["dm_ts"],
            username=utils.get_name(event["user"], client),
            icon_url=utils.get_profile_picture_url(event["user"], client),
        )