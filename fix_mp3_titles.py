#!/usr/bin/python

import os

import eyed3

if __name__ == "__main__":

    for f in os.listdir("mp3"):
        title = f.split(".")[0]
        try:
            af = eyed3.load(f"mp3/{f}")
            if af is None:
                print(f"Cannot load file {f}")
            if af.tag is None:
                af.initTag()
            print(f"Update title from {af.tag.title} to {title}")
            af.tag.title = title
            af.tag.artist = "sermon"
            af.tag.album = "sermon"
            af.tag.save(encoding="utf-8")
        except Exception as e:
            print("An error occurred:\n%s" % (e))
            # raise e
        finally:
            pass
