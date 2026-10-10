#!/usr/bin/env python3
"""Fetch wiki pages as clean text from sources whose *browser* pages block bots
but which have a reachable route from the shell.

Routes that work (tested Oct 2026; see references/sources.md):
  moegirl    萌娘百科 page HTML. Needs a plain/custom User-Agent: Python's default
             UA and full browser UAs get a Cloudflare 403. The API only allows
             opensearch/info/extracts; extracts drop most templated content, so
             the page HTML is the real source and extracts are the fallback.
  fandom     Any <wiki>.fandom.com via its MediaWiki API (action=parse). Page
             URLs themselves are Cloudflare-blocked; the API is not.
  wikipedia  <lang>.wikipedia.org article HTML. The API (api.php, rest_v1) is
             rate-limited (429) from this sandbox; plain article pages are not.
  namu       Namu Wiki is Cloudflare-blocked; namu.moe is a third-party mirror
             (나무모에 미러). It lags the original by days to weeks: the script
             prints the mirror's own "last edited" stamp so you can judge.

Usage:
  python3 wiki_text.py moegirl --search 芙莉               # titles, incl. disambiguations
  python3 wiki_text.py moegirl 芙莉莲                       # outline + full text
  python3 wiki_text.py moegirl 芙莉莲 --sections 简介 经历   # only matching sections
  python3 wiki_text.py fandom frieren "Episode 12"
  python3 wiki_text.py fandom frieren --search "Aura"
  python3 wiki_text.py fandom --find-wiki "frieren" "sousou no frieren"
  python3 wiki_text.py wikipedia ja "葬送のフリーレン (アニメ)" --sections 各話リスト
  python3 wiki_text.py namu "장송의 프리렌/애니메이션" --sections 평가
  ... --out FILE   saves the full text; stdout then gets only the outline
                   (and any --sections), which keeps long pages out of context.

Output starts with a header (source, URL, last-edited when known), then a
section outline with sizes, then text. Headings are rendered as #/##/###.
Moegirl 黑幕 (spoiler/joke text hidden in black) is wrapped as [黑幕:...]:
treat it as the editor's aside or a spoiler, not as plain fact.
"""
import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UA = "bangumi-companion-skill/1.1 (+https://claude.ai)"
TIMEOUT = 25

SKIP_CLASSES = ("navbox", "reference", "mw-editsection", "toc", "printfooter",
                "catlinks", "mw-references-wrap", "noprint", "metadata",
                "mw-empty-elt", "references", "reflist", "gallery", "wds-tabs",
                "vector-", "mw-jump-link", "portable-infobox-navigation")
SKIP_TAGS = {"script", "style", "noscript", "sup", "figure", "nav", "button",
             "svg", "math"}
VOID = {"br", "img", "hr", "meta", "link", "input", "wbr", "area", "base",
        "col", "source", "track", "embed", "param"}
BLOCK = {"p", "div", "li", "tr", "dd", "dt", "blockquote", "table", "ul", "ol",
         "dl", "section", "caption", "pre", "center"}


def get(url, tries=4):
    """GET with backoff: Wikipedia (429) and the Namu mirror (520) fail intermittently."""
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504, 520, 522, 524) or attempt == tries - 1:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or (3, 8, 15)[min(attempt, 2)]
            print(f"[{e.code} from {urllib.parse.urlsplit(url).netloc}; retrying in {wait}s]", file=sys.stderr)
            time.sleep(min(wait, 30))


def get_json(url):
    return json.loads(get(url))


class Html2Text(HTMLParser):
    """Minimal MediaWiki-aware HTML → text with markdown headings."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0          # >0 while inside a skipped subtree
        self.stack = []        # (tag, skipping?, heimu?)

    def _skippable(self, tag, attrs):
        if tag in SKIP_TAGS:
            return True
        a = dict(attrs)
        cls = a.get("class") or ""
        if any(c in cls for c in SKIP_CLASSES):
            return True
        if a.get("id") in ("toc", "catlinks", "footer"):
            return True
        style = (a.get("style") or "").replace(" ", "")
        return "display:none" in style

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            if tag == "br" and not self.skip:
                in_cell = any(t in ("td", "th") for t, _, _ in self.stack)
                self.out.append(" / " if in_cell else "\n")
            return
        skipping = self.skip > 0 or self._skippable(tag, attrs)
        heimu = "heimu" in (dict(attrs).get("class") or "")
        self.stack.append((tag, skipping and self.skip == 0, heimu))
        if skipping:
            self.skip += 1
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.out.append("\n\n" + "#" * max(1, int(tag[1]) - 1) + " ")
        elif tag in ("td", "th"):
            self.out.append(" | ")
        elif tag in BLOCK:
            # block elements nested inside a table cell stay on the cell's line
            in_cell = any(t in ("td", "th") for t, _, _ in self.stack[:-1])
            self.out.append(" " if in_cell else "\n")
            if tag == "li" and not in_cell:
                self.out.append("- ")
        if heimu:
            self.out.append("[黑幕:")

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        # pop to the matching tag (tolerates sloppy HTML)
        while self.stack:
            t, _, heimu = self.stack.pop()
            if self.skip:
                self.skip -= 1
            else:
                if heimu:
                    self.out.append("]")
                if re.fullmatch(r"h[1-6]", t):
                    self.out.append("\n")
                elif t in BLOCK:
                    in_cell = any(x in ("td", "th") for x, _, _ in self.stack)
                    self.out.append(" " if in_cell else "\n")
            if t == tag:
                break

    def handle_data(self, data):
        if self.skip:
            return
        tags = [t for t, _, _ in self.stack]
        if tags and tags[-1] in ("table", "tbody", "thead", "tfoot", "tr", "ul", "ol", "dl") \
                and not data.strip():
            return  # source-formatting whitespace between cells/items
        if "td" in tags or "th" in tags:
            data = data.replace("\n", " ")
        self.out.append(data)

    def text(self):
        t = "".join(self.out).replace("\xa0", " ")
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r" *\n *", "\n", t)
        t = re.sub(r"\n(?:\| *)+\n", "\n", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
        t = re.sub(r"\[(?:编辑|編集|edit|편집)\]", "", t)
        return t.strip()


def html_to_text(fragment):
    p = Html2Text()
    p.feed(fragment)
    p.close()
    return p.text()


def slice_between(page, start_pat, end_pats):
    i = page.find(start_pat)
    if i < 0:
        return None
    j = min([k for k in (page.find(e, i) for e in end_pats) if k > 0] or [len(page)])
    return page[i:j]


# ---------- per-source fetchers: each returns (url, last_edited, text) ----------

def moegirl(title):
    url = "https://zh.moegirl.org.cn/" + urllib.parse.quote(title.replace(" ", "_"))
    try:
        page = get(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(f"no Moegirl page titled {title!r}; try --search with part of the name")
        page = ""
    try:
        if not page or "Just a moment" in page[:2000]:
            raise RuntimeError("Cloudflare challenge")
        body = slice_between(page, 'id="mw-content-text"',
                             ['class="printfooter"', 'id="catlinks"', "<footer"])
        lm = re.search(r'最后编辑于\s*([^<"。]{4,40})', page)
        last = lm.group(1).strip() if lm else None
        if body:
            return url, last, html_to_text(body)
    except Exception as e:  # noqa: BLE001
        print(f"[moegirl page failed ({e}); falling back to API extract, which omits templated sections]",
              file=sys.stderr)
    api = "https://zh.moegirl.org.cn/api.php?" + urllib.parse.urlencode({
        "action": "query", "prop": "extracts|info", "explaintext": 1, "redirects": 1,
        "titles": title, "format": "json"})
    p = next(iter(get_json(api)["query"]["pages"].values()))
    ex = p.get("extract") or ""
    ex = re.sub(r"^(=+) *(.*?) *=+$", lambda m: "#" * (len(m.group(1)) - 1) + " " + m.group(2), ex, flags=re.M)
    return url, p.get("touched"), ex


def moegirl_search(q):
    api = "https://zh.moegirl.org.cn/api.php?" + urllib.parse.urlencode({
        "action": "opensearch", "search": q, "limit": 20, "format": "json"})
    return get_json(api)[1]


def fandom_api(wiki, **params):
    params.setdefault("format", "json")
    return get_json(f"https://{wiki}.fandom.com/api.php?" + urllib.parse.urlencode(params))


def fandom(wiki, title):
    d = fandom_api(wiki, action="parse", page=title, prop="text|revid", redirects=1)
    if "error" in d:
        raise RuntimeError(d["error"].get("info"))
    rev = fandom_api(wiki, action="query", prop="revisions", rvprop="timestamp",
                     titles=d["parse"]["title"])
    last = None
    for p in rev.get("query", {}).get("pages", {}).values():
        last = (p.get("revisions") or [{}])[0].get("timestamp")
    url = f"https://{wiki}.fandom.com/wiki/" + urllib.parse.quote(d["parse"]["title"].replace(" ", "_"))
    return url, last, html_to_text(d["parse"]["text"]["*"])


def fandom_search(wiki, q):
    d = fandom_api(wiki, action="query", list="search", srsearch=q, srlimit=20)
    return [f'{s["title"]}  ({s.get("wordcount", "?")} words)' for s in d["query"]["search"]]


def fandom_find_wiki(names):
    """Fandom's cross-wiki search is blocked, so probe likely subdomains."""
    cands = []
    for n in names:
        base = re.sub(r"[^a-z0-9 ]", "", n.lower()).strip()
        words = [w for w in base.split()
                 if w not in ("the", "a", "an", "of", "no", "to", "wa", "ga", "season", "anime")]
        for c in {base.replace(" ", ""), "-".join(words), "".join(words[:2]),
                  words[0] if words else "", words[-1] if words else ""}:
            if c and c not in cands:
                cands.append(c)
    found = []
    for c in cands:
        try:
            d = fandom_api(c, action="query", meta="siteinfo", siprop="general|statistics")
            g, s = d["query"]["general"], d["query"]["statistics"]
            found.append(f'{c}.fandom.com  "{g["sitename"]}"  lang={g["lang"]}  articles={s["articles"]}')
        except Exception:  # noqa: BLE001
            pass
    return found or ["no wiki found among: " + ", ".join(cands) +
                     " — WebSearch '<title> fandom wiki' to get the subdomain"]


def wikipedia(lang, title):
    url = f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
    page = get(url)
    body = slice_between(page, 'class="mw-content-ltr mw-parser-output"',
                         ['class="printfooter"', 'id="catlinks"']) or \
        slice_between(page, 'id="mw-content-text"', ['class="printfooter"', 'id="catlinks"'])
    lm = re.search(r'id="footer-info-lastmod"[^>]*>(.*?)</li>', page, re.S)
    last = html.unescape(re.sub(r"<[^>]+>", "", lm.group(1))).strip() if lm else None
    return url, last, html_to_text(body or page)


def namu(title):
    url = "https://namu.moe/w/" + urllib.parse.quote(title)
    page = get(url)
    if "Just a moment" in page[:2000]:
        raise RuntimeError("mirror is Cloudflare-blocked too")
    body = slice_between(page, "<article", ["</article>"]) or page
    lm = re.search(r"최근 수정 시각\s*:\s*([0-9:\- ]+)", html.unescape(re.sub(r"<[^>]+>", " ", page)))
    last = (lm.group(1).strip() if lm else "unknown") + f" (mirror copy, read from {url})"
    original = "https://namu.wiki/w/" + urllib.parse.quote(title)   # cite this, not the mirror
    return original, last, namu_clean(html_to_text(body))


def namu_clean(t):
    """The mirror leaks unrendered namumark (#!if, {{{#!wiki ...}}}); drop it."""
    t = re.sub(r"\{\{\{#!(?:wiki|html)[^\n]*", "", t)
    t = re.sub(r"\{\{\{[+-]?\d? ?|\}\}\}|'''", "", t)
    t = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", t)
    keep = [ln for ln in t.split("\n")
            if not re.match(r"\s*(#!if|#!wiki|<nopad>|<colbgcolor|<table)", ln)]
    t = "\n".join(keep)
    # "자세한 내용은 <page> 문서 ... 참고하십시오" → a clean pointer to the subpage
    t = re.sub(r"(자세한 내용은 .*? 문서)[\s\S]*?참고하십시오\.", r"\1 참고 (fetch that page)", t)
    return re.sub(r"\n{3,}", "\n\n", t)


# ---------- output ----------

def sections(text):
    """Split into (heading, body) pairs; first pair is the lead."""
    parts, head, buf = [], "(lead)", []
    for line in text.split("\n"):
        m = re.match(r"^(#{1,5}) (.*)", line)
        if m:
            parts.append((head, "\n".join(buf).strip()))
            head, buf = line, []
        else:
            buf.append(line)
    parts.append((head, "\n".join(buf).strip()))
    return parts


def select(parts, keys):
    """Keep sections whose heading matches a key, plus their subsections."""
    out, keep_level = [], None
    for head, body in parts:
        level = len(head) - len(head.lstrip("#")) if head.startswith("#") else 0
        if keep_level is not None and level > keep_level:
            out.append((head, body))
            continue
        keep_level = None
        if any(k.lower() in head.lower() for k in keys):
            keep_level = level
            out.append((head, body))
    return out


def emit(source, url, last, text, a):
    parts = sections(text)
    hdr = [f"source: {source}", f"url: {url}", f"last edited: {last or 'unknown'}",
           f"chars: {len(text)}"]
    outline = "\n".join(f"  {h}  [{len(b)}]" for h, b in parts if h != "(lead)" or b)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write("\n".join(hdr) + "\n\n" + text + "\n")
        hdr.append(f"saved: {a.out}")
    print("\n".join(hdr))
    print("outline:\n" + outline)
    if a.sections:
        chosen = select(parts, a.sections)
        print("\n".join(f"\n{h}\n{b}" for h, b in chosen) if chosen
              else "\n(no section matched " + ", ".join(a.sections) + ")")
    elif not a.out:
        print("\n" + text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", choices=["moegirl", "fandom", "wikipedia", "namu"])
    ap.add_argument("args", nargs="*", help="title | <wiki> <title> | <lang> <title>")
    ap.add_argument("--search", help="list matching page titles instead of fetching")
    ap.add_argument("--find-wiki", nargs="+", metavar="NAME", help="fandom: probe subdomains")
    ap.add_argument("--sections", nargs="+", metavar="KEY", help="print only sections whose heading contains KEY")
    ap.add_argument("--out", help="write the full text here")
    a = ap.parse_args()

    try:
        if a.source == "moegirl":
            if a.search:
                print("\n".join(moegirl_search(a.search)))
                return
            emit("萌娘百科 Moegirl", *moegirl(a.args[0]), a)
        elif a.source == "fandom":
            if a.find_wiki:
                print("\n".join(fandom_find_wiki(a.find_wiki)))
                return
            if a.search:
                print("\n".join(fandom_search(a.args[0], a.search)))
                return
            emit(f"Fandom ({a.args[0]})", *fandom(a.args[0], a.args[1]), a)
        elif a.source == "wikipedia":
            emit(f"Wikipedia ({a.args[0]})", *wikipedia(a.args[0], a.args[1]), a)
        elif a.source == "namu":
            emit("Namu Wiki via namu.moe mirror", *namu(a.args[0]), a)
    except IndexError:
        ap.error("missing title (fandom/wikipedia need two arguments: <wiki|lang> <title>)")
    except urllib.error.HTTPError as e:
        hint = " (page not found: check the exact title, or use --search)" if e.code == 404 else ""
        print(f"error: HTTP {e.code}{hint}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
