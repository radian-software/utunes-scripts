import argparse
import atexit
import base64
import functools
import glob
import hashlib
import json
import os
import pathlib
import re
import readline
import shlex
import shutil
import subprocess
import sys
import tempfile
import traceback
import uuid

import mutagen.easyid3
import mutagen.mp3
import tabulate


def log(fmt, *args, **kwargs):
    print("import_album.py:", fmt.format(*args, **kwargs), file=sys.stderr)


def die(fmt, *args, **kwargs):
    log(fmt, *args, **kwargs)
    sys.exit(1)


def get_env_cmd(var, default):
    return shlex.split(os.environ.get(var, default))


def run_pager(text):
    result = subprocess.run(
        get_env_cmd("PAGER", "less -RS"), input=text, encoding="utf-8"
    )
    if result.returncode != 0:
        print("pager returned error {}".format(result.returncode))


def run_editor(text):
    with tempfile.NamedTemporaryFile("w+") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
        result = subprocess.run(get_env_cmd("EDITOR", "nano") + [f.name])
        if result.returncode != 0:
            print("editor returned error {}".format(result.returncode))
            return None
        f.seek(0)
        return f.read()


def safe_input(*args, **kwargs):
    try:
        return input(*args, **kwargs)
    except EOFError:
        print()
        sys.exit(0)


def disambiguate(options, filename):
    if not options:
        return ""
    options = sorted(options)
    if len(options) == 1 or True:  # FIXME, hack
        return options[0]
    print("[{}]".format(filename))
    for idx, option in enumerate(options, start=1):
        print("  {}. {}".format(idx, option))
    while True:
        try:
            choice = int(safe_input("> "))
        except ValueError:
            continue
        if choice < 1 or choice > len(options):
            continue
        return options[choice - 1]


def yesno(prompt):
    while True:
        ans = safe_input(prompt + " []").lower()
        if ans[0] == "y":
            return True
        if ans[0] == "n":
            return False


def extract_metadata(filename, artwork_db):
    m_easy = mutagen.easyid3.EasyID3(filename)
    m_full = mutagen.mp3.MP3(filename)
    album = disambiguate(m_easy["album"], filename)
    song = disambiguate(m_easy["title"], filename)
    track = disambiguate(
        {re.sub(r"/.*", "", s) for s in m_easy.get("tracknumber") or ()}, filename
    )
    disc = disambiguate(m_easy.get("discnumber"), filename)
    artist_raw = disambiguate(m_easy.get("artist"), filename)
    album_artist_raw = disambiguate(m_easy.get("albumartist"), filename)
    artist = artist_raw or album_artist_raw
    album_artist = album_artist_raw or artist_raw
    composer = disambiguate(m_easy.get("composer"), filename)
    year = disambiguate(m_easy.get("date"), filename)
    apics = m_full.tags.getall("APIC")
    digests = []
    for apic in apics:
        digest = hashlib.md5(apic.data).hexdigest()
        match = re.fullmatch(r"image/([a-z]+)", apic.mime)
        extension = "." + match.group(1)
        artwork_db[digest] = {
            "data": apic.data,
            "ext": extension,
        }
        digests.append(digest)
    data = {
        # Stuff we get from ID3
        "artwork": digest,
        "album": album,
        "song": song,
        "track": track,
        "disc": disc,
        "artist": artist,
        "album_artist": album_artist,
        "composer": composer,
        "year": year,
        "filename": filename,
        # Stuff we need to add
        "song_sort": "",
        "album_sort": "",
        "artist_sort": "",
        "composer_sort": "",
        "acquired_legally": "",
        "acquired_illegally": "",
        "as_bundle": "",
        "as_gift": "",
        "group": "",
        "paid": "",
        "min_paid": "",
        "date": "",
        "source": "",
        "tracklist": "",
        "refined_source": "",
    }
    if "|" in json.dumps(data):
        die("song metadata contains pipe character")
    return data


def fplural(num):
    return num, "s" if num != 1 else ""


def describe_field_values(values):
    if len(values) > 1 and not values[0]:
        desc = values[1]
    else:
        desc = values[0] or "-"
    if len(values) > 1:
        extra = " and {} more value{}".format(*fplural(len(values) - 1))
        desc = "[{}]".format(desc)
    else:
        extra = ""
    return desc, extra


def pseudonumeric_sort_key(x):
    if not x:
        return (2,)
    try:
        return (0, int(x))
    except ValueError:
        return (1, x)


def import_album(root_dir):
    filenames = sorted(glob.glob(str(root_dir / "**/*.mp3"), recursive=True))
    artwork_db = {}
    artwork_map = {}
    songs = [extract_metadata(fname, artwork_db) for fname in filenames]
    if not songs:
        log("no songs to import")
        return
    first_run = True
    while True:
        try:
            all_fields = {field for song in songs for field in song}
            field_values = {
                field: sorted(
                    {song[field] for song in songs}, key=pseudonumeric_sort_key
                )
                for field in all_fields
            }
            if first_run:
                cmd = "help"
                first_run = False
            else:
                cmdline = safe_input("> ")
                if not cmdline or cmdline.isspace():
                    continue
                cmd, *args = shlex.split(cmdline)
            if "quit".startswith(cmd):
                break
            elif "help".startswith(cmd):
                print(
                    tabulate.tabulate(
                        [
                            [field, *describe_field_values(field_values[field])]
                            for field in sorted(all_fields)
                        ]
                    )
                )
                print(
                    tabulate.tabulate(
                        [
                            ["help", "show this information"],
                            [
                                "values [FIELD...]",
                                "show distinct field values in pager",
                            ],
                            ["table [FIELD...]", "show field information in pager"],
                            ["sort FIELD...", "sort lexiocographically by fields"],
                            ["set FIELD VAL", "set a field for every song"],
                            ["su", "set all unset fields"],
                            [
                                "edit [FIELD...]",
                                "open your favorite editor on given fields",
                            ],
                            ["open [DIGEST...]", "open artwork using xdg-open"],
                            ["read [FILE]", "read artwork from clipboard or file"],
                            ["map DIGEST FNAME", "map artwork in db to relative path"],
                            [
                                "go",
                                "import the music, write changes to disk using µTunes",
                            ],
                            ["showmap", "show artwork map"],
                            ["dump", "write current import state to disk"],
                            ["load", "read current import state from disk"],
                            ["quit", "exit program"],
                        ],
                        tablefmt="plain",
                    )
                )
            elif "values".startswith(cmd):
                fields = args or sorted(
                    [field for field in all_fields if len(field_values[field]) > 1]
                )
                bad = False
                for field in fields:
                    if field not in all_fields:
                        print("not a valid field: {}".format(field))
                        bad = True
                        break
                if bad:
                    continue
                parts = []
                for field in fields:
                    lines = []
                    lines.append("{}:".format(field))
                    for value in field_values[field]:
                        lines.append("  {}".format(value or "-"))
                    parts.append("\n".join(lines))
                run_pager("\n\n".join(parts))
            elif "table".startswith(cmd):
                fields = args or sorted(all_fields)
                bad = False
                for field in fields:
                    if field not in all_fields:
                        print("not a valid field: {}".format(field))
                        bad = True
                        break
                if bad:
                    continue
                text = (
                    tabulate.tabulate(
                        [[song[field] for field in fields] for song in songs],
                        headers=fields,
                    )
                    + "\n"
                )
                run_pager(text)
            elif "sort".startswith(cmd):  # FIXME accept any number of arguments
                if not args:
                    print("needs at least one argument")
                    continue
                fields = args
                bad = False
                for field in fields:
                    if field not in all_fields:
                        print("not a valid field: {}".format(field))
                        bad = True
                        break
                if bad:
                    continue
                songs.sort(
                    key=lambda song: [
                        pseudonumeric_sort_key(song[field]) for field in fields
                    ]
                )
            elif "set".startswith(cmd):
                if len(args) != 2:
                    print("needs exactly two arguments")
                    continue
                field, value = args
                if field not in all_fields:
                    print("not a valid field: {}".format(field))
                    continue
                if value == "-":
                    value = ""  # hyphen is easier to type
                for song in songs:
                    song[field] = value
            elif "su".startswith(cmd):
                for field in sorted(all_fields):
                    if field_values[field] == [""]:
                        value = safe_input("value for {}: ".format(field))
                        if value.isspace():
                            continue
                        if value == "-":
                            value = ""
                        for song in songs:
                            song[field] = value
            elif "edit".startswith(cmd):
                fields = args or sorted(all_fields)
                bad = False
                for field in fields:
                    if field not in all_fields:
                        print("not a valid field: {}".format(field))
                        bad = True
                        break
                    for song in songs:
                        if "|" in song[field]:
                            die("song metadata contains a pipe character")
                if bad:
                    continue
                text_in = (
                    tabulate.tabulate(
                        [
                            ["{}: {}".format(field, song[field]) for field in fields]
                            for song in songs
                        ],
                        tablefmt="github",
                    )
                    # break string to avoid confusing Emacs
                    + "\nLocal"
                    + " Variables:\nmode: markdown\ntruncate-lines: t\nEnd:"
                )
                text_out = run_editor(text_in)
                # If fields have special chars in them, we're screwed.
                # This script isn't for public use so let's not bother
                # handling it.
                matches = list(
                    re.finditer(
                        r"^\s*\|\s*{}\s*\|\s*$".format(
                            r"\s*\|\s*".join(
                                r"{0}:\s*(?P<{0}>[^|]*?)".format(field)
                                for field in fields
                            )
                        ),
                        text_out,
                        re.MULTILINE,
                    )
                )
                if len(matches) != len(songs):
                    with tempfile.NamedTemporaryFile("w", delete=False) as f:
                        f.write(text_out)
                    print("malformed table, ignoring (wrote to {})".format(f.name))
                    continue
                songs = [
                    {**song, **match.groupdict()} for song, match in zip(songs, matches)
                ]
            elif "open".startswith(cmd):
                digests = args or sorted(artwork_db.keys())
                bad = False
                for digest in digests:
                    if digest not in artwork_db:
                        print("no such artwork in memory: {}".format(digest))
                        bad = True
                        break
                if bad:
                    continue
                for digest in digests:
                    if "fptr" in artwork_db[digest]:
                        artwork_db[digest]["fptr"].close()
                    fptr = tempfile.NamedTemporaryFile(
                        "wb", suffix="." + digest + artwork_db[digest]["ext"],
                    )
                    artwork_db[digest]["file"] = fptr
                    fptr.write(artwork_db[digest]["data"])
                    fptr.flush()
                    os.fsync(fptr.fileno())
                for digest in digests:
                    subprocess.Popen(
                        ["xdg-open", artwork_db[digest]["file"].name],
                        stderr=subprocess.DEVNULL,
                    )
            elif "read".startswith(cmd):
                if len(args) > 1:
                    print("needs zero or one arguments")
                    continue
                if len(args) >= 1:
                    fname = args[0]
                    try:
                        with open(fname, "rb") as f:
                            data = f.read()
                    except OSError as e:
                        print("failed to read file: {}".format(e))
                        continue
                else:
                    try:
                        result = subprocess.run(
                            [
                                "xclip",
                                "-o",
                                "-selection",
                                "clipboard",
                                "-t",
                                "image/png",
                            ],
                            stdout=subprocess.PIPE,
                            check=True,
                        )
                        data = result.stdout
                    except (OSError, subprocess.CalledProcessError) as e:
                        print("failed to read clipboard: {}".format(e))
                        continue
                digest = hashlib.md5(data).hexdigest()
                if digest in artwork_db:
                    print("digest already exists: {}".format(digest))
                    continue
                artwork_db[digest] = {"data": data, "ext": ".png"}
                print("imported artwork, digest: {}".format(digest))
            elif "map".startswith(cmd):
                if len(args) != 2:
                    print("needs exactly two arguments")
                    continue
                digest, fname = args
                if digest not in artwork_db:
                    print("digest not in memory: {}".format(digest))
                    continue
                if "/" in fname:
                    print("full paths are not allowed in filename: {}".format(fname))
                    continue
                if fname == "-":
                    artwork_map.pop(digest)
                else:
                    artwork_map[digest] = fname
            elif "showmap".startswith(cmd):
                for digest, fname in artwork_map.items():
                    print(digest, fname)
            elif "dump".startswith(cmd):
                try:
                    try:
                        shutil.copyfile(".import_state.json", ".import_state.json.bak")
                    except OSError:
                        pass
                    with open(".import_state.json", "w") as f:
                        json.dump(
                            {
                                "songs": songs,
                                "artwork_db": {
                                    digest: {
                                        "data": base64.encodebytes(
                                            art["data"]
                                        ).decode(),
                                        "ext": art["ext"],
                                    }
                                    for digest, art in artwork_db.items()
                                },
                                "artwork_map": artwork_map,
                            },
                            f,
                        )
                except OSError as e:
                    print("failed to dump state: {}".format(e))
                    continue
                print("dumped state to .import_state.json")
            elif "load".startswith(cmd):
                try:
                    with open(".import_state.json") as f:
                        state = json.load(f)
                        songs = state["songs"]
                        artwork_db = {
                            digest: {
                                "data": base64.decodebytes(art["data"].encode()),
                                "ext": art["ext"],
                            }
                            for digest, art in state["artwork_db"].items()
                        }
                        artwork_map = state["artwork_map"]
                except OSError as e:
                    print("failed to load state: {}".format(e))
                    continue
                print("loaded state from .import_state.json")
            elif "go".startswith(cmd):
                time_uuid = str(uuid.uuid1())
                final_songs = [
                    {
                        **song,
                        "artwork": artwork_map.get(song["artwork"], song["artwork"]),
                        "import_uuid": time_uuid,
                    }
                    for song in songs
                ]
                fields = sorted(all_fields) + ["import_uuid"]
                for digest, fname in artwork_map.items():
                    fpath = pathlib.Path(".") / "artwork" / fname
                    try:
                        try:
                            fpath.stat()
                        except FileNotFoundError:
                            pass
                        else:
                            if not yesno("overwrite {}?".format(fname)):
                                continue
                    except OSError as e:
                        print("failed to write artwork: {}".format(e))
                        continue
                lines = []
                for song in final_songs:
                    for field in fields:
                        if "|" in song[field]:
                            die("song metadata contains pipe character")
                    lines.append("|".join(song[field] for field in fields) + "\n")
                regex = (
                    r"\|".join(r"(P<{}>[^|]*)".format(field) for field in fields)
                    + r"\n"
                )
                print(regex)
                print("".join(lines))
                # result = subprocess.run(
                #     ["utunes", "write", regex], input="".join(lines)
                # )
                # if result.returncode != 0:
                #     print("µTunes returned error {}".format(result))
                #     continue
            else:
                print("no such command: {}".format(cmd))
                continue
        except KeyboardInterrupt:
            print("^C")
        except Exception:
            traceback.print_exc()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "directory", metavar="DIRECTORY", nargs="?", default=os.getcwd()
    )
    args = parser.parse_args()
    os.chdir(os.environ["UTUNES_LIBRARY"])
    histfile = ".import_history"
    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        pass
    atexit.register(readline.write_history_file, histfile)
    import_album(root_dir=pathlib.Path(args.directory))


if __name__ == "__main__":
    main()
