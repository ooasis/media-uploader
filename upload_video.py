#!/usr/bin/python

import argparse
import http.client as httplib
import os
import random
import shutil
import time

import httplib2
import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

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
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


# Authorize the request and store authorization credentials.
def get_authenticated_service():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_local_server()
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def get_service_with_service_account():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    credentials.refresh(Request())
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def get_service_with_api_key():
    return build(
        API_SERVICE_NAME,
        API_VERSION,
        developerKey="AIzaSyC3UZ05ijeCL6Om1gvHft6oBgPCeWdpaWw",
    )


def initialize_upload(youtube, title, dt, file):
    tags = ["sermon"]

    body = dict(
        snippet=dict(title=f"{dt} {title}", tags=tags, categoryId=29),
        status=dict(privacyStatus="unlisted"),
        recordingDetails=dict(recordingDate=dt),
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting 'chunksize' equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (If the upload fails,
        # it will still be retried where it left off.) This is usually a best
        # practice, but if you're using Python older than 2.6 or if you're
        # running on App Engine, you should set the chunksize to something like
        # 1024 * 1024 (1 megabyte).
        media_body=MediaFileUpload(file, chunksize=-1, resumable=True),
    )

    resumable_upload(insert_request)


# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print("Uploading file...")
            status, response = request.next_chunk()
            if response is not None:
                if "id" in response:
                    print('Video id "%s" was successfully uploaded.' % response["id"])
                else:
                    exit("The upload failed with an unexpected response: %s" % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (
                    e.resp.status,
                    e.content,
                )
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)


def download(fn, url):
    data = requests.get(url, stream=True)
    with open(fn, "wb") as f:
        data.raw.decode_content = True
        shutil.copyfileobj(data.raw, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Video file to upload")
    args = parser.parse_args()

    youtube = get_authenticated_service()
    # youtube = get_service_with_api_key()
    # youtube = get_service_with_service_account()

    LIST = open(args.file, "r")
    for line in LIST:
        if line.startswith("#"):
            continue

        [title, dt, idx, url] = line.strip().split("|")
        fn = url.split("/")[-1]

        if not fn.endswith(".flv"):
            print(f"Skip file {fn} as it is now video file")
            continue

        try:
            print(f"Downloading file {fn} ...")
            if not os.path.isfile(fn):
                download(fn, url)
                print(f"File {fn} downloaded")
            else:
                print(f"File {fn} has already been downloaded")

            print(f"Uploading file {fn} ...")
            initialize_upload(youtube, title, dt, fn)
            print(f"File {fn} uploaded")

            if os.path.isfile(fn):
                os.remove(fn)
        except HttpError as e:
            print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
            raise e
        finally:
            pass
