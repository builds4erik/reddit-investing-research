# Reddit access

`reddit_top.py` prints the top posts of a few subreddits, with their best
comments, as JSON on stdout. Claude reads that output, picks the posts that name
a ticker and make a concrete claim, checks them with the stock_viewer MCP tools
and writes notes with `add_note`. The stock_viewer app itself never talks to
Reddit.

Python standard library only; no packages to install.

## Getting access

Reddit no longer hands out API keys on its own (Responsible Builder Policy,
November 2025): every app must be approved first, personal ones included.

1. Make the request at https://support.reddithelp.com/hc/en-us/requests/new
   (Developer Platform & Data API), as a use case not supported by Devvit.
   Describe it plainly: personal and non-commercial; once a day, read the top
   posts of a few investing subreddits and summarize them into notes in my own
   desktop app; read only, nothing posted, no AI training.
2. Once approved, register a **script** app as Reddit's reply says (it used to
   be https://www.reddit.com/prefs/apps). The client id is the string under the
   app's name, the secret is labelled "secret". The script signs in as the app
   alone (application-only OAuth), so no Reddit password is needed.
3. Set the credentials as user environment variables (in a new terminal they
   are then always there):

   ```
   setx REDDIT_CLIENT_ID "..."
   setx REDDIT_CLIENT_SECRET "..."
   setx REDDIT_USERNAME "your reddit username, without /u/"
   ```

   The username only goes into the User-Agent, which Reddit requires as contact
   information. The secret never goes in a file in this folder.

## Running

```
python reddit_top.py                                  # default subreddits, today's top 10 each
python reddit_top.py stocks investing --limit 5 --comments 3
python reddit_top.py ValueInvesting --time week --comments 0
```

Defaults: `investing`, `stocks`, `ValueInvesting` and `SecurityAnalysis`, the
day's top 10 posts each, 5 top-level comments per post. Pinned posts and
removed comments are skipped. Long texts are cut at 3000 characters (posts)
and 1000 (comments).

That is about 45 requests a run; the free limit is 100 a minute.

## Searching for companies

`reddit_search.py` searches the same kind of subreddits for posts about given
companies or tickers and prints them in the same JSON form, grouped by query.
It reuses the sign-in and formatting from `reddit_top.py`, so keep both files
together.

```
python reddit_search.py IREN "Golar LNG"                    # last week's newest posts, 10 per query
python reddit_search.py AMD Nvidia --sort top --time month --comments 0
python reddit_search.py Canatu --subreddits investing stocks EuropeFIRE
```

One search request covers all the subreddits at once (`/r/a+b+c/search`), plus
one request per post for its comments, fetched only once even if several
queries find the same post. Five queries with 10 posts each is at most about
55 requests. Put multi-word names in quotes.

## Rules this follows

- **No author names in the output**: nothing needs them.
- **Nothing is stored**: the script prints and forgets. Reddit requires that
  content deleted on Reddit is deleted everywhere, and recommends not keeping
  any for more than 48 hours. So a note keeps the post's link and Claude's own
  summary and checks, not the post's text.
- **Errors say why**: 401 is usually a wrong id or secret, 403 an app that is
  not (or no longer) approved.
