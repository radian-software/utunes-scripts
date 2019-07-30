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
EXPORT_DIR = THIS_DIR / "export"
EXPORT_MUSIC_DIR = EXPORT_DIR / "music"
EXPORT_PLAYLISTS_DIR = EXPORT_DIR / "playlists"


LIBRARY_FRACTION_EXPORTED = 0.1
ANDROID_MUSIC_SUBDIR = pathlib.Path("primary/raxod502/music")


def step(name):
    print(name, file=sys.stderr)


def get_exported_songs(library):
    def sort_key(song):
        try:
            return int(song.get("play_count"))
        except ValueError:
            return 0

    songs = list(library["songs"].values())
    songs.sort(key=sort_key, reverse=True)
    num_exported = int(len(songs) * LIBRARY_FRACTION_EXPORTED)
    return songs[:num_exported]


def hardlink_song(song):
    orig_fname = MUSIC_DIR / song["filename"]
    exported_fname = EXPORT_MUSIC_DIR / song["filename"]
    exported_fname.parent.mkdir(parents=True, exist_ok=True)
    os.link(orig_fname, exported_fname)


def get_android_id():
    return (
        subprocess.run(["kdeconnect-cli", "-a", "--id-only"], stdout=subprocess.PIPE)
        .stdout.strip()
        .decode()
    )


def get_android_mount_point(android_id):
    return pathlib.Path("/run/user/{}/{}".format(os.getuid(), android_id))


def sync_to_android(directory):
    assert directory.is_dir()
    subprocess.run(
        ["rsync", "-aPh", "--delete", str(EXPORT_DIR) + "/", str(directory) + "/"]
    )


def main():
    step("Delete existing export directory")
    try:
        shutil.rmtree(EXPORT_DIR)
    except FileNotFoundError:
        pass
    step("Read library database")
    with open(LIBRARY_FILE) as f:
        library = json.load(f)
    step("Filter library")
    songs = get_exported_songs(library)
    step("Hard-link selected music")
    for song in songs:
        hardlink_song(song)
    step("Locate Android filesystem mount point")
    android_id = get_android_id()
    mount_point = get_android_mount_point(android_id)
    step("Synchronize music files to Android filesystem")
    sync_to_android(mount_point / ANDROID_MUSIC_SUBDIR)


if __name__ == "__main__":
    main()
