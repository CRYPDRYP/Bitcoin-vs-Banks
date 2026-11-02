"""Offline tests for integrations/x_capture.py (fixture = real FxTwitter response, 2026-11-02)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import x_capture as xc  # noqa: E402

FIX = HERE / "fixtures" / "x_post_robiartec_rea.json"


class XCaptureTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIX.read_text(encoding="utf-8"))

    def test_parse_status_url(self):
        self.assertEqual(xc.parse_status_url("https://x.com/robiartec/status/2116945895015231669?a=1&s=19"),
                         ("robiartec", "2116945895015231669"))
        self.assertEqual(xc.parse_status_url("https://twitter.com/a_b/status/42"), ("a_b", "42"))
        with self.assertRaises(xc.XCaptureError):
            xc.parse_status_url("https://example.com/")

    def test_extract(self):
        post = xc.extract(self.data)
        self.assertEqual(post["author_handle"], "robiartec")
        self.assertEqual(post["posted"], "2026-11-01T17:30:06+00:00")
        self.assertEqual(post["lang"], "es")
        self.assertTrue(post["is_note"])
        self.assertEqual(post["likes"], 2466)
        self.assertEqual(len(post["links"]), 18)                 # 18 url facets; media facet excluded
        self.assertTrue(post["links"][1]["truncated"])            # "http://github.com/NationalSecuri"
        self.assertFalse(post["links"][0]["truncated"])
        self.assertEqual(post["links"][0]["shown"], "http://github.com/morluto/rea")
        self.assertEqual(post["media"][0]["type"], "video")
        self.assertAlmostEqual(post["media"][0]["duration"], 21.61)

    def test_resolve_links_uses_tco(self):
        with mock.patch.object(xc, "resolve_tco", lambda u: "https://github.com/NationalSecurityAgency/ghidra"
                               if u.endswith("lbaJuUnflN") else u):
            post = xc.extract(self.data, resolve_links=True)
        self.assertEqual(post["links"][1]["resolved"], "https://github.com/NationalSecurityAgency/ghidra")

    def test_write_note(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(xc, "SOURCES", Path(tmp)):
            post = xc.extract(self.data)
            path = xc.write_note(post, project="Bitcoin vs Banks", tags=["#tooling", "reverse-engineering"],
                                 why="Pointer to the REA stack")
            text = path.read_text(encoding="utf-8")
        self.assertRegex(path.name, r"^\d{8}-x-robiartec-.+\.md$")
        self.assertIn("source_type: x-post", text)
        self.assertIn('author_handle: "robiartec"', text)
        self.assertIn("tags: [x-post, tooling, reverse-engineering]", text)
        self.assertIn("> [01] núcleo de análisis", text)
        self.assertIn("http://github.com/morluto/rea (https://t.co/sE3MOSYxHG)", text)
        self.assertIn("video: https://video.twimg.com/", text)
        self.assertIn("Pointer to the REA stack", text)

    def test_cli_fixture_json(self):
        import io
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = xc.main(["https://x.com/robiartec/status/2116945895015231669", "--fixture", str(FIX), "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(buf.getvalue())["id"], "2116945895015231669")


if __name__ == "__main__":
    unittest.main()
