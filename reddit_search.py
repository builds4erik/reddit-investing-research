"""Searches some subreddits for posts about given companies, with their best comments, as JSON.

Read only: it never posts, comments, votes or sends messages. Reads Reddit through its
Data API with application-only OAuth, sharing the helpers in reddit_top.py. Needs an
approved Reddit app; see README.md. Python standard library only.

    python reddit_search.py IREN "Golar LNG" --time week --limit 10 --comments 3
"""

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone

from reddit_top import comment_summaries, get_token, post_summary, request_json, user_agent

DEFAULT_SUBREDDITS = [
    # general
    "investing", "stocks", "StockMarket", "investing_discussion",
    # analysis and value
    "ValueInvesting", "SecurityAnalysis",
    # long-term, ETFs, dividends
    "Bogleheads", "ETFs", "dividends", "financialindependence",
    # sectors and companies I follow
    "semiconductors", "AMD_Stock", "NVDA_Stock", "BitcoinMining", "ASX_Bets",
]
API = "https://oauth.reddit.com"


def search(subreddits, query, sort, time_window, limit, headers):
    """One request covers all subreddits: /r/a+b+c/search restricted to them."""
    params = urllib.parse.urlencode({
        "q": query, "restrict_sr": "on", "sort": sort, "t": time_window,
        "limit": limit, "type": "link", "raw_json": 1,
    })
    listing = request_json(f"{API}/r/{'+'.join(subreddits)}/search?{params}", headers)
    return [child["data"] for child in listing["data"]["children"]
            if child["kind"] == "t3" and not child["data"].get("stickied")]


def top_comments(post, count, headers, cache):
    """Fetched once per post, even when several queries find the same post."""
    if post["id"] not in cache:
        params = urllib.parse.urlencode({"sort": "top", "depth": 1, "limit": count * 2, "raw_json": 1})
        thread = request_json(f"{API}/r/{post['subreddit']}/comments/{post['id']}?{params}", headers)
        cache[post["id"]] = comment_summaries(thread[1], count)
    return cache[post["id"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("queries", nargs="+", help='company names or tickers, e.g. IREN "Golar LNG"')
    parser.add_argument("--subreddits", nargs="+", default=DEFAULT_SUBREDDITS, metavar="NAME")
    parser.add_argument("--sort", default="new", choices=["new", "relevance", "top", "comments"])
    parser.add_argument("--time", default="week", choices=["hour", "day", "week", "month", "year"])
    parser.add_argument("--limit", type=int, default=10, help="posts per query, at most 100")
    parser.add_argument("--comments", type=int, default=3, help="top comments per post, 0 for none")
    args = parser.parse_args()

    env = {k: os.environ.get(k) for k in ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME")}
    missing = [k for k, v in env.items() if not v]
    if missing:
        sys.exit("Set these environment variables first (see README.md): " + ", ".join(missing))

    agent = user_agent(env["REDDIT_USERNAME"])
    token = get_token(env["REDDIT_CLIENT_ID"], env["REDDIT_CLIENT_SECRET"], agent)
    headers = {"Authorization": f"bearer {token}", "User-Agent": agent}

    results, cache = [], {}
    for query in args.queries:
        posts = []
        for post in search(args.subreddits, query, args.sort, args.time, min(args.limit, 100), headers):
            summary = post_summary(post)
            if args.comments > 0 and post["num_comments"] > 0:
                summary["comments"] = top_comments(post, args.comments, headers, cache)
            posts.append(summary)
        results.append({"query": query, "posts": posts})

    json.dump({"fetched": datetime.now(timezone.utc).isoformat(timespec="minutes"),
               "subreddits": args.subreddits, "sort": args.sort, "time": args.time,
               "results": results}, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
