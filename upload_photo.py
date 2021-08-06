#!/usr/bin/python

import argparse
import http.client as httplib
import json
import os
import shutil

import httplib2
import requests
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from PIL import Image

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
SCOPES = ["https://www.googleapis.com/auth/photoslibrary"]
API_SERVICE_NAME = "photoslibrary"
API_VERSION = "v1"

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


# Authorize the request and store authorization credentials.
def get_authenticated_service():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_console()
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def get_service_with_service_account():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def upload(photolib, photo_file):
    token = photolib._http.credentials.token
    url = "https://photoslibrary.googleapis.com/v1/uploads"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
        "X-Goog-Upload-Content-Type": "image/jpeg",
        "X-Goog-Upload-Protocol": "raw",
    }
    upload_token = requests.post(
        url, headers=headers, data=open(photo_file, "rb").read()
    ).text

    payload = json.dumps(
        {
            "newMediaItems": [
                {
                    "description": photo_file,
                    "simpleMediaItem": {
                        "fileName": photo_file,
                        "uploadToken": upload_token,
                    },
                }
            ]
        }
    )

    url = "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, data=payload)

    # r = photolib.mediaItems().batchCreate(payload).execute()
    print(f"Upload response: {r}")


def download(pth, fn):
    url = f"https://www.lwbcsd.org/wordpress/wp-content/uploads/{pth}"
    data = requests.get(url, stream=True)
    with open(fn, "wb") as f:
        data.raw.decode_content = True
        shutil.copyfileobj(data.raw, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Video file to upload")
    args = parser.parse_args()

    photolib = get_authenticated_service()
    LIST = open(args.file, "r")
    for line in LIST:
        pth = line.strip()
        fn = pth.split("/")[-1]
        download(pth, fn)
        im = Image.open(fn)
        (width, height) = im.size
        if width >= 1000 and height >= 1000:
            print(f"Skip picture {fn}: {im.size}")
        elif width >= 1000 or height >= 1000:
            print(f"To upload picture {fn}: {im.size}")
            upload(photolib, fn)
            print(f"Uploaded picture {fn}")
        else:
            print(f"Skip picture {fn}: {im.size}")

        if os.path.isfile(fn):
            os.remove(fn)

