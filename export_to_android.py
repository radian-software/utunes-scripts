#!/usr/bin/env python3

import json
import operator
import os
import pathlib
import shutil
import subprocess
import sys


THIS_DIR = pathlib.Path(__file__).parent
LIBRARY_FILE = THIS_DIR / "utunes.json"
MUSIC_DIR = THIS_DIR / "music"
PLAYLISTS_DIR = THIS_DIR / "playlists"
RCLONE_MUSIC_DIR = "drive:music/music"


def step(name):
    print(name, file=sys.stderr)


def main():
    step("Read library database")
    with open(LIBRARY_FILE) as f:
        library = json.load(f)
    step("Synchronize music files to Google Drive")
    subprocess.run(
        ["rclone", "sync", "--transfers=32", "--verbose", MUSIC_DIR, RCLONE_MUSIC_DIR]
    )


if __name__ == "__main__":
    main()
