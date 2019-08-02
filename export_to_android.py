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
RCLONE_DIR = "drive:music"
RCLONE_MUSIC_SUBDIR = "music"
RCLONE_PLAYLISTS_SUBDIR = "playlists"


def step(name):
    print(name, file=sys.stderr)


def main():
    step("Read library database")
    with open(LIBRARY_FILE) as f:
        library = json.load(f)
    step("Generate M3U playlists")
    shutil.rmtree(PLAYLISTS_DIR, ignore_errors=True)
    PLAYLISTS_DIR.mkdir(parents=True)
    for playlist_name, song_ids in library["playlists"].items():
        # Blind trust in my ability to make playlist names that aren't
        # malicious.
        playlist_name = playlist_name.replace("/", "-")
        playlist_file = PLAYLISTS_DIR / (playlist_name + ".m3u")
        with open(playlist_file, "w") as f:
            for sid in song_ids:
                song = library["songs"][sid]
                filename = song["filename"]
                f.write(str(filename))
                f.write("\n")
    step("Synchronize playlist files to Google Drive")
    subprocess.run(
        [
            "rclone",
            "sync",
            "--transfers=32",
            "--verbose",
            PLAYLISTS_DIR,
            RCLONE_DIR + "/" + RCLONE_PLAYLISTS_SUBDIR,
        ]
    )
    step("Synchronize music files to Google Drive")
    subprocess.run(
        [
            "rclone",
            "sync",
            "--transfers=32",
            "--verbose",
            MUSIC_DIR,
            RCLONE_DIR + "/" + RCLONE_MUSIC_SUBDIR,
        ]
    )


if __name__ == "__main__":
    main()
