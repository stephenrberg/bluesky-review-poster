import requests
from ConfigurationFile import ConfigurationFile
from datetime import datetime, timezone, timedelta
from time import sleep
import re
from atproto import client_utils

def check_serializd_feed(serializd_account):
    pending_posts = []
    registry = ConfigurationFile('serializd-registry')

    # Essential headers to avoid 403 Forbidden from Serializd
    headers = {
        "X-Requested-With": "serializd_vercel",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    diary_url = f'https://serializd.onrender.com/api/user/{serializd_account}/diary'
    
    try:
        response = requests.get(diary_url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        reviews = data.get('reviews', [])
    except Exception as e:
        print(f"Error fetching Serializd data: {e}")
        sleep(300)
        return

    # Load last_post as an aware datetime
    last_post_raw = registry.getValue('last_post', None)
    if last_post_raw is None:
        # If fresh start, only look at posts from the last 10 minutes
        last_post = datetime.now(timezone.utc) - timedelta(days=1)
        registry.setValue('last_post', last_post.isoformat())
    else:
        last_post = datetime.fromisoformat(last_post_raw)
    
    posted = False
    # Process the list (Serializd JSON is usually reverse-chronological)
    for item in reviews:
        # Parse 'dateAdded' (e.g., 2026-04-21T14:13:19Z)
        # Python 3.11+ handles the 'Z' suffix natively with fromisoformat
        item_date = datetime.fromisoformat(item['dateAdded'].replace('Z', '+00:00'))

        if item_date > last_post:
            show_name = item.get('showName')
            print(f"New Entry Found: {show_name}")
            posted = True

            # 1. Handle Ratings (Serializd is 1-10)
            rating_val = float(item.get('rating', 0)) / 2.0
            full_stars = int(rating_val)
            half_star = '½' if rating_val % 1 != 0 else ''
            stars_str = ('★' * full_stars) + half_star if rating_val > 0 else "No rating"

            # 2. Get Season and Episode info
            season_id = item.get('seasonId')
            seasons = item.get('showSeasons', [])
            current_season = next((s for s in seasons if s['id'] == season_id), None)
            
            season_name = current_season.get('name', None) if current_season else None
            ep_num = item.get('episodeNumber', None)
            ep_name = item.get('episodeName', None)
            current_episode = None
            if current_season and 'episodes' in current_season and ep_num:
                # Find the specific episode from the season's episode list
                episodes_list = current_season.get('episodes', [])
                current_episode = next((e for e in episodes_list if e.get('episodeNumber') == ep_num), None)
            
            # Build the display title
            display_title = f"{show_name}"
            if season_name:
                display_title += f" - {season_name}"
                if ep_num:
                    display_title += f" (Ep {ep_num}: {ep_name})"

            # 3. Create the BlueSky post body
            verb = "I rewatched" if item.get('isRewatch') == True else "I watched"
            tags = ["TV", "TVSky", "Serializd", "NowWatching"]

            # SCRAPE TAGS from reviewText
            review_content = item.get('reviewText', '')
            custom_tags = []
            if review_content:
                # Find all #hashtags (alphanumeric only)
                found_tags = re.findall(r"#(\w+)", review_content)
                for t in found_tags:
                    if t not in tags: # Avoid duplicates
                        custom_tags.append(t)
            
            tags = custom_tags + tags
            
            tb = client_utils.TextBuilder()
            tb.text(f'{verb} {display_title} and gave it {stars_str}\n')
            
            for i, tag in enumerate(tags):
                tb.tag(f"#{tag}", tag)
                if i < len(tags) - 1:
                    tb.text(" ")

            # 4. Construct the review link
            review_id = item.get('id')
            review_link = f"https://www.serializd.com/review/{review_id}"

            # --- POSTER PATH LOGIC ---
            # Prioritize the specific Season Poster, fallback to Show Banner
            # New hierarchy: Episode Still > Season Poster > Show Banner
            poster_path = None
            if current_episode and 'stillPath' in current_episode and current_episode['stillPath']:
                poster_path = current_episode['stillPath']
            elif current_season and 'posterPath' in current_season and current_season['posterPath']:
                poster_path = current_season['posterPath']
            else:
                poster_path = item.get('showBannerImage')

            # Construct the high-res TMDB URL
            image_url = f"https://image.tmdb.org/t/p/w780{poster_path}" if poster_path else None
            
            # 5. Send to BlueSky
            print(f'Sending post: [{tb.build_text()}] {review_link}')
            pending_posts.append({
                'text_builder': tb,
                'link': review_link,
                'image_url': image_url,
                'padding': True # Vertical TV posters need padding!
            })

            # Track total stats
            registry.setValue('total_posts', registry.getValue('total_posts', 0) + 1)
        else:
            # Stop processing if we reach an entry older than our baseline
            break

    # Only update the baseline if we actually processed new items
    if posted:
        registry.setValue('last_post', datetime.now(timezone.utc).isoformat())

    registry.setValue('last_process', datetime.now(timezone.utc).isoformat())
    return pending_posts
