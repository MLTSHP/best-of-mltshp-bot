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

def encode_toot(feed_entry):
    return f"{feed_entry.link} “{feed_entry.title}”"

def post_toot(toot):
    response = requests.post(
        f"https://{MASTODON_INSTANCE}/api/v1/statuses",
        headers={
            "Authorization": f"Bearer {MASTODON_TOKEN}",
            "Idempotency-Key": IDEMPOTENCY_KEY
        },
        data={
            "status": toot,
            "visibility": "unlisted"
        }
    )
    if response.status_code == 200:
        print(f"Posted {toot}")
    else:
        print(f"Failed to post {toot}")
        print(response.status_code)

# Don't verify SSL certs
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

print("Loading MLTSHP Popular RSS feed")
input_feed = feedparser.parse("https://mltshp.com/user/mltshp/rss")
input_feed.entries.reverse() # Start with the oldest entry in the popular feed
print(f"  found {len(input_feed.entries)} entries")

print(f"Loading {MASTODON_USER} RSS feed")
output_feed = feedparser.parse(f"https://{MASTODON_INSTANCE}/{MASTODON_USER}.rss?limit=200")
print(f"  found {len(output_feed.entries)} entries")

already_tooted = []
for entry in output_feed.entries:
    match = re.search('https://mltshp.com/p/[a-zA-Z0-9]+', entry.description)
    if match:
        already_tooted.append(match[0])

for entry in input_feed.entries:
    if entry.link not in already_tooted:
        post_toot(encode_toot(entry))
        break