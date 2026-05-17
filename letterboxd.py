import feedparser
from ConfigurationFile import ConfigurationFile
from BlueSky import BlueSky
from datetime import datetime, timezone, timedelta
from time import mktime, sleep
from atproto import Client, client_utils
import re
from bs4 import BeautifulSoup


def check_letterboxd_feed(letterboxd_account):
    pending_posts = []
    registry = ConfigurationFile('letterboxd-registry')

    #now grab rss feed
    rss_url = f'https://letterboxd.com/{letterboxd_account}/rss'
    rss_feed = feedparser.parse(rss_url)

    last_post_raw = registry.getValue('last_post', None)
    if last_post_raw is None:
        # If fresh start, only look at posts from the last day
        last_post = datetime.now(timezone.utc) - timedelta(days=1)
        registry.setValue('last_post', last_post.isoformat())
    else:
        last_post = datetime.fromisoformat(last_post_raw)

    #check for any new diary entries on letterboxd
    posted = False
    for item in rss_feed.entries:
        item_date = datetime.strptime(item.published, '%a, %d %b %Y %H:%M:%S %z')
        if item_date > last_post:
            print('New Entry Found...')
            posted = True
            # post_text = f'Just watched {item.letterboxd_filmtitle} ({item.letterboxd_filmyear}) and rated it {item.letterboxd_memberrating}/5 on Letterboxd:'
            # Convert the rating to a float first
            rating_val = float(item.letterboxd_memberrating)
            # Calculate full stars and check for a half star
            full_stars = int(rating_val)
            half_star = '½' if rating_val % 1 != 0 else ''
            # Create the string (e.g., 3.5 becomes ★★★½)
            stars_str = ('★' * full_stars) + half_star
            # Define your tag string
            tags = ["Letterboxd", "Film", "FilmSky", "Movie", "MovieSky", "NowWatching"]

            raw_desc = item.description
            soup = BeautifulSoup(raw_desc, "html.parser")
            clean_text = soup.get_text()
            custom_tags = re.findall(r"#(\w+)", clean_text)

            tags = custom_tags + tags

            # Determine the verb based on the rewatch status
            is_rewatch = getattr(item, 'letterboxd_rewatch', 'No') == 'Yes'
            verb = "I rewatched" if is_rewatch else "I watched"

            # Your updated post_text
            tb = client_utils.TextBuilder()
            tb.text(f'{verb} {item.letterboxd_filmtitle} ({item.letterboxd_filmyear}) and gave it {stars_str}\n')
            for i, tag in enumerate(tags):
                tb.tag(f"#{tag}", tag)
                if i < len(tags) - 1:
                    tb.text(" ") # Add space between tags

            post_text = tb.build_text()
            registry.setValue('last_post_contents', post_text)
            print(f'Sending post: [{post_text}]')
            pending_posts.append({
                'text_builder': tb,
                'link': item.link,
                'image_url': None,      # Letterboxd standard embeds scrape the cover automatically
                'padding': False
            })

            registry.setValue('total_posts', registry.getValue('total_posts', 0) + 1)
        else:
            break

    if posted:
        registry.setValue('last_post', datetime.now().astimezone())
    registry.setValue('last_process', datetime.now().astimezone())
    return pending_posts