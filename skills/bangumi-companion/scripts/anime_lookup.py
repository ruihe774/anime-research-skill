#!/usr/bin/env python3
"""Resolve an anime title (any language/abbreviation) into canonical metadata.

Queries AniList (GraphQL, POST) and Bangumi.tv (bgm.tv REST) and prints a
compact JSON summary: titles in every script, synonyms, season chain
(prequel/sequel), air dates, status, episodes, studios, key staff, main cast,
and per-episode titles/air dates/staff notes from Bangumi.

Usage:
  python3 anime_lookup.py "葬送のフリーレン"
  python3 anime_lookup.py "frieren" --episodes          # include Bangumi episode list
  python3 anime_lookup.py --anilist-id 154587 --bgm-id 400602 --episodes

Either source may be unreachable in a given environment; the script reports
which ones failed instead of crashing, so fall back to WebSearch/WebFetch.
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request

UA = "bangumi-companion-skill/1.0 (+https://claude.ai)"
TIMEOUT = 15

ANILIST_QUERY = """
query ($search: String, $id: Int) {
  Media(search: $search, id: $id, type: ANIME) {
    id idMal format status episodes duration season seasonYear source
    title { romaji english native }
    synonyms
    startDate { year month day } endDate { year month day }
    nextAiringEpisode { episode airingAt }
    studios(isMain: true) { nodes { name } }
    staff(perPage: 12, sort: RELEVANCE) { edges { role node { name { full native } } } }
    characters(perPage: 10, sort: [ROLE, RELEVANCE]) {
      edges { role node { name { full native } }
              voiceActors(language: JAPANESE) { name { full native } } }
    }
    relations { edges { relationType node { id type format status
      title { romaji native } startDate { year month } } } }
    averageScore popularity siteUrl
  }
}
"""


def http_json(url, data=None, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    body = json.dumps(data).encode() if data is not None else None
    if body is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=h, method="POST" if body else "GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def date_str(d):
    if not d or not d.get("year"):
        return None
    return "-".join(str(x).zfill(2) for x in (d.get("year"), d.get("month"), d.get("day")) if x)


def anilist(search=None, mid=None):
    variables = {"search": search} if mid is None else {"id": mid}
    res = http_json("https://graphql.anilist.co", {"query": ANILIST_QUERY, "variables": variables})
    if res.get("errors"):
        raise RuntimeError(res["errors"][0].get("message"))
    m = res["data"]["Media"]
    return {
        "anilist_id": m["id"], "mal_id": m["idMal"], "url": m["siteUrl"],
        "titles": m["title"], "synonyms": m["synonyms"],
        "format": m["format"], "status": m["status"], "source": m["source"],
        "season": f'{m["season"]} {m["seasonYear"]}' if m["season"] else None,
        "start": date_str(m["startDate"]), "end": date_str(m["endDate"]),
        "episodes": m["episodes"], "next_airing": m["nextAiringEpisode"],
        "studios": [n["name"] for n in m["studios"]["nodes"]],
        "staff": [f'{e["role"]}: {e["node"]["name"]["native"] or e["node"]["name"]["full"]}'
                  for e in m["staff"]["edges"]],
        "characters": [{
            "role": e["role"],
            "name": e["node"]["name"]["native"] or e["node"]["name"]["full"],
            "romaji": e["node"]["name"]["full"],
            "cv": [v["name"]["native"] or v["name"]["full"] for v in e["voiceActors"]],
        } for e in m["characters"]["edges"]],
        "relations": [{
            "type": e["relationType"], "anilist_id": e["node"]["id"],
            "format": e["node"]["format"], "status": e["node"]["status"],
            "title": e["node"]["title"]["native"] or e["node"]["title"]["romaji"],
            "start": date_str(e["node"]["startDate"]),
        } for e in m["relations"]["edges"] if e["node"]["type"] == "ANIME"],
        "score": m["averageScore"], "popularity": m["popularity"],
    }


def bgm_search(keyword):
    url = "https://api.bgm.tv/search/subject/" + urllib.parse.quote(keyword) + "?type=2&responseGroup=small"
    res = http_json(url)
    return [{"bgm_id": s["id"], "name": s["name"], "name_cn": s.get("name_cn")}
            for s in (res.get("list") or [])[:8]]


def bgm_subject(sid):
    s = http_json(f"https://api.bgm.tv/v0/subjects/{sid}")
    info = {}
    for item in s.get("infobox", []):
        v = item["value"]
        if isinstance(v, list):
            v = ", ".join(x.get("v", "") for x in v)
        info[item["key"]] = v
    keep = ["中文名", "别名", "话数", "放送开始", "放送星期", "官方网站", "播放电视台",
            "原作", "导演", "监督", "系列构成", "脚本", "人物设定", "音乐", "动画制作"]
    return {
        "bgm_id": s["id"], "url": f"https://bgm.tv/subject/{s['id']}",
        "name": s["name"], "name_cn": s["name_cn"], "date": s.get("date"),
        "eps": s.get("total_episodes") or s.get("eps"),
        "rating": (s.get("rating") or {}).get("score"),
        "rating_votes": (s.get("rating") or {}).get("total"),
        "rank": (s.get("rating") or {}).get("rank"),
        # Score histogram ("1".."10" -> votes) and viewer status counts (wish/collect/doing/
        # on_hold/dropped). A mean alone can't tell "uniformly mediocre" from "polarized",
        # and the dropped share shows whether people quit or stayed to complain.
        "rating_distribution": (s.get("rating") or {}).get("count"),
        "collection": s.get("collection"),
        "tags": [t["name"] for t in (s.get("tags") or [])[:12]],
        "infobox": {k: info[k] for k in keep if k in info},
    }


def bgm_characters(sid):
    """Character ids are needed for bgm.tv/character/<id> comment pages."""
    res = http_json(f"https://api.bgm.tv/v0/subjects/{sid}/characters")
    return [{"bgm_char_id": c["id"], "name": c["name"], "relation": c.get("relation"),
             "cv": ", ".join(a["name"] for a in c.get("actors") or [])}
            for c in res if c.get("relation") in ("主角", "配角")]


def mal_score(mal_id):
    """MAL blocks its API (Jikan) here, but the HTML page is reachable."""
    req = urllib.request.Request(f"https://myanimelist.net/anime/{mal_id}",
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        page = r.read().decode("utf-8", "replace")
    m = re.search(r'itemprop="ratingValue"[^>]*>([0-9.]+)', page)
    n = re.search(r'itemprop="ratingCount"[^>]*>([0-9,]+)', page)
    return {"score": m and m.group(1), "votes": n and n.group(1),
            "url": f"https://myanimelist.net/anime/{mal_id}"}


def bgm_episodes(sid):
    out, offset = [], 0
    while True:
        res = http_json(f"https://api.bgm.tv/v0/episodes?subject_id={sid}&type=0&limit=100&offset={offset}")
        for e in res["data"]:
            out.append({
                "ep": e["sort"], "airdate": e["airdate"], "name": e["name"],
                "name_cn": e["name_cn"], "comments": e["comment"],
                "discussion_url": f"https://bgm.tv/ep/{e['id']}",
                "desc": (e.get("desc") or "").strip(),
            })
        offset += 100
        if offset >= res["total"]:
            return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("title", nargs="?")
    ap.add_argument("--anilist-id", type=int)
    ap.add_argument("--bgm-id", type=int)
    ap.add_argument("--episodes", action="store_true", help="include Bangumi episode list")
    a = ap.parse_args()
    if not (a.title or a.anilist_id or a.bgm_id):
        ap.error("give a title or an id")

    out, errors = {}, {}
    if a.title or a.anilist_id:  # an empty AniList search returns an unrelated show
        try:
            out["anilist"] = anilist(a.title, a.anilist_id)
        except Exception as e:  # noqa: BLE001
            errors["anilist"] = str(e)

    bgm_id = a.bgm_id
    if not bgm_id:
        # Bangumi search works best with the native title; fall back to the raw query.
        queries = []
        if "anilist" in out and out["anilist"]["titles"].get("native"):
            queries.append(out["anilist"]["titles"]["native"])
        if a.title:
            queries.append(a.title)
        # Bangumi's legacy search returns nothing for some punctuation ("BanG Dream! X"),
        # so also try a punctuation-stripped form and the last segment of the title.
        extra = []
        for q in queries:
            plain = re.sub(r"[!！:：'’\[\]【】「」『』]", " ", q).strip()
            extra += [plain, plain.split("  ")[-1].strip()]
        originals = set(queries)
        queries += [q for q in extra if q and q not in queries]
        norm = lambda s: re.sub(r"\W", "", s or "").lower()  # noqa: E731
        targets = {norm(q) for q in originals}
        for q in queries:
            try:
                hits = bgm_search(q)
            except Exception as e:  # noqa: BLE001
                errors["bgm_search"] = str(e)
                continue
            if hits:
                out["bgm_candidates"] = hits
                # prefer an exact title match against what the user/AniList gave,
                # not against the stripped query (else sequels or compilations can win)
                exact = [h for h in hits if norm(h["name"]) in targets]
                bgm_id = (exact or hits)[0]["bgm_id"]
                break
    if bgm_id:
        try:
            out["bangumi"] = bgm_subject(bgm_id)
            out["bangumi"]["characters"] = bgm_characters(bgm_id)
            if a.episodes:
                out["bangumi"]["episodes"] = bgm_episodes(bgm_id)
        except Exception as e:  # noqa: BLE001
            errors["bangumi"] = str(e)

    mal_id = out.get("anilist", {}).get("mal_id")
    if mal_id:
        try:
            out["mal"] = mal_score(mal_id)
        except Exception as e:  # noqa: BLE001
            errors["mal"] = str(e)

    if errors:
        out["errors"] = errors
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
