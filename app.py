import feedparser
from ConfigurationFile import ConfigurationFile
from BlueSky import BlueSky
from datetime import datetime
from time import mktime, sleep
import os
import pickle
import dotenv
from atproto import Client, client_utils
import re
from bs4 import BeautifulSoup
from letterboxd import check_letterboxd_feed
from backloggd import check_backloggd_feed
from serializd import check_serializd_feed

QUEUE_FILE = "pending_posts_queue.pkl"

def save_queue(queue):
    """Saves the current backlog state to a local file."""
    try:
        with open(QUEUE_FILE, "wb") as f:
            pickle.dump(queue, f)
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error saving queue to disk: {e}")

def load_queue():
    """Loads the backlog state from disk if it exists."""
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "rb") as f:
                queue = pickle.load(f)
                if isinstance(queue, list) and len(queue) > 0:
                    print(f"Restored {len(queue)} pending post(s) from persistent storage.")
                    return queue
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error loading queue from disk: {e}")
    return []

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
        
        posts_to_make = load_queue()
        
        BASE_SLEEP = 300      # Normal operations: 5 minutes
        BASE_BACKOFF = 1800    # Initial firewall cool-down unit: 30 minutes
        MAX_BACKOFF = 14400    # Hard ceiling: 4 hours max sleep so it doesn't sleep forever
        backoff_factor = 1
        current_sleep = BASE_SLEEP

        while True:
            new_items = []
            if letterboxd_valid:
                try:
                    new_items.extend(check_letterboxd_feed(letterboxd_account))
                except Exception as e:
                    print(f"Error reading Letterboxd: {e}")
                    
            if backloggd_valid:
                try:
                    new_items.extend(check_backloggd_feed(backloggd_account))
                except Exception as e:
                    print(f"Error reading Backloggd: {e}")
                    
            if serializd_valid:
                try:
                    new_items.extend(check_serializd_feed(serializd_account))
                except Exception as e:
                    print(f"Error reading Serializd: {e}")

            if new_items:
                posts_to_make.extend(new_items)
                save_queue(posts_to_make)
            
            if posts_to_make:
                try:
                    with BlueSky(bluesky_user, bluesky_app_password) as bsky_client:
                        for post in list(posts_to_make):
                            bsky_client.post_with_link_embed(
                                contents=post['text_builder'], 
                                link=post['link'], 
                                image_url=post.get('image_url'), 
                                padding=post.get('padding', False)
                            )
                            posts_to_make.remove(post)
                            save_queue(posts_to_make)
                    print("Batch processing complete. Session closed and memory cleared.")
                    current_sleep = BASE_SLEEP
                except Exception as bsky_error:
                    err_str = str(bsky_error)
                    err_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Smart dynamic backoff check for 403 or 429 errors
                    if "403" in err_str or "429" in err_str or "Unauthorized" in err_str:
                        calculated_backoff = BASE_BACKOFF * backoff_factor
                        current_sleep = min(calculated_backoff, MAX_BACKOFF)
                        
                        print(f"\n[{err_time}] [CRITICAL] BlueSky rate limit/firewall detected: {bsky_error}")
                        print(f"Consecutive failure count: {backoff_factor}")
                        print(f"Backing off exponentially! Sleeping for {current_sleep // 60} minutes to clear IP.")
                        
                        # Double the factor for the next consecutive loop failure
                        backoff_factor *= 2
                    else:
                        current_sleep = BASE_SLEEP
                        print(f"\n[{err_time}] [WARNING] BlueSky broadcast failed: {bsky_error}")
                        
                    print(f"Keeping {len(posts_to_make)} post(s) safely stored in persistent cache file.\n")
            else:
                current_sleep = BASE_SLEEP
            sleep(current_sleep) # wait 5 minutes

    else:
        print('Could not run due to missing keys. Aborting program...')

#run program
if __name__ == '__main__':
    run()