from atproto import Client, models
from bs4 import BeautifulSoup
import requests
import time
from requests.exceptions import HTTPError
from PIL import Image, ImageFilter, ImageEnhance
import io

class BlueSky:
    def __init__(self, username, password):
        self.client = Client()
        self.client.login(username, password)
        # Initialize the session once to reuse connections
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
        self.session = None
        self.client = None
        
    def post_with_link_embed(self, contents, link, image_url=None, padding=False, title="", description=""):
        thumbnail = None

        # Always scrape details first
        scraped_title, scraped_description, embedded_thumbnail = self.get_embed_details(link)
        if(scraped_title != ''):
            title = scraped_title
        if(scraped_description != ''):
            description = scraped_description

        if embedded_thumbnail:
            thumbnail = embedded_thumbnail  # Use scraped thumbnail if it exists
        elif image_url:
            try:
                img_response = requests.get(image_url, timeout=10)
                img_response.raise_for_status()
                
                if padding:
                    try: 
                        # --- PILLOW PADDING LOGIC (BLURRED BACKGROUND) ---
                        img = Image.open(io.BytesIO(img_response.content))
                        img = img.convert("RGB") 
                        w, h = img.size
                        
                        target_width = int(h * 1.91) # Keep standard widescreen ratio aspect
                        
                        background = img.resize((target_width, int(target_width / w * h)), Image.Resampling.LANCZOS)
                        background = background.filter(ImageFilter.GaussianBlur(radius=40))

                        enhancer = ImageEnhance.Color(background)
                        background = enhancer.enhance(0.4) # Saturation to 40%
                        
                        bg_w, bg_h = background.size
                        top = (bg_h - h) // 2
                        background = background.crop((0, top, target_width, top + h))
                        
                        paste_x = (target_width - w) // 2
                        background.paste(img, (paste_x, 0))
                        
                        img_byte_arr = io.BytesIO()
                        background.save(img_byte_arr, format='JPEG', quality=85)
                        thumbnail = self.client.upload_blob(img_byte_arr.getvalue()).blob
                        
                    except Exception as e:
                        print(f"Force image/padding failed: {e}")
                else:
                    img_byte_arr = io.BytesIO(img_response.content)
                    thumbnail = self.client.upload_blob(img_byte_arr.getvalue()).blob
            except Exception as e:
                print(f"Failed pulling backup image URL: {e}")

        embed = models.AppBskyEmbedExternal.Main(
            external=models.AppBskyEmbedExternal.External(
                title=title,
                description=description,
                uri=link,
                thumb=thumbnail,
            )
        )

        self.client.send_post(text=contents, embed=embed)
        # print(f"Sent post {title} with link embed: {link} and contents: {contents.build_text()}")

    def get_embed_details(self, link):
        title = ''
        description = ''
        thumbnail = None

        try:
            link = link.strip().replace('\u200b', '').replace('\u2060', '')
            response = self.session.get(link, timeout=10)
            
            if response.status_code == 429:
                print("Rate limited on page fetch. Sleeping 10s...")
                time.sleep(10)
                response = self.session.get(link, timeout=10)
                
            response.raise_for_status()
            data = BeautifulSoup(response.text, "html.parser")

            title_tag = data.find("meta", property="og:title")
            if title_tag:
                title = title_tag['content']

            description_tag = data.find("meta", property="og:description")
            if description_tag:
                description = description_tag["content"]
            
            image_tag = data.find("meta", property="og:image")
            if image_tag:
                img_url = image_tag["content"]
                img_headers = {"Referer": link}
                img_response = self.session.get(img_url, headers=img_headers, timeout=10)
                
                if img_response.status_code == 200:
                    thumbnail = self.client.upload_blob(img_response.content).blob

        except HTTPError as e:
            print(f"HTTP Error: {e}")
            return title, description, None
        except Exception as e:
            print(f"Unexpected scraping error: {e}")
            return title, description, None
            
        return title, description, thumbnail