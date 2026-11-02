"""Offline tests for integrations/commons_bridge.py.

Run:  python -m unittest discover -s integrations/tests -v
No network: HTTP is stubbed, fixtures are recorded live responses (see fixtures/README.md).
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import commons_bridge as cb  # noqa: E402

FIX = HERE / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


class HelperTests(unittest.TestCase):
    def test_clean_url_strips_utm_only(self):
        u = ("https://upload.wikimedia.org/wikipedia/commons/4/46/Bitcoin.svg"
             "?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original")
        self.assertEqual(cb.clean_url(u),
                         "https://upload.wikimedia.org/wikipedia/commons/4/46/Bitcoin.svg")
        self.assertEqual(cb.clean_url("https://x/y?page=2&utm_x=1"), "https://x/y?page=2")
        self.assertIsNone(cb.clean_url(None))

    def test_strip_html(self):
        self.assertEqual(
            cb.strip_html('<a href="//commons.wikimedia.org/wiki/User:MB-one">Matti Blume</a>'),
            "Matti Blume")
        self.assertEqual(cb.strip_html("Own<br/>work &amp; more"), "Own work & more")

    def test_normalise_title(self):
        self.assertEqual(cb.normalise_title("Bitcoin.svg"), "File:Bitcoin.svg")
        self.assertEqual(cb.normalise_title("file:bitcoin_Price.webp"), "File:Bitcoin Price.webp")
        self.assertEqual(
            cb.normalise_title("https://commons.wikimedia.org/wiki/File:Bitcoin_Price.webp#x"),
            "File:Bitcoin Price.webp")

    def test_license_class(self):
        self.assertEqual(cb.license_class("cc0", "CC0"), "public-domain")
        self.assertEqual(cb.license_class("pd", "Public domain"), "public-domain")
        self.assertEqual(cb.license_class("cc-by-sa-4.0", "CC BY-SA 4.0"), "share-alike")
        self.assertEqual(cb.license_class("gfdl", "GFDL"), "share-alike")
        self.assertEqual(cb.license_class("cc-by-4.0", "CC BY 4.0"), "attribution")
        self.assertEqual(cb.license_class("", "MIT"), "other")
        self.assertEqual(cb.license_class("", ""), "unknown")

    def test_build_search_query(self):
        q = cb.build_search_query("bitcoin atm", filetype="BITMAP", mime="image/png",
                                  min_width=800, depicts="Q131723", category="Bitcoin",
                                  exclude_category="Logos")
        self.assertEqual(q, 'bitcoin atm filetype:bitmap filemime:"image/png" filew:>800 '
                            'haswbstatement:P180=Q131723 incategory:"Bitcoin" -incategory:"Logos"')

    def test_user_agent_policy_shape(self):
        with mock.patch.dict("os.environ", {"COMMONS_CONTACT": "me@example.org"}):
            ua = cb.user_agent()
        self.assertRegex(ua, r"^ResearchMonsterBot/\d+\.\d+ \(https://github\.com/\S+; me@example\.org\) "
                             r"python-urllib/\d+\.\d+$")
        self.assertIn("bot", ua.lower())


class ParseTests(unittest.TestCase):
    def setUp(self):
        pages = sorted(load("search_bitcoin.json")["query"]["pages"], key=lambda p: p["index"])
        self.files = [cb.parse_page(p) for p in pages]

    def test_ordering_by_search_index(self):
        self.assertEqual([f.title for f in self.files],
                         ["File:Bitcoin, Wroclaw (P1180334).jpg", "File:Bitcoin-core-v0.10.0.png",
                          "File:Bitcoin Price.webp"])

    def test_cc_by_sa_photo(self):
        f = self.files[0]
        self.assertEqual(f.filename, "Bitcoin, Wroclaw (P1180334).jpg")
        self.assertEqual(f.license_short, "CC BY-SA 4.0")
        self.assertEqual(f.license_code, "cc-by-sa-4.0")
        self.assertEqual(f.license_class, "share-alike")
        self.assertTrue(f.attribution_needed)
        self.assertEqual(f.artist, "Matti Blume")          # HTML anchor stripped
        self.assertEqual(f.credit, "Own work")             # span stripped
        self.assertEqual(f.description, "Bitcoin ATM store in Wrocław")
        self.assertNotIn("utm_", f.url)
        self.assertTrue(f.url.endswith("Bitcoin%2C_Wroclaw_%28P1180334%29.jpg"))
        self.assertTrue(f.thumb_url.startswith("https://thumb.wikimedia.org/"))
        self.assertEqual(f.sha1, "e6372e0531c522b4aa313be70fcf8dbf08f84d24")

    def test_cc0_chart_needs_no_attribution(self):
        f = self.files[2]
        self.assertEqual(f.license_class, "public-domain")
        self.assertFalse(f.attribution_needed)
        self.assertEqual(f.mime, "image/webp")
        self.assertEqual((f.width, f.height), (4827, 1644))

    def test_mit_screenshot_is_other(self):
        f = self.files[1]
        self.assertEqual(f.license_class, "other")
        self.assertTrue(f.attribution_needed)

    def test_credit_line_formats(self):
        f = self.files[0]
        self.assertEqual(
            f.credit_line("md"),
            "Matti Blume, [Bitcoin, Wroclaw (P1180334).jpg]"
            "(https://commons.wikimedia.org/wiki/File:Bitcoin,_Wroclaw_(P1180334).jpg), "
            "[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.en), "
            "via Wikimedia Commons")
        self.assertIn('<a href="https://creativecommons.org/licenses/by-sa/4.0/deed.en">CC BY-SA 4.0</a>',
                      f.credit_line("html"))
        self.assertTrue(f.credit_line("text").startswith(
            "Matti Blume, Bitcoin, Wroclaw (P1180334).jpg, CC BY-SA 4.0, via Wikimedia Commons"))

    def test_license_filters(self):
        self.assertEqual(len(cb._filter_license(self.files, "any")), 3)
        self.assertEqual(len(cb._filter_license(self.files, "free")), 3)
        self.assertEqual([f.title for f in cb._filter_license(self.files, "no-sa")],
                         ["File:Bitcoin Price.webp"])
        self.assertEqual([f.title for f in cb._filter_license(self.files, "pd")],
                         ["File:Bitcoin Price.webp"])
        self.assertEqual(cb._filter_license(self.files, "attribution"), [])

    def test_info_fixture_categories_usage_and_pd(self):
        pages = load("info_two_files.json")["query"]["pages"]
        svg, webp = (cb.parse_page(p) for p in pages)
        self.assertEqual(svg.license_class, "public-domain")
        self.assertFalse(svg.attribution_needed)            # no AttributionRequired key → inferred
        self.assertEqual(svg.mediatype, "DRAWING")
        self.assertEqual(svg.categories, ["Bitcoin logos"])
        self.assertEqual(svg.global_usage, 3)
        # SVG thumbnails are rasterised server-side to PNG
        self.assertTrue(svg.thumb_url.endswith("960px-Bitcoin.svg.png"))
        self.assertEqual(webp.categories[:2], ["Bitcoin", "Charts showing data through 2024"])
        self.assertEqual(webp.global_usage, 0)

    def test_to_dict_has_derived_fields(self):
        d = self.files[2].to_dict()
        self.assertIn("credit_line_md", d)
        self.assertFalse(d["attribution_needed"])


class SDCTests(unittest.TestCase):
    def test_parse_sdc(self):
        ent = load("sdc_M156272632.json")["entities"]["M156272632"]
        sdc = cb.parse_sdc(ent)
        self.assertEqual(sdc["caption"], "Chart of the growth of Bitcoin prices from 2014 to 2024.")
        self.assertEqual(sdc["depicts"], [{"qid": "Q131723", "label": "Bitcoin"}])
        self.assertEqual(sdc["license"], [{"qid": "Q6938433", "label": "Creative Commons CC0 License"}])
        self.assertEqual(sdc["copyright_status"][0]["qid"], "Q88088423")
        self.assertEqual(sdc["creator"], ["Wikideas1"])      # somevalue + author-name qualifier
        self.assertEqual(sdc["inception"], ["2024-12-04"])
        self.assertEqual(sdc["mime"], ["image/webp"])
        self.assertEqual(sdc["sha1"], ["1f81cb8b69a2730960393b934a77f177132f31e3"])


class TransportTests(unittest.TestCase):
    """api_get / _http_get with urlopen stubbed — no network."""

    def _resp(self, payload: dict, headers: dict | None = None):
        body = json.dumps(payload).encode()

        class R(io.BytesIO):
            def __init__(self):
                super().__init__(body)
                self.headers = headers or {}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return R()

    def test_api_get_builds_policy_compliant_request(self):
        seen = {}

        def fake_urlopen(req, timeout=0):
            seen["url"] = req.full_url
            seen["headers"] = dict(req.header_items())
            return self._resp({"batchcomplete": True, "query": {}})

        with mock.patch("urllib.request.urlopen", fake_urlopen), \
                mock.patch.object(cb, "MIN_REQUEST_INTERVAL", 0):
            cb.api_get({"action": "query", "titles": "File:A|File:B"})
        self.assertIn("format=json", seen["url"])
        self.assertIn("formatversion=2", seen["url"])
        self.assertIn("maxlag=5", seen["url"])
        self.assertIn("titles=File:A|File:B", seen["url"])     # pipes/colons left readable
        hdrs = {k.lower(): v for k, v in seen["headers"].items()}
        self.assertTrue(hdrs["user-agent"].startswith("ResearchMonsterBot/"))
        self.assertEqual(hdrs["accept-encoding"], "gzip")

    def test_api_error_raises(self):
        with mock.patch("urllib.request.urlopen",
                        lambda req, timeout=0: self._resp({"error": {"code": "badvalue", "info": "nope"}})), \
                mock.patch.object(cb, "MIN_REQUEST_INTERVAL", 0):
            with self.assertRaisesRegex(cb.CommonsError, "badvalue"):
                cb.api_get({"action": "query"})

    def test_429_retries_with_retry_after(self):
        calls = {"n": 0}

        def flaky(req, timeout=0):
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {"Retry-After": "7"}, io.BytesIO(b""))
            return self._resp({"ok": 1})

        slept = []
        with mock.patch("urllib.request.urlopen", flaky), \
                mock.patch.object(cb.time, "sleep", slept.append), \
                mock.patch.object(cb, "MIN_REQUEST_INTERVAL", 0):
            data = cb.api_get({"action": "query"}, maxlag=None)
        self.assertEqual(data, {"ok": 1})
        self.assertEqual(calls["n"], 2)
        self.assertIn(7.0, slept)

    def test_403_gives_user_agent_hint(self):
        def forbidden(req, timeout=0):
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(b"blocked"))
        with mock.patch("urllib.request.urlopen", forbidden), \
                mock.patch.object(cb, "MIN_REQUEST_INTERVAL", 0):
            with self.assertRaisesRegex(cb.CommonsError, "User-Agent"):
                cb.api_get({"action": "query"})


class FilingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self._patches = [
            mock.patch.object(cb, "VAULT", root),
            mock.patch.object(cb, "SOURCES", root / "10-sources"),
            mock.patch.object(cb, "ASSETS", root / "50-assets" / "commons"),
        ]
        for p in self._patches:
            p.start()
        pages = load("info_two_files.json")["query"]["pages"]
        self.svg, self.webp = (cb.parse_page(p) for p in pages)

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmp.cleanup()

    def test_download_verifies_sha1_and_names_file(self):
        payload = b"fake-webp-bytes"
        self.webp.sha1 = hashlib.sha1(payload).hexdigest()
        with mock.patch.object(cb, "_http_get", lambda url, accept="": (payload, {})):
            path = cb.download(self.webp, cb.ASSETS)
        self.assertEqual(path.name, "bitcoin-price.webp")
        self.assertEqual(path.read_bytes(), payload)

    def test_download_rejects_sha1_mismatch(self):
        with mock.patch.object(cb, "_http_get", lambda url, accept="": (b"tampered", {})):
            with self.assertRaisesRegex(cb.CommonsError, "SHA-1 mismatch"):
                cb.download(self.webp, cb.ASSETS)

    def test_write_source_note(self):
        asset = cb.ASSETS / "bitcoin-price.webp"
        asset.parent.mkdir(parents=True)
        asset.write_bytes(b"x")
        self.webp.sdc = cb.parse_sdc(load("sdc_M156272632.json")["entities"]["M156272632"])
        note = cb.write_source_note(self.webp, asset, project="Bitcoin vs Banks",
                                    tags=["#stability", "fees"], why="Price history for the volatility thread")
        text = note.read_text(encoding="utf-8")
        self.assertRegex(note.name, r"^\d{8}-commons-bitcoin-price\.md$")
        self.assertIn('title: "Chart of the growth of Bitcoin prices from 2014 to 2024."', text)
        self.assertIn("provider: wikimedia-commons", text)
        self.assertIn('license: "CC0"', text)
        self.assertIn("license_class: public-domain", text)
        self.assertIn("attribution_required: false", text)
        self.assertIn("tags: [commons, media, stability, fees]", text)
        self.assertIn("![[50-assets/commons/bitcoin-price.webp]]", text)
        self.assertIn("via Wikimedia Commons", text)
        self.assertIn("- MOC:: [[bitcoin-vs-banks]] · [[Bitcoin-vs-Banks]]", text)
        self.assertIn('"depicts"', text)                   # SDC block present
        self.assertIn("Price history for the volatility thread", text)
        self.assertIn("- [x] Attribution not legally required", text)

    def test_share_alike_note_flags_derivatives(self):
        pages = sorted(load("search_bitcoin.json")["query"]["pages"], key=lambda p: p["index"])
        photo = cb.parse_page(pages[0])
        note = cb.write_source_note(photo, None, project="Bitcoin vs Banks", tags=["access"])
        text = note.read_text(encoding="utf-8")
        self.assertIn("ShareAlike: derivatives must carry the same license.", text)
        self.assertIn("- [ ] Attribution required", text)
        self.assertIn("![Bitcoin, Wroclaw (P1180334).jpg](https://thumb.wikimedia.org/", text)


class CLITests(unittest.TestCase):
    def run_cli(self, *argv) -> str:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf), mock.patch.dict("os.environ", {"COMMONS_QUIET": "1"}):
            rc = cb.main(list(argv))
        self.assertEqual(rc, 0, buf.getvalue())
        return buf.getvalue()

    def test_search_fixture_table_and_filter(self):
        out = self.run_cli("search", "bitcoin", "--fixture", str(FIX / "search_bitcoin.json"), "--license", "no-sa")
        self.assertIn("[PD ] File:Bitcoin Price.webp", out)
        self.assertNotIn("Wroclaw", out)

    def test_search_fixture_json(self):
        out = self.run_cli("search", "bitcoin", "--fixture", str(FIX / "search_bitcoin.json"), "--json")
        data = json.loads(out)
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["title"], "File:Bitcoin, Wroclaw (P1180334).jpg")

    def test_credit_fixture(self):
        out = self.run_cli("credit", "File:Bitcoin.svg", "--fixture", str(FIX / "info_two_files.json"),
                           "--format", "text")
        self.assertIn("Grayliptrot, Bitcoin.svg, Public domain, via Wikimedia Commons", out)

    def test_fetch_license_policy_blocks_sa(self):
        buf, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", buf), mock.patch("sys.stderr", err), \
                mock.patch.dict("os.environ", {"COMMONS_QUIET": "1"}), \
                tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(cb, "SOURCES", Path(tmp)):
            rc = cb.main(["fetch", "File:Bitcoin, Wroclaw (P1180334).jpg", "--license", "no-sa",
                          "--fixture", str(FIX / "search_bitcoin.json")])
        self.assertEqual(rc, 3)
        self.assertIn("fails the --license no-sa policy", err.getvalue())


if __name__ == "__main__":
    unittest.main()
