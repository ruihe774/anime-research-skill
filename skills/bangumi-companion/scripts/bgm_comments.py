#!/usr/bin/env python3
"""Mine Bangumi (bgm.tv) discussion comments for a show, episode by episode.

Bangumi episode pages (bgm.tv/ep/<id>) and character pages (bgm.tv/character/<id>)
hold hundreds of short viewer comments posted right after each airing. They are
the most reliable reachable source for (a) what actually happened in an episode
when wikis are blocked or thin, and (b) how opinion moved week by week.

Usage:
  # per-episode heat only
  python3 bgm_comments.py 583729 --out /path/to/dir
  # plus comments mentioning a character (any of the keywords, case-insensitive)
  python3 bgm_comments.py 583729 --keywords 都子 疼肚子 tdz --character 183864 --out DIR
  # restrict to some episodes
  python3 bgm_comments.py 583729 --eps 6-9 --keywords 都子 --out DIR

Writes DIR/comments.txt (matched comments grouped by episode, plus the
character page) and prints a per-episode table: total comments, keyword hits,
hit share. Use the table as a heat/trajectory signal and read the text file for
substance. Comments are raw fan text: paraphrase, never quote abusive lines.
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.request

UA = "Mozilla/5.0 (bangumi-companion-skill)"
CMT_RE = re.compile(r'<div class="(?:message|cmt_sub_content)[^"]*">(.*?)</div>', re.S)


def get(url, as_json=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read().decode("utf-8", "replace")
    return json.loads(data) if as_json else data


def comments_from(page):
    out = []
    for c in CMT_RE.findall(page):
        s = html.unescape(re.sub(r"<[^>]+>", "", c)).strip().replace("\n", " ")
        if s:
            out.append(s)
    return out


def episodes(sid):
    res, off = [], 0
    while True:
        d = get(f"https://api.bgm.tv/v0/episodes?subject_id={sid}&type=0&limit=100&offset={off}", True)
        res += d["data"]
        off += 100
        if off >= d["total"]:
            return res


def ep_range(spec, n):
    if not spec:
        return set(range(1, n + 1))
    keep = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        keep.update(range(int(a), int(b or a) + 1))
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subject_id", type=int)
    ap.add_argument("--keywords", nargs="*", default=[], help="match any (regex ok, case-insensitive)")
    ap.add_argument("--character", type=int, help="Bangumi character id to also mine")
    ap.add_argument("--eps", help="e.g. 1-4,7")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    kw = re.compile("|".join(a.keywords), re.I) if a.keywords else None
    eps = episodes(a.subject_id)
    keep = ep_range(a.eps, len(eps))
    lines, rows = [], []

    for e in eps:
        n = int(e["sort"])
        if n not in keep:
            continue
        try:
            cs = comments_from(get(f"https://bgm.tv/ep/{e['id']}"))
        except Exception as ex:  # noqa: BLE001
            print(f"ep{n}: fetch failed ({ex})", file=sys.stderr)
            continue
        hits = [c for c in cs if kw and kw.search(c)]
        rows.append((n, e["airdate"], len(cs), len(hits)))
        lines.append(f"\n===== EP{n} ({e['airdate']}) {e['name']}: {len(cs)} comments, {len(hits)} keyword hits")
        lines += ["- " + c[:400] for c in (hits if kw else cs[:60])]
        time.sleep(0.5)  # be polite

    if a.character:
        try:
            cs = comments_from(get(f"https://bgm.tv/character/{a.character}"))
            lines.append(f"\n===== CHARACTER PAGE {a.character}: {len(cs)} comments (roughly oldest first)")
            lines += ["- " + c[:400] for c in cs]
        except Exception as ex:  # noqa: BLE001
            print(f"character page failed ({ex})", file=sys.stderr)

    path = os.path.join(a.out, "comments.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("ep\tairdate\tcomments\thits\tshare")
    for n, d, t, h in rows:
        print(f"{n}\t{d}\t{t}\t{h}\t{(h / t if t else 0):.0%}")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
