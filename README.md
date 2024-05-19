# Best of MLTSHP Mastodon bot

Takes an [RSS feed](https://mltshp.com/user/mltshp/rss) and posts to a [configured bot account](https://mefi.social/@best_of_mltshp).

## Development Setup

```
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Edit `.env` with environment variables described below.

## Environment variables

-   `MASTODON_INSTANCE` - hostname of the Mastodon instance e.g., `mastodon.social`
-   `MASTODON_USER` - the bot's user account, prefixed with an `@` symbol, e.g., `@bot_user`
-   `MASTODON_TOKEN` - access token found in Mastodon _Settings → Development → [Your Application]_

## Run from the CLI

```
$ python best_of_mltshp.py
```

## GitHub Actions

This repo includes a workflow to run the bot:

-   Each time an update gets pushed
-   On demand from the Actions tab
-   Once per hour

## Inspiration

Prompted by [this post](https://mltshp.com/p/1Q1UG) (and [GitHub issue](https://github.com/MLTSHP/mltshp/issues/751)) from Jessamyn West. [This post](https://www.bentasker.co.uk/posts/blog/software-development/writing-a-simple-mastodon-bot-to-submit-rss-items.html) from Ben Tasker's blog was a helpful reference.
