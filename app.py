import os
from dataclasses import dataclass
from typing import Any

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

REDDIT_BASE = "https://www.reddit.com"
USER_AGENT = "reddit-analyzer/1.0 (by u/example)"
TIME_FILTER_MAP = {
    "week": "week",
    "month": "month",
    "year": "year",
}


@dataclass
class CommentRecord:
    author: str
    score: int
    body: str


def reddit_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(
        f"{REDDIT_BASE}{path}",
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_top_posts(subreddit: str, limit: int, time_filter: str) -> list[dict[str, Any]]:
    payload = reddit_get(
        f"/r/{subreddit}/top/.json",
        params={"limit": limit, "t": time_filter},
    )
    return payload.get("data", {}).get("children", [])


def flatten_comments(node: dict[str, Any], output: list[CommentRecord]) -> None:
    if not isinstance(node, dict):
        return

    kind = node.get("kind")
    data = node.get("data", {})

    if kind == "t1":
        body = (data.get("body") or "").strip()
        if body:
            output.append(
                CommentRecord(
                    author=data.get("author") or "[deleted]",
                    score=int(data.get("score") or 0),
                    body=body,
                )
            )

    replies = data.get("replies")
    if isinstance(replies, dict):
        for child in replies.get("data", {}).get("children", []):
            flatten_comments(child, output)


def fetch_comments(subreddit: str, post_id: str) -> list[CommentRecord]:
    payload = reddit_get(
        f"/r/{subreddit}/comments/{post_id}/.json",
        params={"limit": 500, "depth": 8, "sort": "top"},
    )

    if not isinstance(payload, list) or len(payload) < 2:
        return []

    output: list[CommentRecord] = []
    for child in payload[1].get("data", {}).get("children", []):
        flatten_comments(child, output)
    return output


def fetch_exa_contents(urls: list[str]) -> dict[str, str]:
    api_key = os.getenv("EXA_API_KEY")
    if not api_key or not urls:
        return {}

    response = requests.post(
        "https://api.exa.ai/contents",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json={"urls": urls, "text": {"maxCharacters": 8000}},
        timeout=45,
    )

    if not response.ok:
        return {}

    data = response.json()
    results = data.get("results", [])

    by_url: dict[str, str] = {}
    for item in results:
        url = item.get("url")
        text = (item.get("text") or "").strip()
        if url and text:
            by_url[url] = text

    return by_url


def build_analysis_text(posts: list[dict[str, Any]]) -> str:
    sections: list[str] = []

    for idx, post in enumerate(posts, start=1):
        comments = post["comments"]
        section = [
            f"Post #{idx}",
            f"Title: {post['title']}",
            f"Post upvotes: {post['score']}",
            f"Post URL: {post['url']}",
            f"Reddit permalink: https://reddit.com{post['permalink']}",
            "Post body:",
            post["selftext"] or "[No selftext]",
            "Comments:",
        ]

        if comments:
            for c in comments:
                section.append(f"- ({c['score']} upvotes) u/{c['author']}: {c['body']}")
        else:
            section.append("[No comments found]")

        if post.get("external_content"):
            section.append("External content extracted via Exa:")
            section.append(post["external_content"])

        sections.append("\n".join(section))

    return "\n\n" + ("\n\n".join(sections))


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.post("/api/scrape")
def scrape() -> Any:
    payload = request.get_json(force=True)
    subreddit = (payload.get("subreddit") or "").strip().replace("/r/", "").replace("r/", "")
    limit = int(payload.get("limit") or 5)
    time_option = (payload.get("time_filter") or "week").strip().lower()

    if not subreddit:
        return jsonify({"error": "Please provide a subreddit."}), 400
    if time_option not in TIME_FILTER_MAP:
        return jsonify({"error": "time_filter must be one of: week, month, year"}), 400

    limit = max(1, min(limit, 50))

    raw_posts = fetch_top_posts(subreddit, limit, TIME_FILTER_MAP[time_option])

    posts: list[dict[str, Any]] = []
    external_urls: list[str] = []

    for item in raw_posts:
        data = item.get("data", {})
        post_id = data.get("id")
        if not post_id:
            continue

        comments = fetch_comments(subreddit, post_id)
        post_url = data.get("url") or ""

        if post_url.startswith("http") and "reddit.com" not in post_url:
            external_urls.append(post_url)

        posts.append(
            {
                "id": post_id,
                "title": data.get("title") or "",
                "score": int(data.get("score") or 0),
                "url": post_url,
                "permalink": data.get("permalink") or "",
                "selftext": data.get("selftext") or "",
                "num_comments": int(data.get("num_comments") or 0),
                "comments": [c.__dict__ for c in comments],
            }
        )

    exa_content = fetch_exa_contents(external_urls)
    for post in posts:
        post["external_content"] = exa_content.get(post["url"], "")

    analysis_text = build_analysis_text(posts)

    return jsonify(
        {
            "subreddit": subreddit,
            "time_filter": time_option,
            "count": len(posts),
            "posts": posts,
            "analysis_text": analysis_text.strip(),
            "used_exa": bool(os.getenv("EXA_API_KEY")),
        }
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
