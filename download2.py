#!/usr/bin/python

import argparse
import http.client as httplib
import os
import random
import shutil
import time

import httplib2
import requests

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10


def download(target_fn, url):
    data = requests.get(url, headers={"User-Agent": "Python-3"}, stream=True)
    with open(target_fn, "wb") as f:
        data.raw.decode_content = True
        shutil.copyfileobj(data.raw, f)


if __name__ == "__main__":
    LIST = open("audo.psv", "r")
    for line in LIST:
        [dt, title, raw_file] = line.strip().split("|")
        url = f"https://www.lwbcsd.org/msg/{raw_file}"
        target_fn = f"mp3/{dt}-{title}.mp3"
        print(f"To download {url}")
        download(target_fn, url)
