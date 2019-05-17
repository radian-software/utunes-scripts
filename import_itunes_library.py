#!/usr/bin/env python3

import argparse
import contextlib
import json
import pathlib
import plistlib
import random
import re
import sys
import urllib.parse

import mutagen.easyid3
import mutagen.mp3

THIS_DIR = pathlib.Path(__file__).resolve().parent
ITUNES_DIR = THIS_DIR.parent / "iTunes"
ITUNES_MUSIC_DIR = ITUNES_DIR / "iTunes Media" / "Music"
ARTWORK_DIR = THIS_DIR / "artwork"


@contextlib.contextmanager
def progress(msg):
    print(msg + "...", file=sys.stderr)
    yield None
    print("  done.", file=sys.stderr)


def parse_itunes_xml():
    fname = ITUNES_DIR / "iTunes Music Library.xml"
    with open(fname, "rb") as f:
        plist = plistlib.load(f)
    songs = {}
    for track_id, track in plist["Tracks"].items():
        last_play = track.get("Play Date UTC")
        if last_play:
            last_play = last_play.isoformat()
        location = urllib.parse.unquote(track["Location"])
        match = re.fullmatch(
            r"file://.+?iTunes Media/Music/(.+)",
            location)
        if not match:
            continue
        filename, = match.groups()
        songs[track_id] = {
            "play_count": track.get("Play Count", 0),
            "last_play": last_play,
            "filename": str(ITUNES_MUSIC_DIR / filename),
        }
    assert len(songs) >= 5000
    playlists = {}
    for playlist in plist["Playlists"]:
        playlist_songs = []
        for entry in playlist.get("Playlist Items", []):
            playlist_songs.append(entry["Track ID"])
        if not playlist_songs:
            continue
        playlists[playlist["Name"]] = playlist_songs
    return {
        "songs": songs,
        "playlists": playlists,
    }


COMMENT_FIELDS_HAVE_ARGUMENT = {
    # Ones I still use.
    "Group": True,
    "Free": False,
    "Paid": True,
    "Min": True,
    "Pirated": False,
    "Donated": True,
    "Bundle": True,
    "Gift": True,
    "Tag2": False,
    "Date": True,
    "Upstream": True,
    "Source": True,
    "Tracklist": True,
    "Bypass": True,
    # For backwards compatibility.
    "Inherit": False,
    "Artwork": False,
    "Copyedited": False,
    "Renamed": False,
    "Reordered": False,
    "Combined": False,
    "Trimmed": False,
    "Transcoded": False,
    "Cut": False,
    "Handled": False,
    "Estimate": False,
    "Multiple": False,
}


def parse_comments(comments):
    header, *longfields = comments.splitlines()
    assert header.startswith("\\") and header.endswith("\\")
    fields = header[1:-1].split("\\")
    tags = {}
    for field in fields:
        match = re.fullmatch(r"([^:]+)(?::(.+))?", field)
        assert match
        key, val = match.groups()
        assert key not in tags
        tags[key] = val
    for field in longfields:
        match = re.fullmatch(r"([^:]+): (.+)", field)
        assert match
        key, val = match.groups()
        assert key not in tags
        tags[key] = val
    for key, val in tags.items():
        assert key in COMMENT_FIELDS_HAVE_ARGUMENT, comments
        if COMMENT_FIELDS_HAVE_ARGUMENT[key]:
            assert val is not None, "field {} should have arg".format(key)
        else:
            assert val is None, "field {} shouldn't have arg".format(key)
    assert "Tag2" in tags
    return tags


def yesno(b):
    return "yes" if b else "no"


def read_file(path, artwork_cache={}):
    m_easy = mutagen.easyid3.EasyID3(path)
    m_full = mutagen.mp3.MP3(path)
    album, = m_easy["album"]
    song, = m_easy["title"]
    track_str, = m_easy.get("tracknumber") or (None,)
    if track_str:
        match = re.match(r"[0-9]+", track_str)
        assert match, "malformed or missing track data: {}".format(track_str)
        track = match.group(0)
    else:
        track = None
    disc_str, = m_easy["discnumber"]
    match = re.match(r"[0-9]+", disc_str)
    assert match, "malformed or missing disc data: {}".format(disc_str)
    disc = match.group(0)
    artist, = m_easy.get("artist") or m_easy("albumartist")
    album_artist, = m_easy.get("albumartist") or m_easy.get("artist")
    composer, = m_easy.get("composer") or (None,)
    year, = m_easy.get("date")
    album_sort, = m_easy.get("albumsort") or (album,)
    song_sort, = m_easy.get("titlesort") or (song,)
    artist_sort, = m_easy.get("artistsort") or (artist,)
    album_artist_sort, = m_easy.get("albumartistsort") or (album_artist,)
    composer_sort, = m_easy.get("composersort") or (composer,)
    comment_tags = m_full.tags.getall("COMM")
    relevant_comment_tags = [ct for ct in comment_tags if not ct.desc]
    assert len(relevant_comment_tags) == 1, \
        "unexpected comments: {}".format(comment_tags)
    comment_tag, = relevant_comment_tags
    comment_text, = comment_tag.text
    tags = parse_comments(comment_text)
    purchase_method_tags = (
        {"Free", "Paid", "Pirated", "Donated", "Bundle", "Gift"} & set(tags)
    )
    assert len(purchase_method_tags) == 1, comment_text
    purchase_method_tag, = purchase_method_tags
    acquired_legally = purchase_method_tag in ("Free", "Paid", "Bundle", "Gift")
    acquired_illegally = purchase_method_tag in ("Pirated", "Donated")
    as_bundle = purchase_method_tag == "Bundle"
    as_gift = purchase_method_tag == "Gift"
    paid = tags[purchase_method_tag]
    if paid:
        assert re.fullmatch(r"[0-9]+\.[0-9]{2}", paid), "Paid: {}".format(paid)
    min_price = tags.get("Min")
    if min_price:
        assert re.fullmatch(
            r"[0-9]+\.[0-9]{2}", min_price
        ), "Min: {}".format(min_price)
    date = tags["Date"]
    assert re.fullmatch("[0-9]{4}-[0-9]{2}-[0-9]{2}", date), "Date {}".format(date)
    tracklist = tags.get("Tracklist")
    if tracklist:
        assert re.match(r"https?://", tracklist)
    assert not ("Upstream" in tags and "Bypass" in tags)
    if "Upstream" in tags:
        source, refined_source = tags["Upstream"], tags["Source"]
    elif "Bypass" in tags:
        source, refined_source = tags["Source"], tags["Bypass"]
    else:
        source, refined_source = tags["Source"], None
    assert re.match(r"https?://", source)
    if refined_source:
        assert re.match(r"https?://", refined_source)
    group = tags.get("Group")
    apic, = m_full.tags.getall("APIC")
    match = re.fullmatch(r"image/([a-z]+)", apic.mime)
    ext = "." + match.group(1)
    artwork_fname = (
        ARTWORK_DIR / ("-".join(re.findall(r"[a-z0-9]+", album.lower())) + ext)
    )
    if album not in artwork_cache:
        if artwork_fname.is_file():
            with open(artwork_fname, "rb") as f:
                artwork_cache[album] = f.read()
            assert apic.data == artwork_cache[album]
        artwork_fname.parent.mkdir(exist_ok=True)
        with open(artwork_fname, "wb") as f:
            f.write(apic.data)
    artwork = artwork_fname.name
    return {
        "artwork": artwork,
        "album": album,
        "song": song,
        "track": track,
        "disc": disc,
        "artist": artist,
        "album_artist": album_artist,
        "composer": composer,
        "year": year,
        "album_sort": album_sort,
        "song_sort": song_sort,
        "artist_sort": artist_sort,
        "album_artist_sort": album_artist_sort,
        "composer_sort": composer_sort,
        "acquired_legally": yesno(acquired_legally),
        "acquired_illegally": yesno(acquired_illegally),
        "as_bundle": yesno(as_bundle),
        "as_gift": yesno(as_gift),
        "paid": paid,
        "min_price": min_price,
        "date": date,
        "source": source,
        "tracklist": tracklist,
        "refined_source": refined_source,
        "group": group,
    }


def read_songs(songs, itunes_data, random_order, starting_id3):
    itunes_songs = [{"itunes_id": iid, **isong}
                    for iid, isong in itunes_data["songs"].items()]
    if random_order:
        random.shuffle(itunes_songs)
    else:
        itunes_songs.sort(key=lambda s: s["filename"])
    if starting_id3:
        itunes_songs.sort(key=lambda s: int(s["itunes_id"]) != int(starting_id3))
    for itunes_song in itunes_songs:
        itunes_id = itunes_song["itunes_id"]
        if itunes_id in songs and itunes_id != starting_id3:
            continue
        filename = itunes_song["filename"]
        print("    {} {}".format(itunes_id.zfill(5), filename))
        song = read_file(filename)
        for key in ("itunes_id", "play_count", "last_play"):
            song[key] = itunes_song[key]
        songs[itunes_id] = song


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-xml", action="store_true")
    parser.add_argument("--force-id3", action="store_true")
    parser.add_argument("--random-id3", action="store_true")
    parser.add_argument("--starting-id3", default=None)
    args = parser.parse_args()
    itunes_json = THIS_DIR / "itunes.json"
    if args.force_xml or not itunes_json.is_file():
        with progress("Parsing iTunes XML"):
            itunes_data = parse_itunes_xml()
        with open(itunes_json, "w") as f:
            json.dump(itunes_data, f, indent=2)
            f.write("\n")
    else:
        with open(itunes_json) as f:
            itunes_data = json.load(f)
    songs_json = THIS_DIR / "songs.json"
    if args.force_id3 or not songs_json.is_file():
        songs = {}
    else:
        with open(songs_json) as f:
            songs = json.load(f)
    orig_len = len(songs)
    try:
        with progress("Reading song ID3 data"):
            read_songs(songs, itunes_data, random_order=args.random_id3,
                       starting_id3=args.starting_id3)
    finally:
        if len(songs) > orig_len:
            with open(songs_json, "w") as f:
                json.dump(songs, f, indent=2)
                f.write("\n")
    artworks = set()
    for artwork_fname in ARTWORK_DIR.iterdir():
        artwork = artwork_fname.stem
        assert artwork not in artworks, artwork
        artworks.add(artwork)


if __name__ == "__main__":
    main()
