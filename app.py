import feedparser
from ConfigurationFile import ConfigurationFile
from BlueSky import BlueSky
from datetime import datetime
from time import mktime, sleep
import os
import gc
import dotenv
from atproto import Client, client_utils
import re
from bs4 import BeautifulSoup
from letterboxd import check_letterboxd_feed
from backloggd import check_backloggd_feed
from serializd import check_serializd_feed

def run():
    print('Process starting. Initializing...')

    #grab settings
    valid = True

    #if we are running on docker, envs are supplied directly. If not, we load the file
    from_docker = os.getenv('DOCKER')
    if from_docker is None:
        print("Running locally...")
        dotenv.load_dotenv()
    else:
        print("Running in Docker...")

    letterboxd_account = os.getenv('LETTERBOXD_ACCOUNT')
    letterboxd_valid = True
    if letterboxd_account == '' or letterboxd_account is None:
        letterboxd_valid = False
        print("Optional key [LETTERBOXD_ACCOUNT] missing from configuration file [.env]")

    serializd_account = os.getenv('SERIALIZD_ACCOUNT')
    serializd_valid = True
    if serializd_account == '' or serializd_account is None:
        serializd_valid = False
        print("Optional key [SERIALIZD_ACCOUNT] missing from configuration file [.env]")

    backloggd_account = os.getenv('BACKLOGGD_ACCOUNT')
    backloggd_valid = True
    if backloggd_account == '' or backloggd_account is None:
        backloggd_valid = False
        print("Optional key [BACKLOGGD_ACCOUNT] missing from configuration file [.env]")

    bluesky_user = os.getenv('BLUESKY_USERNAME')
    if bluesky_user == '' or bluesky_user is None:
        valid = False
        print("Error: Required key [BLUESKY_USERNAME] missing from configuration file [.env]")

    bluesky_app_password = os.getenv('BLUESKY_APP_PASSWORD')
    if bluesky_app_password == '' or bluesky_app_password is None:
        valid = False
        print("Error: Required key [BLUESKY_APP_PASSWORD] missing from configuration file [.env]")

    if valid:
        print('Configuration is valid.')
        print('Beginning process loop... (no further logs unless posts are made)')
        while True:
            with BlueSky(bluesky_user, bluesky_app_password) as bsky_client: #keep bluesky client for entire load of actions - then free it
                if letterboxd_valid:
                    check_letterboxd_feed(letterboxd_account, bsky_client)
                if backloggd_valid:
                    check_backloggd_feed(backloggd_account, bsky_client)
                if serializd_valid:
                    check_serializd_feed(serializd_account, bsky_client)
            sleep(300) # wait 5 minutes

    else:
        print('Could not run due to missing keys. Aborting program...')

#run program
if __name__ == '__main__':
    run()