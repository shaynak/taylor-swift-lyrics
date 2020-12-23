import argparse
import json
import lyricsgenius
import pandas as pd
import requests
from lyricsgenius.types import Song
from local import *

ALBUMS = ['1989', '1989 (Deluxe)', 'Beautiful Eyes - EP', 'Cats: Highlights From the Motion Picture Soundtrack', 
    'Fearless', 'Fearless (Platinum Edition)', 'Hannah Montana: The Movie', 'Lover', 
    'One Chance (Original Motion Picture Soundtrack)', 'Red (Deluxe Edition)', 'Speak Now', 'Speak Now (Deluxe)', 
    'Taylor Swift', 'Taylor Swift (Deluxe)', 'The Hunger Games: Songs from District 12 and Beyond', 
    'The Taylor Swift Holiday Collection - EP', 'Unreleased Songs', 'Valentine’s Day (Original Motion Picture Soundtrack)', 
    'evermore', 'evermore (deluxe version)', 'folklore', 'folklore (deluxe version)', 'reputation']

ARTIST_ID = 1177
API_PATH = "https://api.genius.com"
ARTIST_URL = API_PATH + "/artists/" + str(ARTIST_ID)
CSV_PATH = 'songs.csv'

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

def get_songs(genius):
    print('Getting songs...')
    songs = []
    next_page = 1
    while next_page != None:
        request_url = ARTIST_URL + "/songs?page=" + str(next_page)
        r = requests.get(request_url, headers={'Authorization': "Bearer " + access_token})
        song_data = json.loads(r.text)
        songs.extend(song_data['response']['songs'])
        next_page = song_data['response']['next_page']

    return [song for song in songs if song['primary_artist']['id'] == ARTIST_ID]

def sort_songs_by_album(genius, songs, existing_songs=[]):
    print('Sorting songs by album...')
    songs_by_album = {}
    for song in songs:
        if song['title'] not in existing_songs:
            try:
                request_url = API_PATH + song['api_path']
                r = requests.get(request_url, headers={'Authorization': "Bearer " + access_token})
                song_data = json.loads(r.text)['response']['song']
                if 'album' in song_data and song_data['lyrics_state'] == 'complete':
                    album_name = song_data['album']['name'].strip() if song_data['album'] else None
                    lyrics = genius.lyrics(song_data['url'])
                    if lyrics and album_name:
                        s = Song(genius, song_data, lyrics)
                        if album_name not in songs_by_album:
                            songs_by_album[album_name] = []
                        songs_by_album[album_name].append(s)
            except requests.exceptions.Timeout:
                print('Failed receiving song', song['title'], '-- saving songs so far')
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

if __name__ == '__main__':
    main()
