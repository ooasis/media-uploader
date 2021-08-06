#!/usr/bin/python

import argparse
import http.client as httplib

import httplib2
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error,
    IOError,
    httplib.NotConnected,
    httplib.IncompleteRead,
    httplib.ImproperConnectionState,
    httplib.CannotSendRequest,
    httplib.CannotSendHeader,
    httplib.ResponseNotReady,
    httplib.BadStatusLine,
)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the {{ Google Cloud Console }} at
# {{ https://cloud.google.com/console }}.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = os.environ["CLIENT_SECRETS_FILE"]
SERVICE_ACCOUNT_FILE = os.environ["SERVICE_ACCOUNT_FILE"]

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

CHANNEL_ID = "UCkgHSp9rAnzaO2mlDCZdOwA"
CATEGORY_ID = "29"
TAGS = ["sermon", "证道"]

# Authorize the request and store authorization credentials.
def get_authenticated_service():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_local_server()
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def get_service_with_service_account():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Video file to upload")
    args = parser.parse_args()

    youtube = get_authenticated_service()

    LIST = open(args.file, "r")
    for line in LIST:
        if line.startswith("#"):
            continue

        [video_url, title, desc] = line.strip().split("|")
        video_id = video_url.split("/")[-1]
        try:
            request = youtube.videos().list(part="snippet", id=video_id)
            response = request.execute()
            published_dt = response["items"][0]["snippet"]["publishedAt"]
            dt = published_dt.split("T")[0]
            new_title = f"{dt} {title}"

            request = youtube.videos().update(
                part="snippet",
                body={
                    "id": video_id,
                    "snippet": {
                        "categoryId": CATEGORY_ID,
                        "description": desc,
                        "tags": TAGS,
                        "title": new_title,
                    },
                },
            )
            response = request.execute()
            print(f"Update video {new_title}")

        except HttpError as e:
            print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
            raise e
        finally:
            pass
