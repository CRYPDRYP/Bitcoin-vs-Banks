# Recorded Commons API responses

Captured live from `https://commons.wikimedia.org/w/api.php` on 2026-11-02 and trimmed.
They let the test-suite (and `commons_bridge.py --fixture …`) run offline, and they
document the real response shapes the bridge is written against — including the
`utm_*` query strings on file URLs and thumbnails served from `thumb.wikimedia.org`.

| File | Request |
|---|---|
| `search_bitcoin.json` | `generator=search&gsrsearch=bitcoin filetype:bitmap&gsrnamespace=6&prop=imageinfo&iiprop=…extmetadata&iiurlwidth=640` |
| `info_two_files.json` | `titles=File:Bitcoin_Price.webp\|File:Bitcoin.svg&prop=imageinfo\|categories\|globalusage\|info` |
| `sdc_M156272632.json` | `action=wbgetentities&ids=M156272632` (Structured Data on Commons for *Bitcoin Price.webp*) |
