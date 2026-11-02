# Wikimedia Commons API — deep dive

> Field notes for `https://commons.wikimedia.org/w/api.php`, written for the Research Monster
> and verified live on **2026-11-02** (Commons was running MediaWiki 1.48.0-wmf.1). Everything
> here is what `integrations/commons_bridge.py` is built on. Where the docs and the live
> responses disagreed, the live responses won and the difference is called out.

**Why we care.** Commons holds ~120M freely licensed files: charts, diagrams, photos, PDFs,
maps. For a project that turns research into explainers and briefings, it is the one place
to get illustrations whose license and author are machine-readable, so every image we use
can carry a correct credit line automatically.

---

## 1. The three doors into Commons

| Door | URL | Use it for |
|---|---|---|
| **Action API** (this doc) | `https://commons.wikimedia.org/w/api.php` | Everything: search, file metadata, licensing, categories, usage, structured data. Mature, rich, one endpoint. |
| **Structured Data on Commons** (Wikibase, same endpoint) | `api.php?action=wbgetentities&ids=M<pageid>` | Machine-readable statements: *depicts*, *license*, *copyright status*, *creator*. Sparser than the wikitext, but unambiguous Q-ids. |
| **REST** | `https://commons.wikimedia.org/w/rest.php/v1/file/File:<name>` and `https://api.wikimedia.org/core/v1/commons/…` | Minimal "give me the URLs and sizes" lookups. **No license fields**, so not enough on its own for reuse. |

Live REST sample (`rest.php/v1/file/File:Bitcoin_Price.webp`) returns `title`,
`file_description_url`, `latest.user`, and `preferred` / `original` / `thumbnail` blocks with
`mediatype`, `width`, `height`, `url`. Handy, but you still need the Action API for
`extmetadata`.

---

## 2. Ground rules (read before sending a single request)

### 2.1 User-Agent policy — mandatory
Wikimedia requires a **descriptive `User-Agent` with contact info**. Generic agents
(`python-requests/x`, `curl`, `Python-urllib`) and empty agents are blocked (HTTP 403), and
"bot-like behaviour with a browser UA is assumed malicious".

```
User-Agent: <client>/<version> (<url or email>; <wiki user>) <library>/<version>
User-Agent: ResearchMonsterBot/0.1 (https://github.com/crypdryp/bitcoin-vs-banks; you@example.org) python-urllib/3.13
```
Include the string `bot` so traffic is classified correctly. Browser JS that cannot set the
header should send `Api-User-Agent` instead. The bridge builds this from `COMMONS_CONTACT`.

### 2.2 Rate limits — **new in 2026**
Wikimedia rolled out per-minute limits across the Action API and REST APIs, enforced per
client identity. Exceeding them returns **HTTP 429** (or 503 when a backend is overloaded)
with a `Retry-After` header; absent the header, wait ≥ 5 s and back off exponentially.

| Client class | Limit |
|---|---|
| Unidentified (IP only, no/ generic UA) | **10 req/min** |
| Unauthenticated **with a compliant User-Agent** | **200 req/min** |
| Browser traffic, third-party wikis (InstantCommons) | 200 req/min |
| Authenticated, new/few edits | 200 req/min |
| Authenticated, established editor | 2 000 req/min |
| Bot flag / stewards / WMCS / known clients | exempt (still subject to the robot policy) |

Best practices from the same page: **≤ 3 concurrent requests**, respect `Retry-After`,
meaningful UA. The bridge is strictly serial with a 0.35 s floor between requests
(~170 req/min ceiling), honours `Retry-After`, and treats 429/503 as retryable.

### 2.3 Etiquette (API:Etiquette)
- Make requests **in series**, not in parallel.
- Batch with pipes: `titles=File:A|File:B|File:C` (50 per request for anonymous users).
- Use **generators** instead of one request per search hit.
- Send `Accept-Encoding: gzip`.
- Use **GET** for reads (cacheable, routed to the nearest datacenter).
- Non-interactive jobs should pass **`maxlag=5`**: when replication lag is high the API
  replies `error.code = "maxlag"` and you sleep, then retry.
- Prefer JSON (`format=json&formatversion=2` — v2 gives real booleans and arrays instead of
  v1's keyed objects and `""` flags).
- For bulk work use dumps / Wikimedia Enterprise, not the API.

---

## 3. Anatomy of a query

```
api.php?action=query
       &format=json&formatversion=2
       &generator=search  &gsrsearch=…  &gsrnamespace=6  &gsrlimit=10   ← what pages
       &prop=imageinfo|categories|globalusage                           ← what to attach to each page
       &iiprop=url|size|mime|mediatype|sha1|timestamp|user|extmetadata  ← imageinfo details
       &iiurlwidth=640 &iiextmetadatafilter=LicenseShortName|Artist|…   ← thumb size / trim
       &maxlag=5
```

- **`action=query`** is the workhorse. It takes a *page selector* (`titles=`, `pageids=`, or a
  `generator=`) plus any number of **`prop=`** modules (per-page data), **`list=`** modules
  (standalone lists) and **`meta=`** modules (site-level data).
- A **generator** is a `list` or `prop` module used as the page selector; its parameters get
  a `g` prefix (`gsrsearch`, `gcmtitle`, …).
- **Namespaces** that matter here: `6` = `File:`, `14` = `Category:`.
- **Limits**: most modules accept `limit` up to **50** (500 with the `apihighlimits` right).
- **Continuation**: when more results exist the response carries a `continue` object; merge
  its keys verbatim into the next request. (Live example: `{"gsroffset":3,"continue":"gsroffset||"}`.)
- Titles are **normalised** (`File:Bitcoin_Price.webp` → `File:Bitcoin Price.webp`) and the
  response reports it under `query.normalized`. Missing pages come back with `"missing": true`.
- With `generator=search`, each page carries an **`index`** field — sort by it to recover
  relevance order (the `pages` array is not guaranteed to be in rank order).

---

## 4. Modules the bridge uses

### 4.1 `prop=imageinfo` (prefix `ii`) — the file facts
`iiprop` values (from live `paraminfo`): `archivename badfile bitdepth canonicaltitle comment
commonmetadata dimensions extmetadata mediatype metadata mime parsedcomment sha1 size
thumbmime thumburls timestamp uploadwarning url user userid`. Default is `timestamp|user`.

Useful parameters:

| Param | Meaning |
|---|---|
| `iiurlwidth=N` / `iiurlheight=N` | Ask for a server-rendered thumbnail of that size → `thumburl`, `thumbwidth`, `thumbheight`, plus `responsiveUrls` (1.5x/2x) and `thumbattribs`. |
| `iiextmetadatafilter=A\|B` | Only return these extmetadata keys (keeps payloads small). |
| `iiextmetadatalanguage=en` | Language for multilingual description fields. |
| `iiextmetadatamultilang=1` | Return all languages of multilingual fields. |
| `iilimit` | Number of *revisions* of the file (default 1 = current). |
| `iilocalonly` | Skip the shared repo (only relevant on other wikis). |

A `mediatype` is one of `BITMAP DRAWING AUDIO VIDEO MULTIMEDIA OFFICE TEXT EXECUTABLE ARCHIVE
3D UNKNOWN` — the same vocabulary as the `filetype:` search keyword.

### 4.2 `extmetadata` — the licensing payload
Each key is `{ "value": …, "source": "commons-desc-page" | "commons-templates" | …, "hidden": "" }`.
`hidden` present means the field is not shown in the default UI table; it says nothing about
validity. Values from the description page are **HTML** (the author is often an `<a>` to a
user page; "Own work" is a `<span class="int-own-work">`), so strip tags before storing.

| Key | What it is | Live example |
|---|---|---|
| `LicenseShortName` | Human label | `CC BY-SA 4.0`, `CC0`, `Public domain`, `MIT` |
| `License` | Template code (from `commons-templates`) | `cc-by-sa-4.0`, `cc0`, `pd` — **absent on some files** (e.g. the MIT screenshot) |
| `LicenseUrl` | Link to the license deed | `https://creativecommons.org/licenses/by-sa/4.0/deed.en` |
| `UsageTerms` | Long license name | `Creative Commons Attribution-Share Alike 4.0` |
| `AttributionRequired` | `"true"`/`"false"` string | **missing on plain PD files** → infer from the license |
| `Attribution` | Author-specified credit text, if any | rare; when present, use it verbatim |
| `Artist` | Author (HTML) | `<a href="//commons.wikimedia.org/wiki/User:MB-one">Matti Blume</a>` |
| `Credit` | Source line (HTML) | `Own work`, a URL, "This file was derived from: …" |
| `Copyrighted` | `"True"`/`"False"` | CC0 files still say `True` (copyrighted, then waived) |
| `Restrictions` | Non-copyright restrictions | `trademarked`, `personality`, `insignia`… usually `""` |
| `ImageDescription`, `DateTimeOriginal`, `ObjectName` | Description, date, title | |
| also: `Categories`, `Assessments`, `GPSLatitude/Longitude`, `Permission`, `DateTime` | | |

For **multi-licensed** files (very common: GFDL + several CC BY-SA versions) `License`
reports **one** template; the full list is only in structured data (`P275`, see §6).

### 4.3 `list=search` / `generator=search` (prefix `sr`/`gsr`) — CirrusSearch
Parameters (live `paraminfo`): `search` (required), `namespace` (default 0 → **always set 6**),
`limit` (≤ 50), `offset`, `what` (`text|title|nearmatch`), `info` (`totalhits|suggestion|
rewrittenquery`), `prop` (`snippet size wordcount timestamp titlesnippet categorysnippet
isfilematch …`), `sort` (`relevance create_timestamp_asc/desc incoming_links_asc/desc
last_edit_asc/desc just_match none random title_natural_asc/desc user_random`),
`qiprofile`/`qdprofile` (ranking profiles incl. `mediasearch_weighted_tags`), `enablerewrites`.

**File keywords** (Help:CirrusSearch → "File properties search"), all combinable and negatable
with a leading `-`:

| Keyword | Example | Notes |
|---|---|---|
| `filetype:` | `filetype:bitmap`, `filetype:drawing` (SVG), `filetype:video` | Case-insensitive. **One value per query** — in testing `filetype:bitmap\|drawing` did not behave as an OR. |
| `filemime:` | `filemime:"image/svg+xml"`, `-filemime:pdf` | Quoted = exact; unquoted matches components. |
| `filesize:` | `filesize:>500`, `filesize:100,500` | Kilobytes. |
| `filew:` `fileh:` `fileres:` `filebits:` | `filew:>1200 fileh:>800` | Pixel measures; `fileres` = √(w·h). |
| `incategory:` | `incategory:"Cryptocurrency charts"` | Direct members only. |
| `deepcat:` | `deepcat:"Bitcoin"` | Category + subcategories (limited depth, slower). |
| `haswbstatement:` | `haswbstatement:P180=Q131723` | Structured data: files that *depict* Bitcoin. Verified live (13 SVG hits). |
| `custommatch:depicts_or_linked_from=` | `custommatch:depicts_or_linked_from=Q131723` | What the MediaSearch UI uses; broader than `haswbstatement`. Verified live. |
| `intitle:`, `"quoted phrase"`, `-term`, `insource:` | | Standard CirrusSearch. |

### 4.4 `list=categorymembers` / `generator=categorymembers` (prefix `cm`/`gcm`)
`title=Category:X` (or `pageid`), `type=file|page|subcat`, `limit` (≤ 500 anonymous for this
module), `sort=sortkey|timestamp`, `dir`, plus `start/end` and sortkey ranges for paging large
categories. Use `type=subcat` to walk the tree one level at a time (there is no server-side
recursion; `deepcat:` in search is the shortcut).

### 4.5 Other `prop`s worth attaching
- `categories` with `clshow=!hidden` — topical categories only (hides maintenance ones).
- `globalusage` (`gulimit`, `guprop=url|pageid|namespace`) — every wiki page using the file.
  A rough quality signal: `Bitcoin.svg` is used on hundreds of pages; a fresh upload on none.
- `info` with `inprop=url` — canonical URL, last revision, protection.
- `pageimages`, `revisions` (`rvprop=content` for the raw wikitext of the file page),
  `videoinfo` (`prop=videoinfo` with `vi` prefix for derivative transcodes of video).

### 4.6 `meta=siteinfo`
`siprop=general|fileextensions|restrictions|rightsinfo`. Live facts: site license is
**CC BY-SA 4.0** (for the *text*), max upload 5 GiB, allowed extensions
`tiff tif png gif jpg jpeg webp xcf pdf mid ogg ogv svg djvu stl oga flac opus wav webm mp3 midi mpg mpeg`.
Also tells you the `thumblimits`/`imagelimits` buckets the UI uses (320…2560 px).

### 4.7 `list=allimages` (prefix `ai`)
Enumerate files by name prefix, upload date, size, MIME or **SHA-1** (`aisha1=` — find whether a
file you have is already on Commons). Not used by the bridge yet.

---

## 5. File and thumbnail URLs

```
original  : https://upload.wikimedia.org/wikipedia/commons/<a>/<ab>/<File_name.ext>
thumbnail : https://thumb.wikimedia.org/wikipedia/commons/thumb/<a>/<ab>/<File_name.ext>/<W>px-<File_name.ext>[.png|.jpg]
file page : https://commons.wikimedia.org/wiki/File:<File_name.ext>       (descriptionurl)
short     : https://commons.wikimedia.org/w/index.php?curid=<pageid>     (descriptionshorturl)
```

- `<a>/<ab>` are the first one and two hex characters of the **MD5 of the filename** with
  spaces replaced by underscores. Don't compute it yourself; take `url`/`thumburl` from the API.
- **Thumbnails now live on `thumb.wikimedia.org`** (the docs still show `upload.wikimedia.org/…/thumb/`;
  both work, but the API returns the new host). When the requested width ≥ the original's
  width you get the original URL back, tagged `utm_content=thumbnail_unscaled`.
- **SVG thumbnails are PNG** (`…/960px-Bitcoin.svg.png`); PDF/DjVu pages are
  `page<N>-<W>px-<name>.jpg`; video thumbnails are JPEG frames; audio has none.
- **`utm_*` tracking parameters.** Since 2025/26 every URL the API returns ends in
  `?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original|thumbnail`.
  Harmless to fetch, but strip them before storing or citing: the canonical URL is the path.
- Hotlinking from your own site works but is discouraged; download and self-host.
- Downloads of originals can be verified against `imageinfo.sha1` (and SDC `P4092`).
  Thumbnails are re-encoded server-side, so they can't be.

---

## 6. Structured Data on Commons (SDC)

Every file page has a Wikibase **mediainfo entity** with id **`M<pageid>`** (e.g.
`File:Bitcoin Price.webp` → pageid 156272632 → `M156272632`). Read it with
`action=wbgetentities&ids=M156272632&props=labels|descriptions|claims&languages=en`.
Response: `entities.M…{ labels (captions), statements{ P… } }`. Note the key is
**`statements`** on Commons (Wikidata uses `claims`).

| Property | Meaning | Value type |
|---|---|---|
| `P180` | depicts | item (`Q131723` Bitcoin) |
| `P275` | copyright license | item(s) — **lists every license**, e.g. the Wrocław ATM photo carries `Q50829104` GFDL 1.2+, `Q19068220` CC BY-SA 2.0, `Q19113751` 2.5, `Q14946043` 3.0, `Q18199165` 4.0 |
| `P6216` | copyright status | `Q50423863` copyrighted · `Q88088423` copyrighted, dedicated to the public domain · `Q19652` public domain |
| `P170` | creator | item, **or `snaktype: somevalue`** with qualifiers `P2093` author name string, `P4174` Wikimedia username, `P2699` URL |
| `P7482` | source of file | `Q66458942` original creation by uploader |
| `P571` | inception | time |
| `P1259` | coordinates of the point of view | globe-coordinate |
| `P6731` | Commons quality assessment | `Q63348069` quality image, etc. |
| `P1163` `P4092` `P3575` `P2048` `P2049` | MIME, SHA-1, data size, height, width | string / quantity |
| `P4082` `P6757` `P6789` `P6790` `P2151` | camera, exposure, ISO, f-number, focal length | |

Q-ids are only labels on **wikidata.org** — resolve with
`https://www.wikidata.org/w/api.php?action=wbgetentities&ids=Q1|Q2&props=labels&languages=en`
(same UA rules apply). The bridge ships a small built-in label cache and can resolve the rest
with `--resolve-labels`.

**extmetadata vs SDC for licensing:** extmetadata is populated for essentially every file and
is human-readable; SDC is precise but incomplete (many files have no `P275`). Use extmetadata
as the primary source and SDC as the cross-check / for multi-license lists and `depicts`.

---

## 7. Licensing and attribution — what the data lets you do

From *Commons:Reusing content outside Wikimedia*: the Foundation owns almost none of the
content, gives **no warranty** on license data, and asks reusers to (1) confirm the license
suits the use, (2) consider non-copyright restrictions (trademark, personality rights, moral
rights), (3) download or link, (4) attribute if required, (5) state/link the license, (6)
license derivatives correctly (ShareAlike).

**Credit line** (Commons:Credit line): *Author, Title, License, via Wikimedia Commons*, with
the title linked to the file page and the license linked to the deed. The bridge emits it as
Markdown, HTML and plain text; when `Attribution` is set the author's own wording is used.

How the bridge buckets licenses (`license_class`):

| Class | From | Means for us |
|---|---|---|
| `public-domain` | `pd*`, `cc0`, "Public domain" | No legal attribution duty; credit anyway for provenance. |
| `attribution` | `cc-by-*` | Credit line required. Derivatives free. |
| `share-alike` | `cc-by-sa-*`, `gfdl*` | Credit line **and** derivatives must carry the same license — matters for infographics built on top. |
| `other` | MIT, GPL, OGL, … | Read the license page. |
| `unknown` | no license fields | Do not reuse until checked. |

`--license no-sa` (PD + CC BY) is the safe default when the output will be a derivative work
or published under a different license.

---

## 8. Response samples (abridged, live)

`generator=search&gsrsearch=bitcoin filetype:bitmap&gsrnamespace=6&prop=imageinfo&iiprop=…`
```json
{"batchcomplete": true,
 "continue": {"gsroffset": 3, "continue": "gsroffset||"},
 "query": {"pages": [
   {"pageid": 148241721, "ns": 6, "title": "File:Bitcoin, Wroclaw (P1180334).jpg", "index": 1,
    "imageinfo": [{"timestamp": "2024-05-10T22:19:12Z", "user": "MB-one",
      "size": 6258600, "width": 3534, "height": 2827,
      "thumburl": "https://thumb.wikimedia.org/wikipedia/commons/thumb/8/86/Bitcoin%2C_Wroclaw_%28P1180334%29.jpg/960px-Bitcoin%2C_Wroclaw_%28P1180334%29.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail",
      "thumbwidth": 640, "thumbheight": 512,
      "url": "https://upload.wikimedia.org/wikipedia/commons/8/86/Bitcoin%2C_Wroclaw_%28P1180334%29.jpg?utm_source=…&utm_content=original",
      "descriptionurl": "https://commons.wikimedia.org/wiki/File:Bitcoin,_Wroclaw_(P1180334).jpg",
      "sha1": "e6372e0531c522b4aa313be70fcf8dbf08f84d24", "mime": "image/jpeg",
      "extmetadata": {
        "ImageDescription": {"value": "Bitcoin ATM store in Wrocław ", "source": "commons-desc-page"},
        "Artist": {"value": "Matti Blume", "source": "commons-desc-page"},
        "Credit": {"value": "Own work", "source": "commons-desc-page"},
        "LicenseShortName": {"value": "CC BY-SA 4.0", "source": "commons-desc-page", "hidden": ""},
        "License": {"value": "cc-by-sa-4.0", "source": "commons-templates", "hidden": ""},
        "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/deed.en", "source": "commons-desc-page"},
        "AttributionRequired": {"value": "true", "source": "commons-desc-page", "hidden": ""},
        "Copyrighted": {"value": "True", "source": "commons-desc-page", "hidden": ""},
        "Restrictions": {"value": "", "source": "commons-desc-page", "hidden": ""}}}]}]}}
```
The full recordings live in `integrations/tests/fixtures/`.

---

## 9. Pitfalls we hit (so you don't)

1. **`*.wikimedia.org` is blocked from the Claude cloud sandbox.** Run the bridge locally;
   the test-suite replays fixtures so CI/sandbox runs still work.
2. **Generic/empty User-Agent → 403.** Set `COMMONS_CONTACT`.
3. **`utm_*` on every URL** — strip before storing.
4. **Thumbnail host changed** to `thumb.wikimedia.org`; don't hard-code `upload.wikimedia.org/…/thumb/`.
5. **`filetype:a|b` is not an OR**; run one `filetype:` per query or use `-filetype:` exclusions.
6. **`AttributionRequired` and `License` can be missing** (PD files, non-CC licenses) — infer.
7. **Author/credit fields are HTML.**
8. **Pages array ≠ rank order** with `generator=search`; sort by `index`.
9. **`formatversion=2`**, always — v1 returns `pages` as an object keyed by pageid and booleans as `""`.
10. **`globalusage` continues separately** (`gucontinue`), so a `continue` block can appear even
    when all your pages were returned.
11. **Multi-licensed files**: `extmetadata.License` shows one template; SDC `P275` shows all.
12. **Don't trust labels blindly**: the Wrocław photo's first `P275` value (`Q50829104`) is GFDL,
    not CC BY-SA. Resolve Q-ids before printing them.
13. **`maxlag` is for non-interactive jobs**; for an interactive lookup the extra `maxlag` error/retry
    cycle is just latency. The bridge sends it on API calls (cheap) and skips it for Wikibase calls.

---

## 10. How `commons_bridge.py` maps onto the API

| Command | Calls |
|---|---|
| `search "<q>" [--filetype --mime --min-width --depicts --category --exclude-category --sort --license]` | `generator=search` + `prop=imageinfo\|categories` (`iiurlwidth=640`, filtered `extmetadata`) |
| `category "<Name>" [--subcats]` | `generator=categorymembers&gcmtype=file` (+ `list=categorymembers&cmtype=subcat`) |
| `info File:… [--sdc --resolve-labels]` | `titles=` + `prop=imageinfo\|categories\|globalusage` (+ `wbgetentities M<pageid>`, + wikidata labels) |
| `credit File:… [--format md\|text\|html]` | same `titles=` call, prints only the credit line |
| `fetch File:… [--width N --project --tag --why --sdc --license]` | `info` → download `url` (or `thumburl` at `--width`) → SHA-1 check → `vault/50-assets/commons/` + source note in `vault/10-sources/` |
| `doctor` | `meta=siteinfo`, one `imageinfo`, one `upload.wikimedia.org` GET |

All calls go through one `api_get()` that adds `format/formatversion/maxlag`, the UA, gzip,
request spacing and 429/503/maxlag retries.

---

## 11. Sources (retrieved 2026-11-02)

- Live `paraminfo` for `query+imageinfo`, `query+search`, `query+categorymembers`; live `meta=siteinfo`.
- https://www.mediawiki.org/wiki/API:Imageinfo · https://www.mediawiki.org/wiki/API:Search ·
  https://www.mediawiki.org/wiki/API:Categorymembers · https://www.mediawiki.org/wiki/API:Query
- https://www.mediawiki.org/wiki/Help:CirrusSearch (file properties, `haswbstatement`, `deepcat`)
- https://www.mediawiki.org/wiki/API:Etiquette
- https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits (2026 limits)
- https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
- https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia ·
  https://commons.wikimedia.org/wiki/Commons:Credit_line
- https://commons.wikimedia.org/wiki/Commons:Structured_data (property usage)
- https://www.mediawiki.org/wiki/API:REST_API and `rest.php/v1/file/…` live response
