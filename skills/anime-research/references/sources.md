# Source map

Which site to use for what. The access notes record what worked from the Claude sandbox when this skill was last tested (9 Oct 2026). Sites change, so if one fails, use WebSearch snippets or the next source in the list rather than retrying through other tools.

## Access cheat sheet

**The User-Agent matters.** Cloudflare-fronted sites here block Python's default `Python-urllib/3.x` and spoofed full browser strings. They let through curl's default and a descriptive custom UA such as `anime-research-skill/1.1`. The scripts set one. Moegirl returns 403 to Python's default UA, which is the only reason it was once marked "blocked". Douban returns 418 to it, but stays blocked with any UA because of its login wall.

| Reachable from the shell | Reachable only via a specific route (use the script) | Blocked: use search snippets |
|---|---|---|
| AniList GraphQL (POST) | **萌娘百科 Moegirl**: page HTML with a custom UA (`wiki_text.py moegirl`). API allows only `opensearch`, `prop=info`, `prop=extracts`; `parse`, `revisions`, `list=search` and `action=raw` return "Unauthorized API call" | Reddit (incl. `.json` and `old.reddit`; API access needs Reddit's approval) |
| Bangumi API `api.bgm.tv` | **Fandom**: `<wiki>.fandom.com/api.php` (`action=parse`, `list=search`, `meta=siteinfo`) (`wiki_text.py fandom`). `/wiki/` pages, `?action=raw` and cross-wiki search are Cloudflare-blocked | X/Twitter (API needs a paid token; syndication endpoints 429) |
| Bangumi HTML: `bgm.tv/ep/<id>`, `bgm.tv/character/<id>`, `bgm.tv/subject/<id>` | **Wikipedia**: article pages and `index.php?action=raw` (`wiki_text.py wikipedia`). `api.php` and `rest_v1` are 429 from this sandbox's shared IP; article pages hit 429 intermittently, so retry | Namu Wiki itself (Cloudflare challenge on every path) |
| MyAnimeList HTML pages | **しょぼいカレンダー**: `json.php` and `db.php` (`syoboi.py`). The HTML pages also load | Douban: subject pages redirect to login, reviews need login, search gives no results |
| Filmarks, Annict (URL-encode the query) | **Namu Wiki via the namu.moe mirror** (`wiki_text.py namu`): third-party, unrendered markup is stripped by the script, lags the original. Check the printed date | Jikan API (opens the connection, never answers) and the official MAL API (needs a client ID) |
| Anime Corner, news sites | | Pixiv百科事典, ニコニコ大百科 |

WebFetch reaches the Bangumi API and most news and review sites. It returns a model-written summary of the page, so details and names can drift. Long features may also be labeled as sponsored (PR) content; note that when citing them as criticism.

## Contents
1. Metadata databases
2. Air dates and schedules
3. Plot / episode detail
4. Japanese communities
5. Chinese-speaking communities
6. Korean communities
7. English / global communities
8. Critics, commentators, production info
9. News and announcements

## 1. Metadata databases

| Source | Good for | Access |
|---|---|---|
| AniList | Canonical titles (native/Romaji/English), synonyms in many languages, relations (season chain), staff, characters + CVs, airing schedule | GraphQL POST `https://graphql.anilist.co` (used by the script). WebFetch can't POST; use the script or search `anilist.co/anime/<id>` |
| Bangumi 番组计划 (bgm.tv) | Chinese titles, aliases, very complete staff infobox, per-episode official synopses + per-episode staff, per-episode discussion, ratings from a Chinese core-fan audience | REST GET works in both script and WebFetch: `api.bgm.tv/search/subject/<kw>?type=2`, `api.bgm.tv/v0/subjects/<id>`, `/v0/subjects/<id>/persons`, `/v0/subjects/<id>/characters`, `/v0/episodes?subject_id=<id>&type=0` |
| MyAnimeList | English-speaking scores, rank, member count, English synopses | HTML pages are reachable; the lookup script reads score and votes from `myanimelist.net/anime/<idMal>`. Jikan doesn't answer, and the official API needs a client ID |
| AniDB | Exhaustive episode/staff data, OVAs and specials | Often rate-limited; use for verification via search |
| Annict (annict.com) | Japanese watcher counts and per-episode Japanese reviews | Web pages; search `annict <title>` |
| Wikipedia (ja/zh/en/ko) | Episode lists with titles and air dates, production background, broadcast stations, 反響・評価 | `wiki_text.py wikipedia <lang> "<title>"`. The anime often has its own article, e.g. `<title> (アニメ)`, or the en `List of <title> episodes`. ja.wikipedia is usually the most complete for staff and broadcast info |

## 2. Air dates and schedules
- Official site "ON AIR" / "放送情報" page — the ground truth for TV stations and times.
- しょぼいカレンダー (cal.syoboi.jp): the complete broadcast record per station, with re-runs, 特番 interruptions and multi-episode blocks flagged; episode titles; staff/cast/OP-ED with episode ranges. Use `syoboi.py search|title|programs`. Its raw endpoints are `json.php?Req=TitleSearch&Search=<kw>`, `db.php?Command=TitleLookup&TID=<tid>` and `db.php?Command=ProgLookup&TID=<tid>&JOIN=SubTitles`.
- AniList `nextAiringEpisode`, Bangumi `airdate` per episode.
- Note: Japanese late-night slots ("25:30") belong to the previous calendar day in listings.

## 3. Plot / episode detail
- **Fandom wikis** (`<series>.fandom.com`): per-episode pages with Synopsis, a long scene-by-scene Plot, Episode Notes (anime-original content, chapters adapted) and an infobox with per-episode staff. Fetch with `wiki_text.py fandom` and find the subdomain with `--find-wiki`.
- **Namu Wiki** (namu.wiki), Korean: often the most exhaustive per-episode and per-character pages, with trivia and adaptation differences. Large works are split into subpages (`<제목>/애니메이션`, `/줄거리`, `/평가`, `/원작과의 차이점`). Read it via the namu.moe mirror with `wiki_text.py namu`; the mirror copy can be weeks old, so for airing shows check its date.
- **萌娘百科 Moegirl** (zh.moegirl.org.cn): character pages with plot history (经历概要), nicknames, memes, 萌战 results and CV info; work pages with STAFF/CAST and a per-episode staff table (各话标题). Use `wiki_text.py moegirl`, with `--search` to resolve titles. 黑幕 text is editor asides or spoilers.
- **Pixiv百科事典** (dic.pixiv.net), Japanese: character and fandom terminology, nicknames. Blocked; search snippets only.
- **ニコニコ大百科** (dic.nicovideo.jp), Japanese: nicknames, memes, episode reactions. Blocked; search snippets only.
- **Bangumi episode pages** (`bgm.tv/ep/<id>`): Chinese viewer comments, often 100–300 per episode for a mid-size show, describing key scenes within hours of airing. This is the most reliable reachable plot source for new or niche shows; mine them with `scripts/bgm_comments.py`. Comments that quote or reply to each other repeat text, so count distinct commenters, not lines.
- **Per-episode review columns**: Anime Corner runs weekly episode pieces for many seasonal shows (search `animecorner <title> episode N`); ANN reviews the bigger ones.
- **r/anime episode threads** — search `"<English or Romaji title>" "Episode N discussion" reddit`; first comments often summarize.
- **Japanese recap blogs** — search `<title> <N>話 感想` or `あらすじ ネタバレ`.

## 4. Japanese communities

Japanese fan reaction to new shows is the hardest region to reach: X is blocked, and WebSearch tends to return news articles rather than 感想 posts. Try, in order:
1. Filmarks and Annict pages via the shell (scores, short reviews)
2. まとめ sites through search, e.g. `<title> <N>話 反応` or `<略称> 実況`
3. note.com essays: `<title> 感想 note`
4. ニコニコ大百科 for nicknames (search snippets; blocked for fetching)
5. ja Wikipedia 反響・評価 via `wiki_text.py` for press reception and ratings/awards

If all of these come up empty, say Japanese reaction wasn't reachable.

- **X (Twitter)** — real-time reaction; trending hashtags are usually the official `#<略称>` tag. Search results often surface via news roundups rather than direct fetch.
- **5ch / まとめブログ** (e.g. アニメ速報 sites, やらおん, あにまんch) — blunt core-fan reaction; skew negative and meme-heavy, so treat as one segment, not "Japan".
- **Filmarks Anime** — Japanese star ratings and short reviews, general audience.
- **Annict** — per-episode ratings and reviews from dedicated watchers.
- **ニコニコ** — comment-on-video culture; 一挙放送 rankings.
- **Yahoo!知恵袋 / note.com** — longer personal essays and interpretations.
- Sales and popularity indicators: BD/DVD sales (less meaningful post-2020), streaming rankings (dアニメストア, ABEMA, U-NEXT weekly rankings), Oricon for music.

## 5. Chinese-speaking communities
- **Bangumi (bgm.tv)**: core otaku audience; scores are strict and respected. Use the per-episode discussion pages plus each character's page (`bgm.tv/character/<id>`, ids from the lookup script). Character-page comments accumulate in rough chronological order, so they show a character's popularity arc. Expect heavy use of nicknames and franchise in-jokes, and some abusive posts.
- **Bilibili** — 番剧 score (if licensed in mainland), 短评/长评, 弹幕 culture, analysis videos (UP主). Licensing affects which shows have pages.
- **Douban 豆瓣**: broader audience score and long reviews (影评). Blocked by a login wall. The score often appears in the rating template on Namu's `/평가` page; otherwise use search snippets.
- **NGA 动漫区, 贴吧, 知乎** — discussion threads; 知乎 for long analytical answers.
- **巴哈姆特 (Taiwan)** — 動畫瘋 view counts/ratings and 哈啦區 boards; reflects Taiwanese audience.
- Hong Kong: forums like LIHKG are smaller sources; mention only if relevant.

## 6. Korean communities
- **Namu Wiki**: the `<제목>/애니메이션/평가` page summarizes Korean (and some global) reaction per season, 방영 전/방영 후. Its rating template carries Laftel, Watcha, Douban, MAL, IMDb and Filmarks scores. Read it via `wiki_text.py namu`.
- **DC Inside** (애니메이션 갤러리, series-specific galleries), **Ruliweb** — fan boards.
- **Laftel** — Korean streaming platform ratings.

## 7. English / global communities
- **r/anime** episode threads (with Karma rankings by Anime Corner/"Anime Trending" style trackers), series subreddits.
- **MyAnimeList** scores and forum threads.
- **Anime Corner** weekly polls, **Anime Trending** awards — popularity snapshots skewed to English-speaking fans.
- **YouTube** analysis creators — cite by channel name as commentators.

## 8. Critics, commentators, production info
- **English press**: Anime News Network (episode reviews, This Week in Anime), Polygon, Crunchyroll News features, Anime Feminist, Otaku USA.
- **Japanese press/critics**: アニメ！アニメ！, WebNewtype, Natalie (コミックナタリー), リアルサウンド映画部, Animage/月刊ニュータイプ interviews; animation critics such as 藤津亮太, 数土直志, 小新井涼, 渡邉大輔 publish columns — search their names with the title.
- **Production/sakuga**: Sakugabooru (sakugabooru.com, tags per animator and show), Sakuga Blog (blog.sakugabooru.com), animator X accounts, Kevin Cirugeda-style production analysis; episode credit sheets on Bangumi/AniDB.
- **Chinese commentators**: Bilibili analysis UP主, 知乎 columnists; cite by account name.

## 9. News and announcements
- Official site and official X account (search the hashtag `#<略称>` to find it).
- Natalie, アニメ！アニメ！, MANTANWEB (Japanese, fastest for staff/cast/PV news).
- ANN, Crunchyroll News (English).
- AnimeJapan / Jump Festa / Aniplex Online Fest / Kadokawa events are where many sequels and premiere dates get announced; check timing when a sequel is "announced".
