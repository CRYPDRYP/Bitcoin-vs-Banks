#!/usr/bin/env python3
"""
Wikimedia Commons bridge for the Research Monster.

Finds, vets and files *properly licensed* media (charts, diagrams, photos,
PDFs) from Wikimedia Commons so explainers, briefings and posts can be
illustrated without a licensing headache. Every file that enters the vault
arrives with its license, author and a ready-to-paste credit line.

It talks to the MediaWiki Action API at https://commons.wikimedia.org/w/api.php
(plus the Wikibase/Structured-Data-on-Commons modules on the same endpoint)
using only the Python standard library. See docs/wikimedia-commons-api.md for
the full API deep dive that this module is built on.

Typical use (from Claude Code, in plain language -> these commands):

    # find candidate images for a topic, vetted by license
    python integrations/commons_bridge.py search "bitcoin atm" --filetype bitmap --license no-sa

    # everything in a Commons category (files only)
    python integrations/commons_bridge.py category "Cryptocurrency charts"

    # full metadata + credit line for one file (add --sdc for structured data)
    python integrations/commons_bridge.py info "File:Bitcoin Price.webp" --sdc

    # download it into the vault and write a source note with the credit line
    python integrations/commons_bridge.py fetch "File:Bitcoin Price.webp" \
        --project "Bitcoin vs Banks" --tag stability --width 1280

Etiquette baked in (per Wikimedia's User-Agent policy, API:Etiquette and the
2026 rate limits): descriptive User-Agent with contact info, serial requests
with a minimum spacing, gzip, `maxlag`, and Retry-After-aware backoff on
429/503. Set COMMONS_CONTACT="you@example.org" (or a URL) so the UA carries
*your* contact, which is what the policy asks for.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import gzip
import hashlib
import html
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths & constants
# --------------------------------------------------------------------------- #

REPO_ROOT = Path(__file__).resolve().parent.parent
VAULT = REPO_ROOT / "vault"
SOURCES = VAULT / "10-sources"
ASSETS = VAULT / "50-assets" / "commons"

API = "https://commons.wikimedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
COMMONS_FILE_NS = 6

VERSION = "0.1"
REPO_URL = "https://github.com/crypdryp/bitcoin-vs-banks"

# Wikimedia's 2026 limit for "User-Agent only" clients is 200 req/min and at
# most 3 concurrent requests. We run strictly serially and space requests so a
# burst never gets near the cap.
MIN_REQUEST_INTERVAL = 0.35  # seconds  (~170 req/min ceiling)
MAX_RETRIES = 4
DEFAULT_MAXLAG = 5

# extmetadata keys we always ask for (iiextmetadatafilter keeps responses small).
EXTMETADATA_KEYS = [
    "LicenseShortName", "License", "LicenseUrl", "UsageTerms",
    "AttributionRequired", "Attribution", "Artist", "Credit", "Copyrighted",
    "Restrictions", "ImageDescription", "DateTimeOriginal", "ObjectName",
]

# Structured Data on Commons (Wikibase) property ids worth reading.
SDC_PROPS = {
    "P180": "depicts",
    "P275": "license",
    "P6216": "copyright_status",
    "P170": "creator",
    "P7482": "source_of_file",
    "P571": "inception",
    "P1259": "coordinates_of_viewpoint",
    "P6731": "quality_assessment",
    "P4092": "sha1",
    "P1163": "mime",
}

# Small built-in label cache for the Q-ids that show up constantly in file
# statements, so `info --sdc` is readable even before any Wikidata lookup.
# (Verified against wikidata.org on 2026-11-02.)
QID_LABELS = {
    "Q131723": "Bitcoin",
    "Q6938433": "Creative Commons CC0 License",
    "Q50423863": "copyrighted",
    "Q88088423": "copyrighted, dedicated to the public domain by copyright holder",
    "Q19652": "public domain",
    "Q50829104": "GNU Free Documentation License, version 1.2 or later",
    "Q19068220": "Creative Commons Attribution-ShareAlike 2.0 Generic",
    "Q19113751": "Creative Commons Attribution-ShareAlike 2.5 Generic",
    "Q14946043": "Creative Commons Attribution-ShareAlike 3.0 Unported",
    "Q18199165": "Creative Commons Attribution-ShareAlike 4.0 International",
    "Q20007257": "Creative Commons Attribution 4.0 International",
    "Q14947546": "Creative Commons Attribution 3.0 Unported",
    "Q66458942": "original creation by uploader",
    "Q63348069": "Commons quality image",
}


class CommonsError(RuntimeError):
    """Raised for transport failures, API errors, or bad input."""


# --------------------------------------------------------------------------- #
# Transport
# --------------------------------------------------------------------------- #

_last_request_at = 0.0
_warned_no_contact = False


def user_agent() -> str:
    """Build a User-Agent that satisfies the Wikimedia User-Agent policy.

    Format: <client>/<version> (<contact>) <library>/<version>. Including the
    word "bot" lets Wikimedia classify the traffic correctly.
    """
    global _warned_no_contact
    contact = os.environ.get("COMMONS_CONTACT", "").strip()
    if contact:
        contact_part = f"{REPO_URL}; {contact}"
    else:
        contact_part = REPO_URL
        if not _warned_no_contact and os.environ.get("COMMONS_QUIET") != "1":
            print("note: set COMMONS_CONTACT=you@example.org so the User-Agent "
                  "carries your contact info (Wikimedia policy).", file=sys.stderr)
            _warned_no_contact = True
    py = ".".join(map(str, sys.version_info[:2]))
    return f"ResearchMonsterBot/{VERSION} ({contact_part}) python-urllib/{py}"


def _throttle() -> None:
    global _last_request_at
    wait = MIN_REQUEST_INTERVAL - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def _http_get(url: str, *, accept: str = "application/json") -> tuple[bytes, dict]:
    """GET with the policy-compliant headers, gzip, and 429/503 backoff."""
    delay = 2.0
    for attempt in range(MAX_RETRIES + 1):
        _throttle()
        req = urllib.request.Request(url, headers={
            "User-Agent": user_agent(),
            "Accept": accept,
            "Accept-Encoding": "gzip",
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
                headers = dict(resp.headers.items())
                if headers.get("Content-Encoding", "").lower() == "gzip":
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                return raw, headers
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < MAX_RETRIES:
                retry_after = e.headers.get("Retry-After")
                try:
                    sleep_for = float(retry_after) if retry_after else delay
                except ValueError:
                    sleep_for = delay
                print(f"  ({e.code} from Commons; waiting {sleep_for:.0f}s before retry)",
                      file=sys.stderr)
                time.sleep(max(sleep_for, 5.0))
                delay *= 2
                continue
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            if e.code == 403:
                raise CommonsError(
                    "403 from Wikimedia. This usually means the User-Agent was "
                    "rejected; set COMMONS_CONTACT and retry.") from e
            raise CommonsError(f"HTTP {e.code} for {url}\n{body}") from e
        except urllib.error.URLError as e:
            raise CommonsError(
                f"Could not reach {urllib.parse.urlsplit(url).netloc}: {e.reason}. "
                "If you are in a sandbox, *.wikimedia.org may be blocked; run this "
                "from your own machine.") from e
    raise CommonsError("Gave up after repeated 429/503 responses.")


def api_get(params: dict, *, endpoint: str = API, maxlag: int | None = DEFAULT_MAXLAG) -> dict:
    """One Action API call. Adds format/formatversion/maxlag; raises on API errors.

    `maxlag` makes the request a good citizen: when replication lag is high the
    API answers with a `maxlag` error and we retry after the suggested pause.
    """
    base = {"format": "json", "formatversion": "2"}
    if maxlag is not None:
        base["maxlag"] = str(maxlag)
    merged = {**base, **{k: v for k, v in params.items() if v is not None}}
    url = f"{endpoint}?{urllib.parse.urlencode(merged, safe='|:')}"
    for attempt in range(MAX_RETRIES + 1):
        raw, headers = _http_get(url)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise CommonsError(f"Non-JSON response from {endpoint}: {raw[:200]!r}") from e
        err = data.get("error")
        if err and err.get("code") == "maxlag" and attempt < MAX_RETRIES:
            pause = float(headers.get("Retry-After", 5))
            print(f"  (Commons replication lag; waiting {pause:.0f}s)", file=sys.stderr)
            time.sleep(pause)
            continue
        if err:
            raise CommonsError(f"API error {err.get('code')}: {err.get('info')}")
        for w in (data.get("warnings") or {}).values():
            msg = w.get("warnings") if isinstance(w, dict) else w
            if msg and os.environ.get("COMMONS_QUIET") != "1":
                print(f"  (api warning) {msg}", file=sys.stderr)
        return data
    raise CommonsError("Gave up waiting for replication lag to clear.")


def api_get_all(params: dict, *, max_pages: int = 10) -> list[dict]:
    """Follow `continue` and return every page of a query (bounded)."""
    pages: list[dict] = []
    cont: dict = {}
    for _ in range(max_pages):
        data = api_get({**params, **cont})
        pages.append(data)
        cont = data.get("continue") or {}
        if not cont:
            break
    return pages


# --------------------------------------------------------------------------- #
# Normalisation helpers
# --------------------------------------------------------------------------- #


def clean_url(url: str | None) -> str | None:
    """Drop the `utm_*` tracking parameters Commons now appends to file URLs.

    Since 2025/2026 the API returns e.g. `...Bitcoin.svg?utm_source=commons...`.
    The canonical, stable URL is the path without them, so that is what we file.
    """
    if not url:
        return url
    parts = urllib.parse.urlsplit(url)
    keep = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
            if not k.startswith("utm_")]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(keep)))


def strip_html(text: str | None) -> str:
    """Flatten the HTML Commons puts in Artist/Credit/Description fields."""
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "untitled"


def normalise_title(title: str) -> str:
    """Accept 'Bitcoin.svg', 'File:Bitcoin.svg', a Commons URL, or 'Bitcoin_Price.webp'."""
    t = title.strip()
    m = re.search(r"commons\.wikimedia\.org/wiki/(File:[^?#]+)", t)
    if m:
        t = urllib.parse.unquote(m.group(1))
    t = t.replace("_", " ")
    if not t.lower().startswith("file:"):
        t = "File:" + t
    return "File:" + t[5:].strip()[:1].upper() + t[5:].strip()[1:]


def license_class(code: str | None, short: str | None) -> str:
    """Bucket a license into what matters for reuse decisions."""
    c = (code or "").lower()
    s = (short or "").lower()
    if c.startswith("pd") or "public domain" in s or c == "cc0" or s == "cc0":
        return "public-domain"
    if "-sa" in c or "sharealike" in s or "share alike" in s or "share-alike" in s \
            or c.startswith("gfdl") or "gfdl" in s:
        return "share-alike"
    if c.startswith("cc-by") or s.startswith("cc by"):
        return "attribution"
    if c or s:
        return "other"
    return "unknown"


LICENSE_FILTERS = {
    "any": {"public-domain", "attribution", "share-alike", "other", "unknown"},
    "free": {"public-domain", "attribution", "share-alike", "other"},
    "no-sa": {"public-domain", "attribution"},
    "attribution": {"attribution"},
    "pd": {"public-domain"},
}


@dataclass
class MediaFile:
    title: str
    pageid: int | None = None
    filename: str = ""
    description_url: str = ""
    url: str = ""
    thumb_url: str = ""
    width: int | None = None
    height: int | None = None
    size: int | None = None
    mime: str = ""
    mediatype: str = ""
    sha1: str = ""
    uploader: str = ""
    uploaded: str = ""
    description: str = ""
    date: str = ""
    artist: str = ""
    credit: str = ""
    attribution: str = ""
    license_short: str = ""
    license_code: str = ""
    license_url: str = ""
    usage_terms: str = ""
    attribution_required: bool | None = None
    copyrighted: bool | None = None
    restrictions: str = ""
    license_class: str = "unknown"
    categories: list[str] = field(default_factory=list)
    global_usage: int | None = None
    sdc: dict = field(default_factory=dict)
    search_snippet: str = ""

    # ---- derived -------------------------------------------------------- #
    @property
    def attribution_needed(self) -> bool:
        if self.attribution_required is not None:
            return self.attribution_required
        return self.license_class not in ("public-domain",)

    def credit_line(self, fmt: str = "md") -> str:
        """A Commons:Credit-line style attribution: Author, Title, License, via Commons."""
        author = self.attribution or self.artist or self.uploader or "Unknown author"
        lic = self.license_short or "license unknown"
        title = self.filename or self.title
        if fmt == "text":
            parts = [author, title, lic, "via Wikimedia Commons"]
            line = ", ".join(parts)
            if self.license_url:
                line += f" ({self.license_url})"
            return line + f" — {self.description_url}" if self.description_url else line
        if fmt == "html":
            t = f'<a href="{html.escape(self.description_url)}">{html.escape(title)}</a>'
            l_ = (f'<a href="{html.escape(self.license_url)}">{html.escape(lic)}</a>'
                  if self.license_url else html.escape(lic))
            return f"{html.escape(author)}, {t}, {l_}, via Wikimedia Commons"
        t = f"[{title}]({self.description_url})" if self.description_url else title
        l_ = f"[{lic}]({self.license_url})" if self.license_url else lic
        return f"{author}, {t}, {l_}, via Wikimedia Commons"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["attribution_needed"] = self.attribution_needed
        d["credit_line_md"] = self.credit_line("md")
        return d


def _bool(v) -> bool | None:
    if v is None:
        return None
    return str(v).strip().lower() in ("true", "1", "yes")


def parse_page(page: dict) -> MediaFile:
    """Turn one `query.pages[]` entry (imageinfo + optional extras) into a MediaFile."""
    title = page.get("title", "")
    mf = MediaFile(title=title, pageid=page.get("pageid"),
                   filename=title[5:] if title.lower().startswith("file:") else title)
    ii = (page.get("imageinfo") or [{}])[0]
    ext = ii.get("extmetadata") or {}

    def em(key: str) -> str:
        v = ext.get(key)
        return (v or {}).get("value", "") if isinstance(v, dict) else (v or "")

    mf.description_url = clean_url(ii.get("descriptionurl")) or ""
    mf.url = clean_url(ii.get("url")) or ""
    mf.thumb_url = clean_url(ii.get("thumburl")) or ""
    mf.width, mf.height, mf.size = ii.get("width"), ii.get("height"), ii.get("size")
    mf.mime = ii.get("mime", "")
    mf.mediatype = ii.get("mediatype", "")
    mf.sha1 = ii.get("sha1", "")
    mf.uploader = ii.get("user", "")
    mf.uploaded = ii.get("timestamp", "")
    mf.description = strip_html(em("ImageDescription"))
    mf.date = strip_html(em("DateTimeOriginal"))
    mf.artist = strip_html(em("Artist"))
    mf.credit = strip_html(em("Credit"))
    mf.attribution = strip_html(em("Attribution"))
    mf.license_short = strip_html(em("LicenseShortName"))
    mf.license_code = em("License")
    mf.license_url = em("LicenseUrl")
    mf.usage_terms = strip_html(em("UsageTerms"))
    mf.attribution_required = _bool(em("AttributionRequired") or None)
    mf.copyrighted = _bool(em("Copyrighted") or None)
    mf.restrictions = strip_html(em("Restrictions"))
    mf.license_class = license_class(mf.license_code, mf.license_short)
    mf.categories = [c["title"].removeprefix("Category:")
                     for c in page.get("categories") or []]
    if "globalusage" in page:
        mf.global_usage = len(page["globalusage"])
    if page.get("snippet"):
        mf.search_snippet = strip_html(page["snippet"])
    return mf


def parse_sdc(entity: dict) -> dict:
    """Reduce a `wbgetentities` mediainfo entity to the statements we care about."""
    out: dict = {"id": entity.get("id"), "caption": ""}
    labels = entity.get("labels") or {}
    if "en" in labels:
        out["caption"] = labels["en"].get("value", "")
    for pid, name in SDC_PROPS.items():
        vals = []
        for st in (entity.get("statements") or entity.get("claims") or {}).get(pid, []):
            snak = st.get("mainsnak", {})
            dv = snak.get("datavalue", {}).get("value")
            if snak.get("snaktype") != "value":
                # e.g. creator = "somevalue" with an author-name qualifier
                q = st.get("qualifiers", {})
                name_q = (q.get("P2093") or q.get("P4174") or [{}])[0]
                dv = name_q.get("datavalue", {}).get("value")
                if dv:
                    vals.append(str(dv))
                continue
            if isinstance(dv, dict) and "id" in dv:
                qid = dv["id"]
                vals.append({"qid": qid, "label": QID_LABELS.get(qid)})
            elif isinstance(dv, dict) and "time" in dv:
                vals.append(dv["time"].lstrip("+")[:10])
            elif isinstance(dv, dict) and "latitude" in dv:
                vals.append(f"{dv['latitude']},{dv['longitude']}")
            elif isinstance(dv, dict) and "amount" in dv:
                vals.append(dv["amount"].lstrip("+"))
            else:
                vals.append(dv)
        if vals:
            out[name] = vals
    return out


# --------------------------------------------------------------------------- #
# Query builders
# --------------------------------------------------------------------------- #

FILE_PROPS = {
    "prop": "imageinfo|categories",
    "iiprop": "url|size|mime|mediatype|sha1|timestamp|user|extmetadata",
    "iiextmetadatafilter": "|".join(EXTMETADATA_KEYS),
    "iiextmetadatalanguage": "en",
    "clshow": "!hidden",
    "cllimit": "20",
}


def build_search_query(text: str, *, filetype: str | None = None, mime: str | None = None,
                       min_width: int | None = None, depicts: str | None = None,
                       category: str | None = None, exclude_category: str | None = None) -> str:
    """Compose a CirrusSearch query string using Commons' file keywords."""
    parts = [text.strip()] if text and text.strip() else []
    if filetype:
        parts.append(f"filetype:{filetype.lower()}")
    if mime:
        parts.append(f'filemime:"{mime}"')
    if min_width:
        parts.append(f"filew:>{int(min_width)}")
    if depicts:
        parts.append(f"haswbstatement:P180={depicts}")
    if category:
        parts.append(f'incategory:"{category}"')
    if exclude_category:
        parts.append(f'-incategory:"{exclude_category}"')
    return " ".join(parts)


def search(text: str, *, limit: int = 10, sort: str = "relevance", **kw) -> list[MediaFile]:
    q = build_search_query(text, **kw)
    data = api_get({
        "action": "query",
        "generator": "search",
        "gsrsearch": q,
        "gsrnamespace": str(COMMONS_FILE_NS),
        "gsrlimit": str(min(max(limit, 1), 50)),
        "gsrsort": sort,
        "gsrprop": "snippet",
        **FILE_PROPS,
        "iiurlwidth": "640",
    })
    pages = (data.get("query") or {}).get("pages") or []
    pages.sort(key=lambda p: p.get("index", 0))
    return [parse_page(p) for p in pages]


def category_files(category: str, *, limit: int = 20) -> list[MediaFile]:
    cat = category if category.lower().startswith("category:") else f"Category:{category}"
    data = api_get({
        "action": "query",
        "generator": "categorymembers",
        "gcmtitle": cat,
        "gcmtype": "file",
        "gcmlimit": str(min(max(limit, 1), 50)),
        **FILE_PROPS,
        "iiurlwidth": "640",
    })
    return [parse_page(p) for p in (data.get("query") or {}).get("pages") or []]


def subcategories(category: str, *, limit: int = 50) -> list[str]:
    cat = category if category.lower().startswith("category:") else f"Category:{category}"
    data = api_get({
        "action": "query", "list": "categorymembers", "cmtitle": cat,
        "cmtype": "subcat", "cmlimit": str(min(max(limit, 1), 500)),
    })
    return [m["title"].removeprefix("Category:")
            for m in (data.get("query") or {}).get("categorymembers") or []]


def file_info(titles: list[str], *, width: int | None = None,
              with_usage: bool = True) -> list[MediaFile]:
    params = {
        "action": "query",
        "titles": "|".join(normalise_title(t) for t in titles),
        **FILE_PROPS,
        "iiurlwidth": str(width) if width else "640",
    }
    if with_usage:
        params["prop"] += "|globalusage"
        params["gulimit"] = "50"
        params["guprop"] = "url"
    data = api_get(params)
    out = []
    for p in (data.get("query") or {}).get("pages") or []:
        if p.get("missing"):
            raise CommonsError(f"No such file on Commons: {p.get('title')}")
        out.append(parse_page(p))
    return out


def structured_data(mf: MediaFile, *, resolve_labels: bool = False) -> dict:
    """Read the file's Structured Data (Wikibase mediainfo entity M<pageid>)."""
    if not mf.pageid:
        raise CommonsError("Need a pageid to look up structured data.")
    data = api_get({"action": "wbgetentities", "ids": f"M{mf.pageid}",
                    "props": "labels|descriptions|claims", "languages": "en"},
                   maxlag=None)
    ent = (data.get("entities") or {}).get(f"M{mf.pageid}") or {}
    sdc = parse_sdc(ent)
    if resolve_labels:
        missing = sorted({v["qid"] for vals in sdc.values() if isinstance(vals, list)
                          for v in vals if isinstance(v, dict) and not v.get("label")})
        if missing:
            wd = api_get({"action": "wbgetentities", "ids": "|".join(missing[:50]),
                          "props": "labels", "languages": "en"},
                         endpoint=WIKIDATA_API, maxlag=None)
            for qid, e in (wd.get("entities") or {}).items():
                lbl = ((e.get("labels") or {}).get("en") or {}).get("value")
                if lbl:
                    QID_LABELS[qid] = lbl
            for vals in sdc.values():
                if isinstance(vals, list):
                    for v in vals:
                        if isinstance(v, dict) and not v.get("label"):
                            v["label"] = QID_LABELS.get(v["qid"])
    mf.sdc = sdc
    return sdc


# --------------------------------------------------------------------------- #
# Download + vault filing
# --------------------------------------------------------------------------- #


def download(mf: MediaFile, dest_dir: Path = ASSETS, *, width: int | None = None,
             verify: bool = True) -> Path:
    """Download the original (or a server-rendered thumbnail of `width`) into the vault.

    The original's SHA-1 is checked against the API's `sha1`, which is a free
    integrity check. Thumbnails are re-encoded server-side so they can't be
    verified that way; SVG/PDF/video thumbnails come back as PNG/JPEG.
    """
    url = mf.url
    if width:
        # Ask the API for a thumbnail of exactly this width (thumb_url is 640 by default).
        info = file_info([mf.title], width=width, with_usage=False)[0]
        url = info.thumb_url or mf.url
    if not url:
        raise CommonsError(f"No download URL for {mf.title}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = _slug(Path(mf.filename).stem)
    ext = Path(urllib.parse.urlsplit(url).path).suffix.lower() or ".bin"
    suffix = f"-{width}px" if width else ""
    path = dest_dir / f"{stem}{suffix}{ext}"

    raw, _ = _http_get(url, accept="*/*")
    digest = hashlib.sha1(raw).hexdigest()
    if verify and not width and mf.sha1 and digest != mf.sha1:
        raise CommonsError(f"SHA-1 mismatch for {mf.title}: expected {mf.sha1}, got {digest}")
    if path.exists() and hashlib.sha1(path.read_bytes()).hexdigest() != digest:
        path = dest_dir / f"{stem}{suffix}-{digest[:8]}{ext}"
    path.write_bytes(raw)
    return path


def _yaml_str(s: str) -> str:
    return json.dumps(s or "", ensure_ascii=False)


def write_source_note(mf: MediaFile, asset_path: Path | None, *, project: str,
                      tags: list[str], why: str = "") -> Path:
    """File a Commons media source note in vault/10-sources/ (media template)."""
    SOURCES.mkdir(parents=True, exist_ok=True)
    today = _dt.date.today().isoformat()
    stem = _slug(Path(mf.filename).stem)
    note_path = SOURCES / f"{today.replace('-', '')}-commons-{stem}.md"

    rel_asset = ""
    embed = ""
    if asset_path:
        try:
            rel_asset = asset_path.relative_to(VAULT).as_posix()
        except ValueError:
            rel_asset = asset_path.as_posix()
        embed = f"![[{rel_asset}]]"
    elif mf.thumb_url:
        embed = f"![{mf.filename}]({mf.thumb_url})"

    all_tags = ["commons", "media"] + [t.lstrip("#") for t in tags if t]
    title = (mf.sdc.get("caption") if mf.sdc else "") or mf.description[:80] or mf.filename
    checklist_sa = "x" if mf.license_class != "share-alike" else " "
    checklist_restr = "x" if not mf.restrictions else " "

    fm = (
        "---\n"
        f"title: {_yaml_str(title)}\n"
        f"created: {today}\n"
        "type: source\n"
        "source_type: media\n"
        "provider: wikimedia-commons\n"
        f"commons_title: {_yaml_str(mf.title)}\n"
        f"pageid: {mf.pageid or ''}\n"
        f"url: {_yaml_str(mf.description_url)}\n"
        f"file_url: {_yaml_str(mf.url)}\n"
        f"path: {_yaml_str(rel_asset)}\n"
        f"author: {_yaml_str(mf.artist or mf.uploader)}\n"
        f"license: {_yaml_str(mf.license_short)}\n"
        f"license_code: {_yaml_str(mf.license_code)}\n"
        f"license_url: {_yaml_str(mf.license_url)}\n"
        f"license_class: {mf.license_class}\n"
        f"attribution_required: {str(mf.attribution_needed).lower()}\n"
        f"restrictions: {_yaml_str(mf.restrictions)}\n"
        f"mime: {_yaml_str(mf.mime)}\n"
        f"dimensions: {_yaml_str(f'{mf.width}x{mf.height}' if mf.width else '')}\n"
        f"sha1: {_yaml_str(mf.sha1)}\n"
        f"date_original: {_yaml_str(mf.date)}\n"
        "status: captured\n"
        f"project: {_yaml_str(project)}\n"
        f"tags: [{', '.join(all_tags)}]\n"
        "---\n\n"
    )
    cats = "\n".join(f"- {c}" for c in mf.categories) or "- (none)"
    sdc_block = ""
    if mf.sdc:
        sdc_block = ("## Structured data (Commons)\n```json\n"
                     + json.dumps(mf.sdc, indent=2, ensure_ascii=False) + "\n```\n\n")
    body = (
        f"# 🖼️ {title}\n\n"
        f"{embed}\n\n"
        f"> {mf.description or '(no description on Commons)'}\n\n"
        "## Credit line (paste wherever the file is used)\n"
        f"{mf.credit_line('md')}\n\n"
        f"Plain text: `{mf.credit_line('text')}`\n\n"
        "## Why it matters\n"
        f"- {why or ''}\n\n"
        "## Reuse checklist\n"
        f"- [{checklist_sa}] License suits the use — **{mf.license_short or 'unknown'}** "
        f"({mf.license_class})."
        + (" ShareAlike: derivatives must carry the same license.\n"
           if mf.license_class == "share-alike" else "\n")
        + f"- [{'x' if not mf.attribution_needed else ' '}] Attribution "
        + ("not legally required (public domain / CC0) — still credit for provenance.\n"
           if not mf.attribution_needed else "required — use the credit line above.\n")
        + f"- [{checklist_restr}] Non-copyright restrictions: "
        + (f"**{mf.restrictions}**\n" if mf.restrictions else "none flagged on Commons.\n")
        + "- [ ] Verified the file page yourself (Commons gives no warranty on license data).\n\n"
        "## Metadata\n"
        "| Field | Value |\n|---|---|\n"
        f"| File | [{mf.title}]({mf.description_url}) |\n"
        f"| Author | {mf.artist or '—'} |\n"
        f"| Source / credit | {mf.credit or '—'} |\n"
        f"| Uploaded by | {mf.uploader or '—'} ({mf.uploaded or '—'}) |\n"
        f"| Type | {mf.mime} · {mf.mediatype} · {mf.width}×{mf.height} · {mf.size or '?'} bytes |\n"
        f"| Used on Wikimedia pages | {mf.global_usage if mf.global_usage is not None else '—'} |\n\n"
        f"## Categories\n{cats}\n\n"
        f"{sdc_block}"
        "## Related\n"
        f"- MOC:: [[{_slug(project)}]] · [[Bitcoin-vs-Banks]]\n"
        "- See also::\n"
    )
    note_path.write_text(fm + body, encoding="utf-8")
    return note_path


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _filter_license(files: list[MediaFile], policy: str) -> list[MediaFile]:
    allowed = LICENSE_FILTERS[policy]
    return [f for f in files if f.license_class in allowed]


def _print_table(files: list[MediaFile]) -> None:
    if not files:
        print("(no results)")
        return
    for i, f in enumerate(files, 1):
        dims = f"{f.width}×{f.height}" if f.width else "?"
        flag = {"public-domain": "PD ", "attribution": "BY ", "share-alike": "SA ",
                "other": "?? ", "unknown": "?? "}[f.license_class]
        restr = f"  ⚠ {f.restrictions}" if f.restrictions else ""
        print(f"{i:>2}. [{flag}] {f.title}")
        print(f"      {f.license_short or 'license unknown'} · {f.artist or f.uploader or '?'} "
              f"· {f.mime} · {dims}{restr}")
        if f.description:
            print(f"      {f.description[:110]}")
        print(f"      {f.description_url}")


def _emit(args, files: list[MediaFile]) -> None:
    if args.json:
        print(json.dumps([f.to_dict() for f in files], indent=2, ensure_ascii=False))
    else:
        _print_table(files)


def _load_fixture(args) -> dict | None:
    """--fixture lets you replay a recorded API response offline (tests/demos)."""
    if getattr(args, "fixture", None):
        return json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    return None


def cmd_search(args) -> int:
    fx = _load_fixture(args)
    if fx:
        pages = sorted((fx.get("query") or {}).get("pages") or [], key=lambda p: p.get("index", 0))
        files = [parse_page(p) for p in pages]
    else:
        files = search(args.query, limit=args.limit, sort=args.sort, filetype=args.filetype,
                       mime=args.mime, min_width=args.min_width, depicts=args.depicts,
                       category=args.category, exclude_category=args.exclude_category)
    files = _filter_license(files, args.license)
    if not args.json:
        q = build_search_query(args.query, filetype=args.filetype, mime=args.mime,
                               min_width=args.min_width, depicts=args.depicts,
                               category=args.category, exclude_category=args.exclude_category)
        print(f"Commons search: {q!r}  (license filter: {args.license})\n")
    _emit(args, files)
    return 0


def cmd_category(args) -> int:
    fx = _load_fixture(args)
    if fx:
        files = [parse_page(p) for p in (fx.get("query") or {}).get("pages") or []]
    else:
        files = category_files(args.category, limit=args.limit)
        if args.subcats and not args.json:
            subs = subcategories(args.category)
            if subs:
                print("Subcategories: " + ", ".join(subs) + "\n")
    _emit(args, _filter_license(files, args.license))
    return 0


def cmd_info(args) -> int:
    fx = _load_fixture(args)
    if fx:
        files = [parse_page(p) for p in (fx.get("query") or {}).get("pages") or []]
    else:
        files = file_info(args.titles)
        if args.sdc:
            for f in files:
                structured_data(f, resolve_labels=args.resolve_labels)
    if args.json:
        print(json.dumps([f.to_dict() for f in files], indent=2, ensure_ascii=False))
        return 0
    for f in files:
        print(f"{f.title}\n  {f.description_url}")
        print(f"  license: {f.license_short or '?'} [{f.license_code or '-'}] "
              f"({f.license_class}; attribution {'required' if f.attribution_needed else 'optional'})")
        print(f"  author: {f.artist or '?'}   credit: {f.credit or '-'}")
        print(f"  type: {f.mime} {f.mediatype} {f.width}×{f.height} {f.size} bytes  sha1 {f.sha1}")
        print(f"  original: {f.url}")
        if f.restrictions:
            print(f"  ⚠ restrictions: {f.restrictions}")
        if f.categories:
            print(f"  categories: {', '.join(f.categories)}")
        if f.global_usage is not None:
            print(f"  used on {f.global_usage} Wikimedia pages (sampled, max 50)")
        if f.sdc:
            print("  structured data:")
            for k, v in f.sdc.items():
                if k in ("id", "caption") or not v:
                    continue
                vv = ", ".join((x.get("label") or x["qid"]) if isinstance(x, dict) else str(x) for x in v)
                print(f"    {k}: {vv}")
            if f.sdc.get("caption"):
                print(f"    caption: {f.sdc['caption']}")
        print(f"  credit: {f.credit_line('md')}\n")
    return 0


def cmd_credit(args) -> int:
    fx = _load_fixture(args)
    files = ([parse_page(p) for p in (fx.get("query") or {}).get("pages") or []]
             if fx else file_info([args.title], with_usage=False))
    for f in files:
        print(f.credit_line(args.format))
    return 0


def cmd_fetch(args) -> int:
    fx = _load_fixture(args)
    files = ([parse_page(p) for p in (fx.get("query") or {}).get("pages") or []]
             if fx else file_info([args.title]))
    mf = files[0]
    if args.license != "any" and mf.license_class not in LICENSE_FILTERS[args.license]:
        print(f"✗ {mf.title} is {mf.license_short or 'unlicensed/unknown'} "
              f"({mf.license_class}), which fails the --license {args.license} policy.",
              file=sys.stderr)
        return 3
    if args.sdc and not fx:
        structured_data(mf, resolve_labels=True)
    asset = None
    if not args.no_download:
        if fx:
            print("• (fixture mode: skipping download)")
        else:
            print(f"• Downloading {mf.title}" + (f" @ {args.width}px" if args.width else " (original)"))
            asset = download(mf, Path(args.dest) if args.dest else ASSETS, width=args.width)
            print(f"  saved {asset}")
    note = write_source_note(mf, asset, project=args.project, tags=args.tag, why=args.why)
    print(f"• Source note: {note}")
    print(f"• Credit line: {mf.credit_line('md')}")
    if mf.license_class == "share-alike":
        print("  ⚠ ShareAlike license: anything you derive from this must carry the same license.")
    if mf.restrictions:
        print(f"  ⚠ Non-copyright restrictions flagged: {mf.restrictions}")
    return 0


def cmd_doctor(args) -> int:
    ok = True
    print("Wikimedia Commons bridge — doctor")
    contact = os.environ.get("COMMONS_CONTACT", "").strip()
    print(f"  {'✓' if contact else '•'} COMMONS_CONTACT {'set' if contact else 'not set (recommended)'}")
    os.environ["COMMONS_QUIET"] = "1"
    print(f"  • User-Agent: {user_agent()}")
    try:
        data = api_get({"action": "query", "meta": "siteinfo", "siprop": "general"}, maxlag=None)
        g = data["query"]["general"]
        print(f"  ✓ api.php reachable — {g.get('sitename')} on {g.get('generator')} "
              f"(server time {g.get('time')})")
    except CommonsError as e:
        ok = False
        print(f"  ✗ api.php: {e}")
    try:
        f = file_info(["File:Bitcoin.svg"], with_usage=False)[0]
        print(f"  ✓ imageinfo+extmetadata OK — File:Bitcoin.svg is {f.license_short} ({f.license_class})")
    except CommonsError as e:
        ok = False
        print(f"  ✗ imageinfo: {e}")
    try:
        raw, _ = _http_get("https://upload.wikimedia.org/wikipedia/commons/4/46/Bitcoin.svg",
                           accept="*/*")
        print(f"  ✓ upload.wikimedia.org reachable ({len(raw)} bytes)")
    except CommonsError as e:
        ok = False
        print(f"  ✗ upload.wikimedia.org: {e}")
    print(f"  • assets dir: {ASSETS}")
    print(f"  • notes dir:  {SOURCES}")
    print("✓ ready" if ok else "✗ fix the items above")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="commons_bridge.py",
        description="Find, vet and file licensed media from Wikimedia Commons into the vault.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, *, license_default="free"):
        sp.add_argument("--json", action="store_true", help="machine-readable output")
        sp.add_argument("--license", choices=sorted(LICENSE_FILTERS), default=license_default,
                        help="license policy: any | free (default) | no-sa (PD + CC BY) | "
                             "attribution (CC BY only) | pd (public domain / CC0)")
        sp.add_argument("--fixture", help="replay a recorded API JSON response (offline)")

    s = sub.add_parser("search", help="full-text search of Commons files (CirrusSearch)")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--sort", default="relevance",
                   choices=["relevance", "incoming_links_desc", "create_timestamp_desc",
                            "last_edit_desc", "random"])
    s.add_argument("--filetype", choices=["bitmap", "drawing", "video", "audio", "office",
                                          "multimedia", "3d"],
                   help="Commons media type (drawing = SVG and other vector)")
    s.add_argument("--mime", help='exact MIME, e.g. image/svg+xml')
    s.add_argument("--min-width", type=int, help="minimum pixel width (filew:>N)")
    s.add_argument("--depicts", help="Wikidata Q-id the file must 'depict' (P180), e.g. Q131723")
    s.add_argument("--category", help="must be in this category (incategory:)")
    s.add_argument("--exclude-category", help="must NOT be in this category")
    common(s)
    s.set_defaults(func=cmd_search)

    c = sub.add_parser("category", help="list the files in a Commons category")
    c.add_argument("category")
    c.add_argument("--limit", type=int, default=20)
    c.add_argument("--subcats", action="store_true", help="also print subcategories")
    common(c)
    c.set_defaults(func=cmd_category)

    i = sub.add_parser("info", help="full metadata + credit line for one or more files")
    i.add_argument("titles", nargs="+")
    i.add_argument("--sdc", action="store_true", help="also read Structured Data on Commons")
    i.add_argument("--resolve-labels", action="store_true",
                   help="resolve unknown Q-ids via wikidata.org (one extra request)")
    common(i, license_default="any")
    i.set_defaults(func=cmd_info)

    cr = sub.add_parser("credit", help="print just the attribution line")
    cr.add_argument("title")
    cr.add_argument("--format", choices=["md", "text", "html"], default="md")
    common(cr, license_default="any")
    cr.set_defaults(func=cmd_credit)

    f = sub.add_parser("fetch", help="download into vault/50-assets/ and write a source note")
    f.add_argument("title")
    f.add_argument("--project", default="Bitcoin vs Banks")
    f.add_argument("--tag", action="append", default=[], help="topic tag(s), e.g. --tag fees")
    f.add_argument("--why", default="", help="one line on why this file matters")
    f.add_argument("--width", type=int, help="download a thumbnail of this width instead of the original")
    f.add_argument("--dest", help="override the assets directory")
    f.add_argument("--sdc", action="store_true", help="include structured data in the note")
    f.add_argument("--no-download", action="store_true", help="write the note only (embeds the thumb URL)")
    common(f, license_default="free")
    f.set_defaults(func=cmd_fetch)

    d = sub.add_parser("doctor", help="check connectivity, User-Agent and vault paths")
    d.set_defaults(func=cmd_doctor)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CommonsError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
