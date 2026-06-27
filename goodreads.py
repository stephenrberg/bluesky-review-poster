import feedparser
from ConfigurationFile import ConfigurationFile
from datetime import datetime, timezone, timedelta
from time import mktime
from atproto import client_utils
import re

def check_goodreads_feed(goodreads_id):
    pending_posts = []
    registry = ConfigurationFile('goodreads-registry')

    # Pass your clean RSS URL (without the shelf parameter)
    rss_feed = feedparser.parse("https://www.goodreads.com/review/list_rss/"+goodreads_id)

    last_post_raw = registry.getValue('last_post', None)
    if last_post_raw is None:
        last_post = datetime.now(timezone.utc) - timedelta(days=1)
        registry.setValue('last_post', last_post.isoformat())
    else:
        last_post = datetime.fromisoformat(last_post_raw)

    posted = False
    
    # Sort entries oldest to newest
    sorted_entries = sorted(rss_feed.entries, key=lambda x: mktime(x.published_parsed))

    for item in sorted_entries:
        item_date = datetime.fromtimestamp(mktime(item.published_parsed)).astimezone()
        
        # 1. Gate check: If it has a rating, it's a finished read
        user_rating = item.get('user_rating', '0')
        rating_val = int(user_rating) if user_rating.isdigit() else 0
        
        if rating_val == 0:
            continue # Skips books you just added to other shelves without rating

        if item_date > last_post:
            print('[Goodreads] New Book Entry Found...')
            posted = True
            
            # 2. Extract title and set stars
            book_title = item.get('title', 'Unknown Title')
            stars_str = f" {'★' * rating_val}" if rating_val > 0 else ""

            # 3. Setup core hashtags
            tags = ["comics", "comicsky", "goodreads"]

            # 4. Optional: Extract custom tags from your written review box text
            raw_review = item.get('user_review', '')
            if raw_review:
                custom_tags = re.findall(r"#(\w+)", raw_review)
                tags = custom_tags + tags

            # 5. Build clean, minimal text layout
            tb = client_utils.TextBuilder()
            tb.text(f'I read \'{book_title}\' and gave it {stars_str}\n')
            for i, tag in enumerate(tags):
                tb.tag(f"#{tag}", tag)
                if i < len(tags) - 1:
                    tb.text(" ")

            post_text = tb.build_text()
            registry.setValue('last_post_contents', post_text)
            print(f'[Goodreads] Queueing post: [{post_text}]')
            
            # 6. Grab the highest quality image URL available in the XML
            image_url = item.get('book_large_image_url', None)
            review_title = f'{book_title} | {stars_str}'
            clean_link = item.link.split('?')[0]
            review_preview = (raw_review[:147] + '...') if len(raw_review) > 150 else raw_review

            pending_posts.append({
                'text_builder': tb,
                'link': clean_link,
                'image_url': image_url,
                'padding': True,
                'title': review_title,
                'description': review_preview
            })

            registry.setValue('total_posts', registry.getValue('total_posts', 0) + 1)
        else:
            continue

    if posted:
        registry.setValue('last_post', datetime.now().astimezone().isoformat())
    registry.setValue('last_process', datetime.now().astimezone().isoformat())
    return pending_posts