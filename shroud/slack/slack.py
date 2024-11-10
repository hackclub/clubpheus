from shroud import settings

# Slack imports
from slack_bolt import App, BoltResponse
from slack_bolt.adapter.socket_mode import SocketModeHandler

from slack_bolt.context.respond import Respond
from slack_sdk.errors import SlackApiError

# To avoid a log message about unhandled requests
from slack_bolt.error import BoltUnhandledRequestError


SLACK_BOT_TOKEN = settings.slack_bot_token
SLACK_APP_TOKEN = settings.slack_app_token
app = App(token=SLACK_BOT_TOKEN, raise_error_for_unhandled_request=True)


def start_app():
    global app
    SocketModeHandler(app, SLACK_APP_TOKEN).start()


# https://github.com/slackapi/bolt-python/issues/299#issuecomment-823590042
@app.error
def handle_errors(error, body, respond: Respond):
    if isinstance(error, BoltUnhandledRequestError):
        return BoltResponse(status=200, body="")
    else:
        print(f"Error: {str(error)}")
        try:
            respond(
                "Something went wrong. If this persists, please contact <@U075RTSLDQ8>."
            )
        except SlackApiError as e:
            print(f"Error sending message: {e.response['error']}")
        return BoltResponse(status=500, body="Something Wrong")
