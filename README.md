# Reddit Top Post Analyzer (Exa + Reddit)

A small Flask website that lets you:

- Choose a subreddit.
- Choose how many top posts to pull.
- Choose the time filter: **past week**, **past month**, or **past year**.
- Fetch each post's comments and include the **upvote score for every comment**.
- Build one big "all text" output for downstream analysis.
- Optionally enrich external post links using the **Exa Contents API**.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variable

Set this to enable Exa content extraction for external links in posts:

```bash
export EXA_API_KEY=your_exa_key
```

If it is not set, the app still works (Reddit data only).

## Run

```bash
python app.py
```

Then open http://localhost:8000

## API endpoint

`POST /api/scrape`

Example JSON payload:

```json
{
  "subreddit": "python",
  "limit": 5,
  "time_filter": "month"
}
```

Allowed `time_filter` values:

- `week`
- `month`
- `year`

## Notes

- Reddit API is read from public JSON endpoints.
- For very large comment trees, Reddit may truncate; this app requests deep/top comments, but completeness depends on Reddit responses.
- Exa extraction is attempted only for non-Reddit URLs in posts.
