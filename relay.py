import time
from datetime import datetime, timedelta
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.client import SpotifyException
import random
import signal
import sys
import logging
import requests

try:
    import RPi.GPIO as GPIO
    import pn532.pn532 as nfc
    from pn532 import *
    pn532 = PN532_I2C(debug=False, reset=20, req=16)
    pn532.SAM_configuration()
except:
    print('Running in dev mode')

from config import *



debugLevel='INFO'

logger = logging.getLogger('spotipy')
logger.addHandler(logging.StreamHandler())
level = logging.getLevelName(debugLevel)
logger.setLevel(level)

run = True

def end_read(signal,frame):
    global run
    logger.info("\nCtrl+C captured, ending read.")
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
    logger.info('{} by {}'.format(pl['tracks']['items'][tracknum]['track']['name'], ", ".join(artists)))
    sp.start_playback(device_id=DEVICE, uris=[track])
    return True

def spotify_play_track(sp, id, device_id):
    tracks = TRACKS
    try:
        trackuri = tracks[id]['uri']
    except:
        logger.error(f'UID not recognised: {id}')
        return False
    volume = int(tracks[id]['volume'])
    name = tracks[id]['name']
    if device_id:
        sp.start_playback(device_id=device_id, uris=[trackuri])
    else:
        sp.start_playback(uris=[trackuri])
    logger.info(f'Playing {name}')
    sp.volume(volume_percent=volume)
    return True

def get_tracks_google():
    logger.info('Setting up tracks from Google Sheet')
    data = requests.get(SHEET_URL).json()
    num_items = int(data['feed']['openSearch$totalResults']['$t'])
    tracks = {}
    num_cols = 4
    for i in range(0,num_items // num_cols):
        item = data['feed']['entry']
        j = i*num_cols
        tagid = str(item[j+1]['content']['$t'])
        payload = {'name':item[j]['content']['$t'],
                    'uri': item[j+2]['content']['$t'],
                    'volume':item[j+3]['content']['$t']}
        tracks[tagid] = payload
        logger.info(tagid)
    return tracks

def init():
    sp, device_id = spotify_init()
    tracks = get_tracks_google()
    return sp, device_id, tracks

if __name__ == '__main__':
    logger.info("Starting")
    sp, device_id = spotify_init()
    current_card = None
    try:
        while True:
            # Check if a card is available to read
            id = pn532.read_passive_target(timeout=0.5)
            # Try again if no card is available.
            if not id and current_card:
                sp.pause_playback(device_id=device_id)
                current_card = None
                continue
            elif id and id.hex() != current_card:
                logger.debug(f'Found card with UID:{id.hex()}')
                current_card = id.hex()
                try:
                    sent = spotify_play_track(sp, current_card, device_id)
                    time.sleep(5) #Delay before checking the tag reader again
                except SpotifyException as e:
                    logger.warning('Problem with playback {}'.format(e))
                    sp, device_id = spotify_init()
    except KeyboardInterrupt:
        GPIO.cleanup()
        raise
