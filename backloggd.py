import feedparser
from ConfigurationFile import ConfigurationFile
from BlueSky import BlueSky
from datetime import datetime, timezone, timedelta
from time import mktime, sleep
import os
import dotenv
from atproto import Client, client_utils
import re
import requests
import io

def extractStatus(description):
    desc = description.lower()
    if "#finished" in desc or "#completed" in desc:
        return "completed"
    if "#abandoned" in desc or "#dropped" in desc:
        return "abandoned"
    if "#played" in desc:
        return "played"
    return "reviewed"

def check_backloggd_feed(backloggd_account, bsky_client):
    registry = ConfigurationFile('backloggd-registry')

    rss_url = f'https://backloggd.com/u/{backloggd_account}/reviews/rss/'
    rss_feed = feedparser.parse(rss_url)

    last_post_raw = registry.getValue('last_post', None)
    if last_post_raw is None:
        last_post = datetime.now(timezone.utc) - timedelta(days=1)
        registry.setValue('last_post', last_post.isoformat())
    else:
        last_post = datetime.fromisoformat(last_post_raw)

    state_map = registry.getValue('state_map', {}) 
    
    # We sort to process chronologically, but we won't strictly "continue" 
    # based on date if it's an update to an existing record.
    sorted_entries = sorted(rss_feed.entries, key=lambda x: mktime(x.published_parsed))

    for item in sorted_entries:
        item_date = datetime.fromtimestamp(mktime(item.published_parsed)).astimezone()
        guid = item.id
        
        # Data from the RSS feed
        current_status = extractStatus(item.description)
        current_rating = item.get('backloggd_user_rating', '0')
        
        # Check what we knew about this game previously
        previous_state = state_map.get(guid)
        
        should_post = False
        change_reason = ""

        # LOGIC 1: It's a brand new entry we've NEVER seen
        if not previous_state:
            # Only post if it's actually new (published after our last_post cutoff)
            if item_date > last_post:
                should_post = True
                change_reason = f"New Log ({current_status})"
            else:
                # Just add it to the state map silently so we track it moving forward
                state_map[guid] = {"status": current_status, "rating": current_rating}
                registry.setValue('state_map', state_map)
                continue

        # LOGIC 2: We've seen it before, check for edits/updates
        else:
            old_status = previous_state.get('status')
            old_rating = previous_state.get('rating')

            if old_status != current_status:
                should_post = True
                change_reason = f"Status changed from {old_status} to {current_status}"
            elif old_rating != current_rating:
                should_post = True
                change_reason = f"Rating updated from {old_rating} to {current_rating}"

        if should_post:
            title_string = item.get('title')
            game_title = title_string.rsplit(" - ", 1)[0] if " - " in title_string else title_string

            image_url = item.get('href')
            if image_url and "igdb.com" in image_url:
                image_url = image_url.replace("t_cover_big", "t_1080p")

            rating_val = float(current_rating) / 2.0
            stars_str = ('★' * int(rating_val)) + ('½' if rating_val % 1 != 0 else '')

            tags = ["gaming", "gamingsky", "backloggd"]
            extra_tags = re.findall(r"#(\w+)", item.description)
            status_keywords = ["finished", "completed", "abandoned", "dropped", "played", "reviewed"]
            
            for tag in extra_tags:
                clean_tag = tag.strip().lower()
                if clean_tag not in status_keywords and clean_tag not in [t.lower() for t in tags]:
                    tags.append(tag)

            verb2 = "rated it"
            if previous_state:
                old_val = float(previous_state.get('rating', 0))
                if float(current_rating) > old_val:
                    verb2 = "increased my rating to"
                elif float(current_rating) < old_val:
                    verb2 = "reduced my rating to"

            tb = client_utils.TextBuilder()
            tb.text(f'I {current_status} {game_title} and {verb2} {stars_str}\n')
            for i, tag in enumerate(tags):
                tb.tag(f"#{tag}", tag)
                if i < len(tags) - 1:
                    tb.text(" ")

            post_text = tb.build_text()
            registry.setValue('last_post_contents', post_text)
            print(f'Sending post [{post_text}] (because {change_reason}): url = {item.link}')
            bsky_client.post_with_link_embed(tb, item.link, image_url)
            
            # Update state_map with the NEW data
            state_map[guid] = {"status": current_status, "rating": current_rating}
            registry.setValue('state_map', state_map)
            
            # If this was a new item (not just an update), push the global clock forward
            if item_date > last_post:
                last_post = item_date
                registry.setValue('last_post', last_post.isoformat())

    registry.setValue('last_process', datetime.now().astimezone().isoformat())