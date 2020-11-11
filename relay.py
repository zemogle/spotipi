import time
from datetime import datetime, timedelta
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.client import SpotifyException
import random
import signal
import sys

from pirc522 import RFID

from config import *


run = True
rdr = RFID()
util = rdr.util()
util.debug = True

def end_read(signal,frame):
    global run
    print("\nCtrl+C captured, ending read.")
    run = False
    rdr.cleanup()
    sys.exit()


def spotify_init():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(username=USERNAME,
            scope=SCOPES,
            client_id=CLIENTID,
            client_secret=CLIENTSECRET,
            show_dialog=False,
            redirect_uri='http://www.gomez.me.uk/'))

def spotify_randomiser(token):
    sp = spotipy.Spotify(auth=token)
    pl = sp.user_playlist(user=USERNAME,playlist_id='spotify:playlist:{}'.format(PLAYLISTID))
    tracknum = random.randint(0,pl['tracks']['total'])-1
    track = pl['tracks']['items'][tracknum]['track']['uri']
    artists = [a['name'] for a in pl['tracks']['items'][tracknum]['track']['artists']]
    print('{} by {}'.format(pl['tracks']['items'][tracknum]['track']['name'], ", ".join(artists)))
    sp.start_playback(device_id=DEVICE, uris=[track])
    return True

def spotify_play_track(sp, trackuri):
    #if not sp.currently_playing() or  not sp.currently_playing().get('is_playing', False):
    sp.start_playback(device_id=DEVICE, uris=[trackuri])
    return True
    #else:
    #    print('Something is already playing')
    #    return False


if __name__ == '__main__':
    signal.signal(signal.SIGINT, end_read)

    print("Starting")
    sp = spotify_init()
    while run:
        rdr.wait_for_tag()

        (error, uid) = rdr.anticoll()
        if not error:
            tagid = f"{uid[0]}_{uid[1]}_{uid[2]}_{uid[3]}_{uid[4]}"
            trackuri = TRACKS.get(tagid,None)
            if not trackuri:
                print(f'Track not found for {tagid}')
                continue
            try:
                sent = spotify_play_track(sp, trackuri)
            except SpotifyException as e:
                print('Trying again to get token {}'.format(e))
                sp = spotify_init()
                sent = spotify_play_track(sp, trackuri)
