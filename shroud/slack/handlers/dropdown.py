from slack_sdk import WebClient
from shroud import settings
from shroud.slack import app
from shroud.utils import db, utils

# Listener for the dropdown selection
@app.action("report_forwarding")
def handle_selection(ack, body):
    ack()

    selected_option = body["actions"][0]["selected_option"]["value"]
    db.save_selection(selection_ts=body["message"]["ts"], selection=selected_option)


# Listener for the submit button
@app.action("submit_forwarding")
def handle_submission(ack, body, say, client: WebClient):
    ack()

    user_id = body["user"]["id"]

    # Get the user's selection
    message_record = db.get_message_by_ts(body["message"]["ts"])
    user_selection = message_record.get("fields", {}).get("selection", None)
    if user_selection is not None:
        original_text = utils.get_message_body_by_ts(
            ts=message_record["fields"]["dm_ts"],
            channel=message_record["fields"]["dm_channel"],
            client=client,
        )
        # TODO: Update the message instead of sending a new one (perhaps)
        # if user_selection == "anonymous":
        #     # Forward anonymously
        #     say("Anonymously forwarding the report...")
        # else:
        #     say("Forwarding the report with your username...")

        # Update the original message to prevent reuse
        app.client.chat_update(
            channel=message_record["fields"]["dm_channel"],
            ts=message_record["fields"]["selection_ts"],
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "This report has been submitted."
                        if user_selection == "with_username"
                        else "This report has been submitted anonymously.",
                    },
                }
            ],
            text="Report submitted",
        )

        forwarded_ts = client.chat_postMessage(
            channel=settings.channel,
            text=original_text,
            username=utils.get_name(user_id, client)
            if user_selection == "with_username"
            else None,
            icon_url=utils.get_profile_picture_url(user_id, client)
            if user_selection == "with_username"
            else None,
        ).data["ts"]
        db.save_forwarded_ts(
            dm_ts=message_record["fields"]["dm_ts"], forwarded_ts=forwarded_ts
        )
        client.chat_postEphemeral(
            channel=message_record["fields"]["dm_channel"],
            user=user_id,
            text="Message content forwarded. Any replies to the forwarded message will be sent back to you as a threaded reply.",
        )
    else:
        say("Please select an option before submitting.")
