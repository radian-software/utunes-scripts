# µTunes library

* To download a Spotify album: <https://spotdl.com/>
* To download from YouTube: <https://ytdl-org.github.io/youtube-dl/>
* To transcode files to MP3: ???
* To trim MP3 files: ???

Tags:
* Basic track information
    * `song`: name of the track
        * `song_sort`: alternate track name that's more friendly for
          sorting
    * `album`: name of the album
        * `album_sort`: alternate album name that's more friendly for
          sorting
    * `album_artist`: the person or group responsible for the album,
      optimized for grouping albums
        * `album_album_sort`: alternate album artist name that's more
          friendly for sorting
    * `artist`: the artist for the specific track, usually same as
      album artist
        * `artist_sort`: alternate track artist name that's more
          friendly for sorting
    * `composer`: the composer of the specific track, or omitted
        * `composer_sort`: alternate composer name that's more
          friendly for sorting
    * `track`: sequential number of the track (should be positive
      integer or omitted)
    * `disc`: sequential number of the disk (should be positive
      integer, use 1 if no discs)
    * `year`: four-digit year of publication of the music
* µTunes data
    * `id`: eight-digit hex string used as unique identifier for song,
      assigned by µTunes automatically and used as primary key
    * `filename`: path on disk (used for import, then managed
      automatically)
    * `artwork`: path of the album artwork (not actually used by
      µTunes, but I think of it that way; relative to `artwork`
      directory)
    * `last_play`: timestamp of last time song was played, in ISO8601
      format (e.g. `2019-05-15T19:40:29`)
    * `play_count`: number of times the song has been played,
      non-negative integer
* Source information
    * `acquired_legally`: `yes` or `no`, was part of the album purchased
      or downloaded for free from an official distributor
    * `acquired_illegally`: `yes` or `no`, was part of the album obtained
      without the permission of an official distributor (if the album is
      pirated from a different source after being purchased, this doesn't
      count)
    * `as_bundle`: `yes` or `no`, was obtained as part of a larger
      non-music purchase
    * `as_gift`: `yes` or `no`, was given as a gift (should still
      include pricing information)
    * `group`: used to separate a single album into multiple groups
      whose source information should be considered as separate, or to
      join parts of different albums together (either omitted to
      assume default album grouping, or a random unique eight-digit
      hex string)
    * `paid`: amount of money that was paid for the song in USD, in
      `XX.YY` format (`0.00` if pirated)
        * `min_paid`: minimum purchase requirement (for Bandcamp etc.)
    * `date`: when the album was added to my library (or downloaded,
      if there was a delay), in `YYYY-MM-DD` format
    * `source`: URL of website that the download or purchase came from
    * `tracklist`: URL of website with canonical tracklist, if I had
      to rename all the tracks
    * `refined_source`: if I purchased the album and then needed to
      pirate a better-tagged version of it from somewhere else, a URL
      for the secondary source
