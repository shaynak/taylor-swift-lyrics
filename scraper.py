import argparse
import json
import lyricsgenius
import math
import pandas as pd
import re
import requests
from lyricsgenius.types import Song
from local import *

ALBUMS = [
    '1989', '1989 (Deluxe)', '2004-2005 Demo CD', 'Beautiful Eyes - EP',
    'Cats: Highlights From the Motion Picture Soundtrack', 'Fearless',
    'Fearless (Platinum Edition)',
    'Fifty Shades Darker (Original Motion Picture Soundtrack)',
    'Hannah Montana: The Movie', 'Lover',
    'One Chance (Original Motion Picture Soundtrack)', 'Red (Deluxe Edition)',
    'Speak Now', 'Speak Now (Deluxe)', 'Taylor Swift', 'Taylor Swift (Deluxe)',
    'The Hunger Games: Songs from District 12 and Beyond',
    'The Taylor Swift Holiday Collection - EP', 'Unreleased Songs',
    'Valentine’s Day (Original Motion Picture Soundtrack)', 'evermore',
    'evermore (deluxe version)', 'folklore', 'folklore (deluxe version)',
    'reputation', 'Uncategorized', ''
]

# Songs that don't have an album or for which Taylor Swift is not the primary artist
OTHER_SONGS = [
    'Only The Young',
    'Christmas Tree Farm',
    # 'Monologue Song (La La La)',
    'Ronan',
    "I Don't Wanna Live Forever",
]

ARTIST_ID = 1177
API_PATH = "https://api.genius.com"
ARTIST_URL = API_PATH + "/artists/" + str(ARTIST_ID)
CSV_PATH = 'songs.csv'
LYRIC_PATH = 'lyrics.csv'
LYRIC_JSON_PATH = 'lyrics.json'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--append', action='store_true')
    args = parser.parse_args()
    existing_df, existing_songs = None, []
    if args.append:
        existing_df = pd.read_csv(CSV_PATH)
        existing_songs = list(existing_df['Title'])
    genius = lyricsgenius.Genius(access_token)
    songs = get_songs(genius)
    songs_by_album = sort_songs_by_album(genius, songs, existing_songs)
    albums_to_songs_csv(songs_by_album, existing_df)
    songs_to_lyrics()
    lyrics_to_json()


def get_songs(genius):
    print('Getting songs...')
    songs = []
    next_page = 1
    while next_page != None:
        request_url = ARTIST_URL + "/songs?page=" + str(next_page)
        r = requests.get(request_url,
                         headers={'Authorization': "Bearer " + access_token})
        song_data = json.loads(r.text)
        songs.extend(song_data['response']['songs'])
        next_page = song_data['response']['next_page']
    return [
        song for song in songs
        if song['primary_artist']['id'] == ARTIST_ID or song in OTHER_SONGS
    ]


def sort_songs_by_album(genius, songs, existing_songs=[]):
    print('Sorting songs by album...')
    songs_by_album = {}
    for song in songs:
        lyrics = None
        if song['title'] not in existing_songs:
            try:
                request_url = API_PATH + song['api_path']
                r = requests.get(
                    request_url,
                    headers={'Authorization': "Bearer " + access_token})
                song_data = json.loads(r.text)['response']['song']
                if 'album' in song_data and song_data[
                        'lyrics_state'] == 'complete':
                    album_name = song_data['album']['name'].strip(
                    ) if song_data['album'] else None
                    # Handle special cases -- uncategorized songs are under "Taylor Swift " on Genius
                    if album_name == "Taylor Swift" and album_name != song_data[
                            'album']['name']:
                        album_name = "Uncategorized"
                    if album_name is None:
                        album_name = ""
                    lyrics = genius.lyrics(song_data['url'])
                    if lyrics and has_song_identifier(lyrics) and (
                            album_name or song['title'] in OTHER_SONGS):
                        lyrics = clean_lyrics(lyrics)
                        s = Song(genius, song_data, lyrics)
                        if album_name not in songs_by_album:
                            songs_by_album[album_name] = []
                        songs_by_album[album_name].append(s)
            except requests.exceptions.Timeout:
                print('Failed receiving song', song['title'],
                      '-- saving songs so far')
                return songs_by_album
    return songs_by_album


def albums_to_songs_csv(songs_by_album, existing_df=None):
    print('Saving songs to CSV...')
    songs_records = []
    for album in songs_by_album:
        if album in ALBUMS:
            for song in songs_by_album[album]:
                record = {
                    'Title': song.title,
                    'Album': album,
                    'Lyrics': song.lyrics,
                }
                songs_records.append(record)

    song_df = pd.DataFrame.from_records(songs_records)
    if existing_df is not None:
        song_df = pd.concat([existing_df, song_df])
    song_df.to_csv(CSV_PATH, index=False)


def has_song_identifier(lyrics):
    if lyrics[:len('[Intro')] == '[Intro':
        return True
    elif lyrics[:len('[Verse')] == '[Verse':
        return True
    elif lyrics[:len('[Chorus')] == '[Chorus':
        return True
    return False


class Lyric:
    def __init__(self, lyric, prev_lyric=None, next_lyric=None):
        self.lyric = lyric
        self.prev = prev_lyric
        self.next = next_lyric

    def __eq__(self, other):
        return self.lyric == other.lyric and self.prev == other.prev and self.next == other.next

    def __repr__(self):
        return self.lyric

    def __hash__(self):
        return hash((self.prev or "") + self.lyric + (self.next or ""))


def songs_to_lyrics():
    print('Generating lyrics CSV...')
    song_data = pd.read_csv(CSV_PATH)
    lyric_records = []
    for song in song_data.to_records(index=False):
        title, album, lyrics = song
        lyric_dict = get_lyric_list(lyrics)
        for lyric in lyric_dict:
            lyric_record = {
                'Song': title,
                'Album': album,
                'Lyric': lyric.lyric,
                'Previous Lyric': lyric.prev,
                'Next Lyric': lyric.next,
                'Multiplicity': lyric_dict[lyric]
            }
            lyric_records.append(lyric_record)
    lyric_df = pd.DataFrame.from_records(lyric_records)
    lyric_df.to_csv(LYRIC_PATH, index=False)


def get_lyric_list(lyrics):
    line = None
    lines = lyrics.split('\n')
    lyric_dict = {}
    for i in range(len(lines)):
        if len(lines[i]) > 0 and lines[i][0] != '[':
            prev_line = line
            line = lines[i]
            next_line = lines[
                i + 1] if i + 1 < len(lines) and lines[i + 1] != '[' else None
            lyric = Lyric(line, prev_line, next_line)
            if lyric not in lyric_dict:
                lyric_dict[lyric] = 1
            else:
                lyric_dict[lyric] = lyric_dict[lyric] + 1
    return lyric_dict


def lyrics_to_json():
    print('Generating lyrics JSON...')
    lyric_dict = {}
    lyric_data = pd.read_csv(LYRIC_PATH)
    for lyric in lyric_data.to_records(index=False):
        title, album, lyric, prev_lyric, next_lyric, multiplicity = lyric
        if album not in lyric_dict:
            lyric_dict[album] = {}
        if title not in lyric_dict[album]:
            lyric_dict[album][title] = []
        lyric_dict[album][title].append({
            'lyric':
            lyric,
            'prev':
            "" if prev_lyric != prev_lyric else prev_lyric,  # replace NaN
            'next':
            "" if next_lyric != next_lyric else next_lyric,
            'multiplicity':
            int(multiplicity),
        })
    lyric_json = json.dumps(lyric_dict, indent=4)
    with open(LYRIC_JSON_PATH, 'w') as f:
        f.write(lyric_json)
        f.close()


def clean_lyrics(lyrics):
    # Replace special quotes with normal quotes
    lyrics = re.sub(r'\u2018|\u2019', "'", lyrics)
    lyrics = re.sub(r'\u201C|\u201D', '"', lyrics)
    # Replace special unicode spaces with standard space
    lyrics = re.sub(
        r'[\u00A0\u1680​\u180e\u2000-\u2009\u200a​\u200b​\u202f\u205f​\u3000]',
        " ", lyrics)
    # Replace dashes with space and single hyphen
    lyrics = re.sub(r'\u2013|\u2014', " - ", lyrics)
    return lyrics


if __name__ == '__main__':
    main()
