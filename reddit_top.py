"""Prints the day's top posts of some subreddits, with their best comments, as JSON.

Reads Reddit through its Data API with application-only OAuth. Needs an approved
Reddit app; see README.md. Python standard library only.

    python reddit_top.py investing stocks --limit 10 --comments 5
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

VERSION = "0.1"
DEFAULT_SUBREDDITS = ["investing", "stocks", "ValueInvesting", "SecurityAnalysis"]
POST_TEXT_LIMIT = 3000
COMMENT_TEXT_LIMIT = 1000


def user_agent(username):
    return f"windows:stock-viewer-notes:v{VERSION} (by /u/{username})"


def request_json(url, headers, data=None):
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            remaining = resp.headers.get("X-Ratelimit-Remaining")
            reset = resp.headers.get("X-Ratelimit-Reset")
            if remaining and reset and float(remaining) < 5:
                time.sleep(float(reset) + 1)
            return json.load(resp)
    except urllib.error.HTTPError as e:
        hint = {401: "wrong client id or secret?", 403: "app not approved, or access revoked?",
                429: "rate limited; try again later"}.get(e.code, "")
        sys.exit(f"Reddit answered {e.code} for {url} {hint}".rstrip())


def get_token(client_id, secret, agent):
    auth = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    reply = request_json("https://www.reddit.com/api/v1/access_token",
                         {"Authorization": f"Basic {auth}", "User-Agent": agent}, body)
    if "access_token" not in reply:
        sys.exit(f"No token from Reddit: {reply}")
    return reply["access_token"]


def clip(text, limit):
    return text if len(text) <= limit else text[:limit] + "…"


def post_summary(post):
    """The fields worth reading; no author names, since nothing needs them."""
    summary = {
        "subreddit": post["subreddit"],
        "id": post["id"],
        "title": post["title"],
        "link": "https://www.reddit.com" + post["permalink"],
        "flair": post.get("link_flair_text"),
        "score": post["score"],
        "upvote_ratio": post.get("upvote_ratio"),
        "num_comments": post["num_comments"],
        "created": datetime.fromtimestamp(post["created_utc"], timezone.utc).isoformat(timespec="minutes"),
        "text": clip(post.get("selftext", ""), POST_TEXT_LIMIT),
    }
    if not post.get("is_self"):
        summary["url"] = post.get("url")
    return summary


def comment_summaries(listing, count):
    """Top-level comments from a comments listing, skipping removed ones and 'more' stubs."""
    comments = []
    for child in listing["data"]["children"]:
        c = child["data"]
        if child["kind"] != "t1" or c.get("stickied") or c.get("body") in ("[removed]", "[deleted]"):
            continue
        comments.append({"score": c["score"], "text": clip(c["body"], COMMENT_TEXT_LIMIT)})
        if len(comments) == count:
            break
    return comments


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("subreddits", nargs="*", default=DEFAULT_SUBREDDITS)
    parser.add_argument("--time", default="day", choices=["hour", "day", "week", "month"])
    parser.add_argument("--limit", type=int, default=10, help="posts per subreddit")
    parser.add_argument("--comments", type=int, default=5, help="top comments per post, 0 for none")
    args = parser.parse_args()

    env = {k: os.environ.get(k) for k in ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME")}
    missing = [k for k, v in env.items() if not v]
    if missing:
        sys.exit("Set these environment variables first (see README.md): " + ", ".join(missing))

    agent = user_agent(env["REDDIT_USERNAME"])
    token = get_token(env["REDDIT_CLIENT_ID"], env["REDDIT_CLIENT_SECRET"], agent)
    headers = {"Authorization": f"bearer {token}", "User-Agent": agent}
    api = "https://oauth.reddit.com"

    posts = []
    for sub in args.subreddits:
        query = urllib.parse.urlencode({"t": args.time, "limit": args.limit, "raw_json": 1})
        listing = request_json(f"{api}/r/{sub}/top?{query}", headers)
        for child in listing["data"]["children"]:
            post = child["data"]
            if post.get("stickied"):
                continue
            summary = post_summary(post)
            if args.comments > 0 and post["num_comments"] > 0:
                query = urllib.parse.urlencode({"sort": "top", "depth": 1, "limit": args.comments * 2, "raw_json": 1})
                thread = request_json(f"{api}/r/{sub}/comments/{post['id']}?{query}", headers)
                summary["comments"] = comment_summaries(thread[1], args.comments)
            posts.append(summary)

    json.dump({"fetched": datetime.now(timezone.utc).isoformat(timespec="minutes"),
               "time": args.time, "posts": posts}, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
