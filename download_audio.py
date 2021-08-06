#!/usr/bin/python

import argparse
import http.client as httplib
import os
import random
import shutil
import time

import eyed3
import httplib2
import requests
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
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def download(target_fn, url):
    data = requests.get(url, headers={"User-Agent": "Python-3"}, stream=True)
    with open(target_fn, "wb") as f:
        data.raw.decode_content = True
        shutil.copyfileobj(data.raw, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Video file to upload")
    args = parser.parse_args()

    LIST = open(args.file, "r")
    for line in LIST:
        if line.startswith("#"):
            continue

        [title, dt, idx, url] = line.strip().split("|")
        fn = url.split("/")[-1]

        if not fn.endswith(".mp3"):
            print(f"Skip file {fn} as it is not audio file")
            continue

        try:
            target_fn = f"mp3/{dt} - {title}.mp3"
            print(f"Downloading file {fn} ...")
            if not os.path.isfile(target_fn):
                download(target_fn, url)
                print(f"File {fn} downloaded")
                af = eyed3.load(target_fn)
                if af.tag is None:
                    af.initTag()
                print(f"Update title from {af.tag.title} to {dt} - {title}")
                af.tag.title = f"{dt} - {title}"
                af.tag.artist = "sermon"
                af.tag.album = "sermon"
                af.tag.save(encoding="utf-8")
            else:
                # pass
                print(f"File {target_fn} has already been downloaded")

        except HttpError as e:
            print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
            raise e
        except Exception as e:
            print("An error occurred:\n%s" % (e))
            # raise e
        finally:
            pass
