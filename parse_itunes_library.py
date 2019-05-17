import json
import pathlib
import plistlib
import sys


def track_path(track):
    pass


def main():
    global fname
    itunes_dir = pathlib.Path.home() / "files" / "music" / "iTunes"
    itunes_music_dir = itunes_dir / "iTunes Media" / "Music"
    fname = itunes_dir / "iTunes Music Library.xml"
    with open(fname, "rb") as f:
        plist = plistlib.load(f)
    songs = {}
    for track in plist["Tracks"]:
        songs[track["Location"]] = {
            "play_count": track["Play Count"],
            "last_play": track["Play Date UTC"],
        }
    playlists = {}
    for playlist in plist["Playlists"]:
        playlist_songs = []
        for entry in playlist["Playlist Items"]:
            playlist_songs.append(plist["Tracks"][entry["Track ID"]])
        playlists[playlist["Name"]] = playlist_songs
    json.dump(sys.stdout, {
        "songs": songs,
        "playlists": playlists,
    })
    print()
    # sys.exit(0)


if __name__ == "__main__":
    main()
