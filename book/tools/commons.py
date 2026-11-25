# SPDX-License-Identifier: MIT
"""Find and fetch photos on Wikimedia Commons with their license metadata (roadmap 2.3.0, M1/M4).

The sessions that write this book cannot reach Commons, so this runs in the GitHub Actions job
photos.yml. Two commands:

    python3 book/tools/commons.py search OUT "query" ["query" ...]
    python3 book/tools/commons.py fetch OUT "File:Name.jpg" ["File:Other.jpg" ...]

search writes OUT/candidates.json and prints one line per file whose license the photo policy
allows (public domain, CC0, CC BY); fetch downloads each file at most 2400 px on its long side to
OUT/ with OUT/<name>.json holding what credits.json needs. A person still reads every license page
before a photo goes into the book: this script only gathers what the page says.
"""
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
AGENT = "d2d-book-photo-fetch/1.0 (GitHub Actions; book build tooling)"
ALLOWED = {"public domain": "PD", "pd": "PD", "cc0": "CC0-1.0", "cc by 4.0": "CC-BY-4.0",
           "cc by 3.0": "CC-BY-3.0"}
WIDTH = 2400


def get(params):
    q = urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def plain(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def license_of(meta):
    short = plain(meta.get("LicenseShortName", {}).get("value", "")).lower()
    for key, lic in ALLOWED.items():
        if re.fullmatch(re.escape(key) + r"( \w+)?", short) or short == key:
            return lic
    if short.startswith("public domain") or short.startswith("pd-"):
        return "PD"
    return None


def describe(page):
    info = (page.get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata", {})
    return {
        "title": page["title"],
        "page": info.get("descriptionurl", ""),
        "license_short": plain(meta.get("LicenseShortName", {}).get("value", "")),
        "license": license_of(meta),
        "license_url": plain(meta.get("LicenseUrl", {}).get("value", "")),
        "author": plain(meta.get("Artist", {}).get("value", "")),
        "credit": plain(meta.get("Credit", {}).get("value", "")),
        "description": plain(meta.get("ImageDescription", {}).get("value", ""))[:300],
        "width": info.get("width"), "height": info.get("height"),
        "mime": info.get("mime"), "url": info.get("thumburl") or info.get("url"),
    }


def search(out, queries):
    found = []
    for q in queries:
        data = get({"action": "query", "generator": "search", "gsrnamespace": 6, "gsrlimit": 30,
                    "gsrsearch": f"{q} filetype:bitmap", "prop": "imageinfo",
                    "iiprop": "url|size|mime|extmetadata", "iiurlwidth": WIDTH})
        for page in data.get("query", {}).get("pages", []):
            d = describe(page)
            d["query"] = q
            found.append(d)
            if d["license"] and d["mime"] in ("image/jpeg", "image/png"):
                print(f"[{q}] {d['license']:10} {d['width']}x{d['height']} {d['title']} | {d['author'][:60]}")
        time.sleep(1)
    (out / "candidates.json").write_text(json.dumps(found, indent=1))


def fetch(out, titles):
    data = get({"action": "query", "titles": "|".join(titles), "prop": "imageinfo",
                "iiprop": "url|size|mime|sha1|extmetadata", "iiurlwidth": WIDTH})
    for page in data.get("query", {}).get("pages", []):
        if "imageinfo" not in page:
            print(f"missing: {page['title']}")
            continue
        d = describe(page)
        if not d["license"]:
            print(f"refused, license {d['license_short']!r}: {d['title']}")
            continue
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", page["title"].removeprefix("File:"))
        req = urllib.request.Request(d["url"], headers={"User-Agent": AGENT})
        with urllib.request.urlopen(req, timeout=120) as r:
            (out / name).write_bytes(r.read())
        d["file"] = name
        d["retrieved"] = time.strftime("%Y-%m-%d", time.gmtime())
        (out / f"{name}.json").write_text(json.dumps(d, indent=1))
        print(f"fetched {name}: {d['license']}, {d['author'][:60]}")
        time.sleep(1)


def main(argv):
    if len(argv) < 4 or argv[1] not in ("search", "fetch"):
        print(__doc__)
        return 2
    out = pathlib.Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    (search if argv[1] == "search" else fetch)(out, argv[3:])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
