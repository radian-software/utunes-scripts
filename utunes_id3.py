import argparse
import json
import re
import sys
import tempfile

import mutagen.easyid3
import mutagen.mp3


COMMENT_FIELDS_HAVE_ARGUMENT = {
    "Inherit": False,
    "Group": True,
    "Free": False,
    "Paid": True,
    "Min": True,
    "Pirated": False,
    "Donated": True,
    "Bundle": True,
    "Gift": True,
    "Artwork": False,
    "Copyedited": False,
    "Renamed": False,
    "Reordered": False,
    "Combined": False,
    "Trimmed": False,
    "Transcoded": False,
    "Cut": False,
    "Handled": False,
    "Tag2": False,
    "Date": True,
    "Estimate": False,
    "Upstream": True,
    "Source": True,
    "Tracklist": True,
    "Bypass": True,
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
        if COMMENT_FIELDS_HAVE_ARGUMENT[key]:
            assert val is not None, "field {} should have arg".format(key)
        else:
            assert val is None, "field {} shouldn't have arg".format(key)
    return tags


def yesno(b):
    return "yes" if b else "no"


def read_file(path):
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
