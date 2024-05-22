from dotenv import load_dotenv
import feedparser
import os
import random
import re
import requests
import ssl
import string

load_dotenv()

MASTODON_INSTANCE = os.environ["MASTODON_INSTANCE"]
MASTODON_USER = os.environ["MASTODON_USER"]
MASTODON_TOKEN = os.environ["MASTODON_TOKEN"]

IDEMPOTENCY_KEY = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))

def load_feed(url):
    response = requests.get(url)
    return feedparser.parse(response.text)

def get_media(entry):
    url = re.search(r"https://mltshp.com/r/[a-zA-Z0-9]+", entry.description)
    alt = re.search(r"alt=\"([^\"]*)\"", entry.description)
    return [url[0], alt[1]]

def download_media(url):
    print(f"Downloading {url}")
    filename = url.split('/')[-1]
    rsp = requests.get(url, stream=True)
    rsp.raise_for_status()
    with open(filename, "wb") as file:
        for chunk in rsp.iter_content(chunk_size=8192): 
            file.write(chunk)
    return [filename, rsp.headers["Content-Type"]]

def upload_media(filename, content_type, alt_text):
    print(f"Uploading {filename} ({content_type}) “{alt_text}”")
    rsp = requests.post(
        f"https://{MASTODON_INSTANCE}/api/v2/media",
        headers={
            "Authorization": f"Bearer {MASTODON_TOKEN}",
            "Idempotency-Key": IDEMPOTENCY_KEY
        },
        files={
            "file": (
                filename,
                open(filename, "rb"),
                content_type
            )
        },
        data={
            "description": alt_text
        },
        timeout=30
    )
    return rsp.json()

def encode_toot(entry):
    return f"{entry.link} “{entry.title}”"

def post_toot(toot, attachment):
    rsp = requests.post(
        f"https://{MASTODON_INSTANCE}/api/v1/statuses",
        headers={
            "Authorization": f"Bearer {MASTODON_TOKEN}",
            "Idempotency-Key": IDEMPOTENCY_KEY
        },
        data={
            "status": toot,
            "visibility": "unlisted",
            "media_ids[]": attachment["id"]
        }
    )
    if rsp.status_code == 200:
        print(f"Posted {toot}")
    else:
        print(f"Failed to post {toot} (HTTP {rsp.status_code})")
        exit(1)
    return rsp.json()

def save_links(links):
    links.sort()
    # limit the number of links to 200
    if len(links) > 200:
        num_links = len(links)
        start = num_links - 200
        links = links[start:num_links]
    with open('links.log', 'w') as file:
        file.write("\n".join(links))

def load_links():
    links = []
    try:
        print("Loading links.log")
        with open("links.log", "r") as file:
            links = file.read().split("\n")
    except FileNotFoundError:
        print(f"Loading {MASTODON_USER} RSS feed")
        output_feed = load_feed(f"https://{MASTODON_INSTANCE}/{MASTODON_USER}.rss?limit=200")
        for entry in output_feed.entries:
            match = re.search('https://mltshp.com/p/[a-zA-Z0-9]+', entry.description)
            if match:
                links.append(match[0])
        save_links(links)
    print(f"  found {len(links)} entries")
    return links

print("Loading MLTSHP Popular RSS feed")
input_feed = load_feed("https://mltshp.com/user/mltshp/rss")
if len(input_feed.entries) == 0:
    raise Exception("No popular posts found, something went wrong")
input_feed.entries.reverse() # Start with the oldest entry in the popular feed
print(f"  found {len(input_feed.entries)} entries")

links = load_links()
toot = None

for entry in input_feed.entries:
    if entry.link not in links:
        links.append(entry.link)
        save_links(links)
        (url, alt_text) = get_media(entry)
        (filename, content_type) = download_media(url)
        attachment = upload_media(filename, content_type, alt_text)
        os.remove(filename)
        if "id" not in attachment:
            print(attachment)
            raise Exception("Attachment failed to upload")
        toot = post_toot(encode_toot(entry), attachment)
        if toot and "id" in toot:
            toot_id = toot["id"]
            print(f"https://{MASTODON_INSTANCE}/{MASTODON_USER}/{toot_id}")
        break

if not toot:
    print("Nothing new to post")