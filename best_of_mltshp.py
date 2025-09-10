from dotenv import load_dotenv
import feedparser
import html
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
    url = re.search(r"https://mltshp(-cdn)?\.com/r/[a-zA-Z0-9]+", entry.description)
    alt = re.search(r"alt=\"([^\"]*)\"", entry.description)
    if not url or not alt:
        print("could not find url or alt")
        print(entry.description)
        return [None, None]
    return [url[0], html.unescape(alt[1])]

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

def encode_toot(entry, alt_text):
    toot = entry.link
    if entry.title != "":
        toot += f" “{entry.title}”"
    if alt_text == "" or alt_text == "CDN Media" or alt_text == "image":
        return False
    return toot
    

def post_toot(toot, attachment):
    data = {
        "status": toot,
        "visibility": "unlisted"
    }
    if attachment and "id" in attachment:
        data["media_ids[]"] = attachment["id"]
    else:
        print("Posting without an attachment")
    if "category" in entry and entry['category'] == "nsfw":
        data['sensitive'] = True

    rsp = requests.post(
        f"https://{MASTODON_INSTANCE}/api/v1/statuses",
        headers={
            "Authorization": f"Bearer {MASTODON_TOKEN}",
            "Idempotency-Key": IDEMPOTENCY_KEY
        },
        data=data
    )
    if rsp.status_code == 200:
        print(f"Posted {toot}")
    else:
        print(f"Failed to post {toot} (HTTP {rsp.status_code})")
        exit(1)
    return rsp.json()

def save_links(links):
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

if __name__ == "__main__":
    print("Loading MLTSHP Popular RSS feed")
    input_feed = load_feed("https://mltshp.com/user/mltshp/rss")
    if len(input_feed.entries) == 0:
        raise Exception("No popular posts found, something went wrong")
    input_feed.entries.reverse() # Start with the oldest entry in the popular feed
    print(f"  found {len(input_feed.entries)} entries")

    links = load_links()
    toot = None

    for entry in input_feed.entries:
        print(entry.link)
        if entry.link not in links:

            # Log the current link
            links.append(entry.link)
            save_links(links)

            # Detect media from the RSS feed
            (url, alt_text) = get_media(entry)
            if not url:
                continue
            if alt_text == "No alt provided":
                alt_text = ""

            # Download the media
            (filename, content_type) = download_media(url)
            attachment = None
            if content_type != "image/gif":
                try:
                    attachment = upload_media(filename, content_type, alt_text)
                except requests.exceptions.ReadTimeout:
                    # If we time out, just keep on truckin'
                    continue
                if "id" not in attachment:
                    print(attachment)
            os.remove(filename)

            # Post the toot
            encoded = encode_toot(entry, alt_text)
            if encoded == False:
                continue
            toot = post_toot(encoded, attachment)
            if "id" in toot:
                print(f"https://{MASTODON_INSTANCE}/{MASTODON_USER}/{toot['id']}")
            else:
                raise Exception("Something went wrong")
            break

    if not toot:
        print("Nothing new to post")