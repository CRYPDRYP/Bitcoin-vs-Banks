#!/usr/bin/env python3
"""
X (Twitter) post capture for the Research Monster.

`research-capture` can't read x.com directly (the site needs a logged-in
browser and blocks plain fetches). This bridge reads a post through the public
FxTwitter JSON API (https://github.com/FxEmbed/FxEmbed, unofficial, no key) and
files it as a source note in vault/10-sources/ with the full text, expanded
links, author, engagement numbers and media.

    python integrations/x_capture.py https://x.com/robiartec/status/2116945895015231669 \
        --project "Bitcoin vs Banks" --tag tooling --tag reverse-engineering

    # offline / tests: replay a recorded API response
    python integrations/x_capture.py <url> --fixture integrations/tests/fixtures/x_post_robiartec_rea.json

Notes:
- Links in long ("note") posts come back truncated by X itself
  (`http://github.com/NationalSecuri`). `--resolve-links` follows each t.co
  redirect to recover the full URL where the network allows.
- FxTwitter is a third-party service: treat it as a convenience, keep the
  original post URL as the citation, and quote only what the note shows.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VAULT = REPO_ROOT / "vault"
SOURCES = VAULT / "10-sources"
API = "https://api.fxtwitter.com"
UA = "ResearchMonsterBot/0.1 (https://github.com/crypdryp/bitcoin-vs-banks) python-urllib"

STATUS_RE = re.compile(r"(?:x\.com|twitter\.com|fxtwitter\.com|fixupx\.com)/([A-Za-z0-9_]+)/status/(\d+)")


class XCaptureError(RuntimeError):
    pass


def parse_status_url(url: str) -> tuple[str, str]:
    m = STATUS_RE.search(url)
    if not m:
        raise XCaptureError(f"Not an X status URL: {url}")
    return m.group(1), m.group(2)


def fetch_post(user: str, status_id: str) -> dict:
    req = urllib.request.Request(f"{API}/{user}/status/{status_id}",
                                 headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise XCaptureError(f"FxTwitter returned HTTP {e.code} for {user}/{status_id}") from e
    except urllib.error.URLError as e:
        raise XCaptureError(f"Could not reach {API}: {e.reason}") from e
    if data.get("code") != 200 or "tweet" not in data:
        raise XCaptureError(f"FxTwitter error: {data.get('message')!r}")
    return data


def resolve_tco(url: str) -> str:
    """Follow a t.co redirect (HEAD) and return the final URL, or the input on failure."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.geturl()
    except Exception:
        return url


def extract(data: dict, *, resolve_links: bool = False) -> dict:
    """Reduce the FxTwitter payload to the fields the note needs."""
    t = data["tweet"]
    a = t.get("author") or {}
    links: list[dict] = []
    for f in (t.get("raw_text") or {}).get("facets") or []:
        if f.get("type") != "url":
            continue
        shown = f.get("replacement") or f.get("display") or ""
        full = resolve_tco(f["original"]) if resolve_links and f.get("original") else ""
        # X cuts displayed URLs in long posts at 32 characters, so a 32-char link
        # may be incomplete (observed: "http://github.com/NationalSecuri").
        links.append({"shown": shown, "tco": f.get("original", ""), "resolved": full,
                      "truncated": not full and len(shown) >= 32})
    media = []
    for kind in ("photos", "videos"):
        for m in (t.get("media") or {}).get(kind) or []:
            media.append({"type": m.get("type", kind[:-1]), "url": m.get("url"),
                          "thumbnail": m.get("thumbnail_url"), "duration": m.get("duration")})
    posted = ""
    if t.get("created_timestamp"):
        posted = _dt.datetime.fromtimestamp(int(t["created_timestamp"]), _dt.timezone.utc).isoformat()
    return {
        "url": t.get("url") or "", "id": t.get("id"), "text": t.get("text") or "",
        "lang": t.get("lang") or "", "posted": posted, "is_note": bool(t.get("is_note_tweet")),
        "author_name": a.get("name") or "", "author_handle": a.get("screen_name") or "",
        "author_url": a.get("url") or "", "author_followers": a.get("followers"),
        "author_verified": bool((a.get("verification") or {}).get("verified")),
        "likes": t.get("likes"), "reposts": t.get("retweets"), "replies": t.get("replies"),
        "bookmarks": t.get("bookmarks"), "quotes": t.get("quotes"), "views": t.get("views"),
        "community_note": t.get("community_note"), "links": links, "media": media,
    }


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s[:60] or "post"


def _yaml(s) -> str:
    return json.dumps("" if s is None else str(s), ensure_ascii=False)


def write_note(post: dict, *, project: str, tags: list[str], title: str | None = None,
               why: str = "") -> Path:
    SOURCES.mkdir(parents=True, exist_ok=True)
    today = _dt.date.today().isoformat()
    first_line = next((ln.strip() for ln in post["text"].splitlines() if ln.strip()), "")
    title = title or f"@{post['author_handle']}: {first_line[:70]}"
    path = SOURCES / f"{today.replace('-', '')}-x-{_slug(post['author_handle'])}-{_slug(title.split(':', 1)[-1])}.md"
    all_tags = ["x-post"] + [t.lstrip("#") for t in tags if t]

    link_lines = []
    for l in post["links"]:
        if l["resolved"]:
            link_lines.append(f"- {l['resolved']}")
        else:
            flag = " _(truncated by X; resolve via the t.co link)_" if l.get("truncated") else ""
            link_lines.append(f"- {l['shown']} ({l['tco']}){flag}")
    media_lines = [f"- {m['type']}: {m['url']}" + (f" (thumb: {m['thumbnail']})" if m.get("thumbnail") else "")
                   + (f" · {m['duration']}s" if m.get("duration") else "") for m in post["media"]]
    quoted = "\n".join("> " + ln for ln in post["text"].splitlines())

    fm = (
        "---\n"
        f"title: {_yaml(title)}\n"
        f"created: {today}\n"
        "type: source\n"
        "source_type: x-post\n"
        f"url: {_yaml(post['url'])}\n"
        f"author: {_yaml(post['author_name'])}\n"
        f"author_handle: {_yaml(post['author_handle'])}\n"
        f"author_followers: {post['author_followers'] if post['author_followers'] is not None else ''}\n"
        f"posted: {_yaml(post['posted'])}\n"
        f"lang: {_yaml(post['lang'])}\n"
        f"engagement: {{likes: {post['likes'] or 0}, reposts: {post['reposts'] or 0}, replies: {post['replies'] or 0}, "
        f"bookmarks: {post['bookmarks'] or 0}, views: {post['views'] or 0}}}\n"
        f"community_note: {'true' if post['community_note'] else 'false'}\n"
        "status: captured\n"
        f"project: {_yaml(project)}\n"
        f"tags: [{', '.join(all_tags)}]\n"
        "---\n\n"
    )
    body = (
        f"# 🐦 {title}\n\n"
        f"> Post by **{post['author_name']}** (@{post['author_handle']}"
        f"{', verified' if post['author_verified'] else ''}) on {post['posted'][:10]} · "
        f"[original]({post['url']}) · captured via FxTwitter\n\n"
        "## Text\n"
        f"{quoted}\n\n"
        "## Links in the post\n" + ("\n".join(link_lines) or "- (none)") + "\n\n"
        "## Media\n" + ("\n".join(media_lines) or "- (none)") + "\n\n"
        "## Why it matters\n"
        f"- {why}\n\n"
        "## Key claims / data\n"
        "- _(what the post asserts; verify before reuse — social posts are claims, not evidence)_\n\n"
        "## Related\n"
        f"- MOC:: [[{_slug(project)}]] · [[Bitcoin-vs-Banks]]\n"
        "- See also::\n"
    )
    path.write_text(fm + body, encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Capture an X post into the vault as a source note.")
    p.add_argument("url")
    p.add_argument("--project", default="Bitcoin vs Banks")
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--title")
    p.add_argument("--why", default="")
    p.add_argument("--resolve-links", action="store_true", help="follow t.co redirects to full URLs")
    p.add_argument("--fixture", help="replay a recorded FxTwitter JSON response")
    p.add_argument("--json", action="store_true", help="print the extracted post instead of writing a note")
    args = p.parse_args(argv)
    try:
        user, sid = parse_status_url(args.url)
        data = json.loads(Path(args.fixture).read_text(encoding="utf-8")) if args.fixture else fetch_post(user, sid)
        post = extract(data, resolve_links=args.resolve_links)
        if args.json:
            print(json.dumps(post, indent=2, ensure_ascii=False))
            return 0
        path = write_note(post, project=args.project, tags=args.tag, title=args.title, why=args.why)
        print(f"• Source note: {path}")
        return 0
    except XCaptureError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
