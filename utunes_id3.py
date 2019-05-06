import argparse
import json
import re
import sys
import tempfile

import mutagen.easyid3
import mutagen.mp3


def read_file(path):
    m_easy = mutagen.easyid3.EasyID3(path)
    album, = m_easy["album"]
    song, = m_easy["title"]
    track_str, = m_easy["tracknumber"]
    match = re.match(r"[0-9]+", track_str)
    assert match, "malformed or missing track data: {}".format(track_str)
    track = match.group(0)
    disc_str, = m_easy["discnumber"]
    match = re.match(r"[0-9]+", disc_str)
    assert match, "malformed or missing disc data: {}".format(disc_str)
    disc = match.group(0)
    artist, = m_easy["artist"] or m_easy["albumartist"]
    album_artist, = m_easy["albumartist"] or m_easy["artist"]
    composer, = m_easy.get("composer")
    year, = m_easy.get("date")
    album_sort, = m_easy.get("albumsort") or (album,)
    song_sort, = m_easy.get("titlesort") or (song,)
    artist_sort, = m_easy.get("artistsort") or (artist,)
    album_artist_sort, = m_easy.get("albumartistsort") or (album_artist,)
    composer_sort, = m_easy.get("composersort") or (composer,)
    # TODO: handle comments
    m_full = mutagen.mp3.MP3(path)
    apic, = m_full.tags.getall("APIC")
    match = re.fullmatch(r"image/([a-z]+)", apic.mime)
    ext = "." + match.group(1)
    with tempfile.NamedTemporaryFile("wb", delete=False, suffix=ext) as f:
        f.write(apic.data)
    artwork = f.name
    return {
        "_artwork": artwork,
        "_album": album,
        "_song": song,
        "_track": track,
        "_disc": disc,
        "artist": artist,
        "album_artist": album_artist,
        "composer": composer,
        "year": year,
        "album_sort": album_sort,
        "song_sort": song_sort,
        "artist_sort": artist_sort,
        "album_artist_sort": album_artist_sort,
        "composer_sort": composer_sort,
    }


def write_file(data, path):
    assert False, "not yet implemented"


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--read", metavar="FILE", default=None)
    group.add_argument("--write", metavar="FILE", default=None)
    args = parser.parse_args()
    if args.read is not None:
        data = read_file(args.read)
        json.dump(data, sys.stdout, indent=2)
        print()
    elif args.write is not None:
        data = json.load(sys.stdin)
        write_file(data, args.write)
    else:
        assert False
    sys.exit(0)


if __name__ == "__main__":
    main()
