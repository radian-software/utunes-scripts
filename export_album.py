import mimetypes
import os
import pathlib
import subprocess
import sys

import mutagen.easyid3
import mutagen.id3
import mutagen.mp3


FIELDS = {
    "song",
    "song_sort",
    "album",
    "album_sort",
    "album_artist",
    "album_artist_sort",
    "artist",
    "artist_sort",
    "composer",
    "composer_sort",
    "track",
    "disc",
    "year",
    "filename",
    "artwork",
    "source",
}


def export_query(args):
    fields = sorted(FIELDS)
    songs = [
        {field: value for field, value in zip(fields, line.split("|"))}
        for line in subprocess.run(
            [
                "utunes",
                "read",
                "|".join("{" + field + "}" for field in fields),
                "--illegal-chars",
                "|",
                *args,
            ],
            stdout=subprocess.PIPE,
            encoding="utf-8",
            check=True,
        ).stdout.splitlines()
    ]
    music_dir = pathlib.Path("music")
    artwork_dir = pathlib.Path("artwork")
    export_dir = pathlib.Path("export")
    for song in songs:
        print(song["filename"], file=sys.stderr)
        m_easy = mutagen.easyid3.EasyID3(music_dir / song["filename"])
        m_easy["title"] = song["song"]
        m_easy["titlesort"] = song["song_sort"]
        m_easy["album"] = song["album"]
        m_easy["albumsort"] = song["album_sort"]
        m_easy["albumartist"] = song["album_artist"]
        m_easy["albumartistsort"] = song["album_artist_sort"]
        m_easy["artist"] = song["artist"]
        m_easy["artistsort"] = song["artist_sort"]
        m_easy["composer"] = song["composer"]
        m_easy["composersort"] = song["composer_sort"]
        m_easy["tracknumber"] = song["track"]
        m_easy["discnumber"] = song["disc"]
        m_easy["date"] = song["year"]
        for key in ("bpm", "genre"):
            try:
                m_easy.pop(key)
            except KeyError:
                pass
        m_easy.save()
        m_full = mutagen.mp3.MP3(music_dir / song["filename"])
        m_full.tags.delall("COMM")
        m_full.tags.add(
            mutagen.id3.COMM(
                text="Exported from µTunes. Music sourced from:\n{}".format(
                    song["source"]
                ),
                # needed for iTunes to see comment:
                lang="eng",
            )
        )
        m_full.tags.delall("APIC")
        with open(artwork_dir / song["artwork"], "rb") as f:
            m_full.tags.add(
                mutagen.id3.APIC(
                    mime=mimetypes.guess_type(song["artwork"])[0],
                    data=f.read(),
                    # needed for iTunes to see artwork (yes, really):
                    type=mutagen.id3.PictureType.OTHER,
                    encoding=mutagen.id3.Encoding.LATIN1,
                )
            )
        m_full.save()
        (export_dir / song["filename"]).parent.mkdir(parents=True, exist_ok=True)
        try:
            os.unlink(export_dir / song["filename"])
        except FileNotFoundError:
            pass
        os.link(music_dir / song["filename"], export_dir / song["filename"])


def main():
    if len(sys.argv) <= 1:
        print("needs an argument (-f ...)", file=sys.stderr)
        sys.exit(1)
    if sys.argv[1] in ("-h", "--help", "-help", "help", "-?"):
        print("export_album.py: passes arguments to 'utunes read'", file=sys.stderr)
        sys.exit(0)
    if sys.argv[1] in ("-v", "--version", "-version", "version", "-V"):
        print("export_album.py: development version", file=sys.stderr)
        sys.exit(0)
    os.chdir(os.environ["UTUNES_LIBRARY"])
    export_query(sys.argv[1:])


if __name__ == "__main__":
    main()
