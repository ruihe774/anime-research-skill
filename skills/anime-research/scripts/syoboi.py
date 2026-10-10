#!/usr/bin/env python3
"""Japanese broadcast record from しょぼいカレンダー (cal.syoboi.jp).

The site's HTML blocks some bots, but its data endpoints (json.php, db.php)
answer normally. Use it for questions the other databases answer poorly:
which station premiered an episode and when (incl. late-night "25:30" slots),
delays, double-episode airings, specials and re-runs, OP/ED usage by episode,
and the full staff/cast list as the Japanese community keeps it.

Usage:
  python3 syoboi.py search フリーレン          # → TID list (use the native title)
  python3 syoboi.py title 6776                 # episode titles, staff/cast/music, links
  python3 syoboi.py programs 6776              # first airing per episode + station list
  python3 syoboi.py programs 6776 --all        # every airing, incl. re-runs
  python3 syoboi.py programs 6776 --ch NHK BS11  # only stations whose name contains these

Times are JST. Late-night airings are also shown in broadcast notation
(e.g. 2023-10-07 01:30 → "10/06 25:30"), which is how Japanese listings and fans
date them. Flags: 新=premiere, 終=finale, 再=re-run, 注=see note.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

UA = "anime-research-skill/1.1 (+https://claude.ai)"
BASE = "https://cal.syoboi.jp"
CATS = {"0": "その他", "1": "アニメ", "2": "ラジオ", "3": "テレビ", "4": "特撮",
        "5": "アニメ関連", "6": "メモ", "7": "OVA", "8": "映画", "10": "アニメ(終了/再放送)"}


def get(path, **params):
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))


def search(kw):
    d = json.loads(get("json.php", Req="TitleSearch", Search=kw, Limit=30))
    rows = sorted((d.get("Titles") or {}).values(),
                  key=lambda t: (t.get("FirstYear") or "", t.get("FirstMonth") or ""))
    return [f'TID {t["TID"]:>5}  {t["Title"]}  ({t.get("FirstYear")}-{(t.get("FirstMonth") or "").zfill(2)}, '
            f'{CATS.get(t.get("Cat"), t.get("Cat"))})' for t in rows]


def clean_comment(c):
    """Syoboi comments use a light wiki markup: *heading, :key:value, [[text url]]."""
    out = []
    for ln in (c or "").splitlines():
        ln = re.sub(r"\[\[(.+?) (https?://\S+)\]\]", r"\1 <\2>", ln)
        ln = re.sub(r"\[\[(.+?)\]\]", r"\1", ln)
        if ln.startswith("**"):
            out.append("  " + ln[2:])
        elif ln.startswith("*"):
            out.append("\n## " + ln[1:])
        elif ln.startswith(":"):
            parts = ln[1:].split(":", 1)
            out.append(f"- {parts[0]}: {parts[1]}" if len(parts) == 2 else "- " + parts[0])
        elif ln.startswith("-"):
            out.append("- " + ln[1:])
        elif ln.strip():
            out.append(ln)
    return "\n".join(out).strip()


def title(tid):
    root = ET.fromstring(get("db.php", Command="TitleLookup", TID=tid))
    it = root.find(".//TitleItem")
    if it is None:
        raise SystemExit(f"no title with TID {tid}")
    f = {c.tag: (c.text or "") for c in it}
    eps = re.findall(r"^\*(\d+)\*(.*)$", f.get("SubTitles", ""), re.M)
    lines = [
        f'# {f["Title"]}  (TID {tid})',
        f'url: {BASE}/tid/{tid}',
        f'reading: {f.get("TitleYomi")}   short: {f.get("ShortTitle") or "-"}   EN: {f.get("TitleEN") or "-"}',
        f'category: {CATS.get(f.get("Cat"), f.get("Cat"))}   first aired: {f.get("FirstYear")}-{f.get("FirstMonth", "").zfill(2)}'
        f' on {f.get("FirstCh") or "?"}   ended: {f.get("FirstEndYear") or "-"}-{(f.get("FirstEndMonth") or "").zfill(2)}',
        f'syoboi user points: {f.get("UserPoint")} (rank {f.get("UserPointRank")}) — a rough popularity signal among Japanese schedule-trackers',
        f'record last updated: {f.get("LastUpdate")}',
        "", "## Episode titles",
    ]
    lines += [f"  #{int(n)} {t}" for n, t in eps] or ["  (none listed)"]
    lines += ["", clean_comment(f.get("Comment"))]
    return "\n".join(lines)


def channels():
    root = ET.fromstring(get("db.php", Command="ChLookup"))
    return {c.findtext("ChID"): c.findtext("ChName") for c in root.iter("ChItem")}


def late_night(dt):
    """01:30 on the 7th → '10/06 25:30' (Japanese broadcast-day convention, day ends 05:00)."""
    if dt.hour < 5:
        prev = dt - timedelta(days=1)
        return f"{prev:%m/%d} {dt.hour + 24}:{dt:%M}"
    return f"{dt:%m/%d} {dt:%H:%M}"


def flags(v):
    v = int(v or 0)
    return "".join(s for bit, s in ((2, "新"), (4, "終"), (8, "再"), (1, "注")) if v & bit)


def programs(tid, show_all=False, ch_filter=None):
    root = ET.fromstring(get("db.php", Command="ProgLookup", TID=tid, JOIN="SubTitles"))
    chs = channels()
    progs = []
    for p in root.iter("ProgItem"):
        if p.findtext("Deleted") == "1":
            continue
        st = datetime.strptime(p.findtext("StTime"), "%Y-%m-%d %H:%M:%S")
        ed = datetime.strptime(p.findtext("EdTime"), "%Y-%m-%d %H:%M:%S")
        ch = chs.get(p.findtext("ChID"), "ch" + p.findtext("ChID"))
        if ch_filter and not any(k.lower() in ch.lower() for k in ch_filter):
            continue
        progs.append({
            "st": st, "min": int((ed - st).total_seconds() // 60), "ch": ch,
            "count": p.findtext("Count") or "", "flag": flags(p.findtext("Flag")),
            "sub": p.findtext("STSubTitle") or p.findtext("SubTitle") or "",
            "note": (p.findtext("ProgComment") or "").strip(),
        })
    progs.sort(key=lambda x: x["st"])
    now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=9)  # JST, to mark future airings
    out = [f"{len(progs)} airings found for TID {tid} (JST)."]

    def row(x):
        n = f'#{x["count"]}' if x["count"] else (x["sub"] or "special")
        note = f'  — {x["note"][:120]}' if x["note"] else ""
        if x["st"] > now:
            note = "  (scheduled)" + note
        return (f'  {x["st"]:%Y-%m-%d %a %H:%M} [{late_night(x["st"])}] {x["min"]:>3}min  '
                f'{n:<8} {x["flag"]:<3} {x["ch"]}{note}')

    if show_all:
        out += [row(x) for x in progs]
        return "\n".join(out)

    # premiere of each numbered episode (earliest non-rerun airing) + specials
    # Multi-episode blocks (e.g. a 2-hour premiere) have no Count but a subtitle
    # like "#1～#4"; they are the real premiere of those episodes.
    first, specials = {}, []
    for x in progs:
        if "再" in x["flag"]:
            continue
        counts = [x["count"]] if x["count"] else []
        m = re.search(r"#(\d+)\s*[～〜~\-ー]\s*#?(\d+)", x["sub"])
        if not counts and m:
            counts = [str(n) for n in range(int(m.group(1)), int(m.group(2)) + 1)]
        for c in counts:
            first.setdefault(c, x)
        if not counts:
            specials.append(x)
    out.append("\n## First airing of each episode")
    printed = set()
    for k in sorted(first, key=lambda k: int(k)):
        if id(first[k]) not in printed:   # a multi-episode block prints once
            printed.add(id(first[k]))
            out.append(row(first[k]))
    if specials:
        out.append("\n## Unnumbered airings (specials, multi-episode blocks, pre-broadcast programs)")
        out += [row(x) for x in specials]
    # station summary: first non-rerun airing per channel, shows the rollout and delays
    seen = {}
    for x in progs:
        if "再" not in x["flag"] and x["count"]:
            seen.setdefault(x["ch"], x)
    out.append("\n## Stations (first numbered airing on each; later dates = delayed/regional/streaming)")
    out += [f'  {x["st"]:%Y-%m-%d %a} {late_night(x["st"])}  #{x["count"]}  {ch}'
            for ch, x in sorted(seen.items(), key=lambda kv: kv[1]["st"])]
    reruns = sum("再" in x["flag"] for x in progs)
    if reruns:
        out.append(f"\n({reruns} re-run airings hidden; use --all to see them)")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("keyword")
    t = sub.add_parser("title")
    t.add_argument("tid", type=int)
    p = sub.add_parser("programs")
    p.add_argument("tid", type=int)
    p.add_argument("--all", action="store_true", help="every airing incl. re-runs")
    p.add_argument("--ch", nargs="+", help="only stations whose name contains any of these")
    a = ap.parse_args()
    try:
        if a.cmd == "search":
            print("\n".join(search(a.keyword)) or "no match — try the native Japanese title or a shorter keyword")
        elif a.cmd == "title":
            print(title(a.tid))
        else:
            print(programs(a.tid, a.all, a.ch))
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
