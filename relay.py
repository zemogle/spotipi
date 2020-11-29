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

def get_device_id(devicelist):
    devices = {d['name']:d['id'] for d in devicelist['devices']}
    # Find ID of required device
    return devices.get(DEVICE, None)

def spotify_init():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(username=USERNAME,
            scope=SCOPES,
            client_id=CLIENTID,
            client_secret=CLIENTSECRET,
            show_dialog=False,
            redirect_uri='http://www.gomez.me.uk/'))
    device_id = get_device_id(sp.devices())
    return sp, device_id

def spotify_randomiser(token):
    '''
    Currently not implemented
    '''
    sp = spotipy.Spotify(auth=token)
    pl = sp.user_playlist(user=USERNAME,playlist_id='spotify:playlist:{}'.format(PLAYLISTID))
    tracknum = random.randint(0,pl['tracks']['total'])-1
    track = pl['tracks']['items'][tracknum]['track']['uri']
    artists = [a['name'] for a in pl['tracks']['items'][tracknum]['track']['artists']]
    print('{} by {}'.format(pl['tracks']['items'][tracknum]['track']['name'], ", ".join(artists)))
    sp.start_playback(device_id=DEVICE, uris=[track])
    return True

def spotify_play_track(sp, trackuri, device_id):
    if device_id:
        sp.start_playback(device_id=device_id, uris=[trackuri])
    else:
        sp.start_playback(uris=[trackuri])
    sp.volume(volume_percent=30)
    return True


if __name__ == '__main__':
    signal.signal(signal.SIGINT, end_read)

    print("Starting")
    sp, device_id = spotify_init()
    while run:
        rdr.wait_for_tag()

        (error, data) = rdr.request()
        if not error:
            print("\nDetected: " + format(data, "02x"))

        (error, uid) = rdr.anticoll()
        if not error:
            tagid = f"{uid[0]}_{uid[1]}_{uid[2]}_{uid[3]}_{uid[4]}"
            trackuri = TRACKS.get(tagid,None)
            if not trackuri:
                print('Track not found for {tagid}')
                continue
            try:
                sent = spotify_play_track(sp, trackuri, device_id)
                time.sleep(5) #Delay before checking the tag reader again
            except SpotifyException as e:
                print('Trying again to get token and device {}'.format(e))
                sp, device_id = spotify_init()
                sent = spotify_play_track(sp, trackuri, device_id)
