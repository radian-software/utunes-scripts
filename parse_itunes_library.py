#!/usr/bin/env python3

import argparse
import json
import pathlib
import plistlib
import sys


def main():
    this_dir = pathlib.Path(__file__).resolve().parent
    itunes_dir = this_dir.parent / "iTunes"
    itunes_music_dir = itunes_dir / "iTunes Media" / "Music"
    fname = itunes_dir / "iTunes Music Library.xml"
    with open(fname, "rb") as f:
        plist = plistlib.load(f)
    songs = {}
    for track_id, track in plist["Tracks"].items():
        last_play = track.get("Play Date UTC")
        if last_play:
            last_play = last_play.isoformat()
        songs[track_id] = {
            "play_count": track.get("Play Count", 0),
            "last_play": last_play,
            "filename": track["Location"],
        }
    playlists = {}
    for playlist in plist["Playlists"]:
        playlist_songs = []
        for entry in playlist.get("Playlist Items", []):
            playlist_songs.append(entry["Track ID"])
        if not playlist_songs:
            continue
        playlists[playlist["Name"]] = playlist_songs
    json.dump({
        "songs": songs,
        "playlists": playlists,
    }, sys.stdout, indent=2)
    print()
    sys.exit(0)


if __name__ == "__main__":
    main()
