# Gathering and presenting opinions

The aim is an honest picture of how a show (or episode, or character) landed, with each opinion attributed to who actually holds it. Readers lose trust fast when "fans think X" turns out to be one Reddit comment, so the work here is mostly about sampling well and labeling clearly.

## 1. Decide the scope
- Whole series, a season, one episode, one character, or one scene? Narrower scope means going to episode-level threads instead of series scores.
- Timing: reception at airing vs. in retrospect can differ (shows that were controversial weekly may be re-evaluated after the finale). Note which you're reporting.

## 2. Collect by region, in the original language
For each region, try to get at least one aggregate signal and one discussion sample.

| Region | Aggregate signal | Discussion sample | Search phrasing |
|---|---|---|---|
| Japan | Filmarks score, Annict watchers/ratings, streaming rankings, ja Wikipedia 反響・評価 (press, awards), X trend via search | まとめ/5ch threads, Annict reviews, note.com essays, news reaction roundups | `<title> <N>話 感想`, `<title> 評価`, `<title> 考察`, `<title> 賛否` |
| Chinese-speaking | Bangumi score + votes + rank, Bilibili score, Douban score (via Namu's rating template or search), 巴哈 rating; Moegirl 萌战 results for character popularity | Bangumi ep comments, NGA/贴吧 threads, 知乎 answers, Bilibili 长评 | `<中文名> 第N集 讨论`, `<中文名> 评价`, `<中文名> 解读`, `<中文名> 争议` |
| Korea | Laftel and Watcha scores (from the rating template on Namu's `/평가` page, via `wiki_text.py namu`) | Namu `/평가` 방영 후 sections, DC Inside / Ruliweb posts via search | `<한국어 제목> N화 반응`, `<제목> 평가` |
| English/global | MAL score + members, AniList score, r/anime karma/poll rank | r/anime episode thread top comments, MAL forum | `"<title>" episode N discussion`, `<title> review` |

The Bangumi script output already includes the Bangumi score, vote count, rank and tags; AniList includes average score and popularity.

## 2b. Character or arc reception: trace the trajectory
Questions like "do people like X" or "how did fans take X's arc" are usually about change over time. The method that worked:
1. Get the character's Bangumi id from `anime_lookup.py` and read the character page comments. They run roughly oldest to newest, so the early-vs-late shift is visible directly.
2. Skim those comments for nicknames and puns, then run `bgm_comments.py` with every name variant.
3. Read the per-episode table. Total comments show which episodes people cared about; the keyword-hit share shows when the character dominated discussion. Spikes usually mark the turning points.
4. Read the hits episode by episode and note for each:
   - what the character did, which doubles as plot reconstruction
   - the dominant reaction
   - the strongest minority defense
5. Separate *liking the character* from *liking the writing*. Fans often still like the design, premise or performer but reject how the story handled the character, or the reverse. Report the two verdicts separately.
6. Check whether criticism lands on the character or on the plotting around them. "Written dumber for the plot" (降智) and "contrived information gap" are complaints about writing, not about the character. Some defenders also point out double standards, such as excusing the villain while blaming the protagonist.

## 3. Split commentators from the wider audience

**Commentators** — anyone whose opinion carries individual weight:
- Professional critics and outlets (ANN, Polygon, Japanese animation critics, Natalie columns).
- Industry voices (animators, directors of other works, voice actors commenting publicly).
- Prominent analysts (YouTube/Bilibili analysis creators, well-known 知乎/note writers, sakuga commentators).
Attribute each by name and outlet. Summarize their argument, not just their verdict.

**Wider audience** — the aggregate:
- Report scores with sample size and, where available, trend over the airing (e.g. "Bangumi 8.5 from ~X votes, up from 8.1 at ep 6").
- Describe the dominant sentiment and the main minority sentiment in big threads. Use "many/most/some" carefully and only when the sample supports it.
- Flag known skews: 5ch/まとめ skew negative and provocative; r/anime and MAL skew toward young English-speaking fans and hype; Bangumi skews toward veteran core fans with strict scoring; Bilibili scores can be inflated for licensed hits; review-bombing happens around controversies.

Keep the two layers visibly separate in the answer (separate paragraphs or headings).

Beware of single-commentator capture. If the only critic you found is a self-declared fan of the character, or the piece is sponsored, say so. One enthusiastic columnist is not "English-speaking reception".

## 4. Interpretations and alternative interpretations
For a "what did this mean" question:
1. **Authorial statements first** — staff/author interviews, audio commentary, booklet notes, original author comments. Note if the staff deliberately left it open.
2. **Mainstream reading** — the interpretation most commonly stated across communities. Say where it's prevalent.
3. **Alternative readings** — at least one credible alternative, ideally from a different community or critic, with its supporting evidence (scene details, source material, motifs).
4. **Source-material context** — whether the manga/LN resolves it later (spoiler-gated).
5. **Your own read** — optional, labeled as yours, with reasoning.

Present competing readings fairly; don't crown one as "correct" unless the creators settled it. Note when a reading is a regional tendency (e.g. a pun or cultural reference that Japanese viewers read one way and translated releases obscure). Translation differences between subtitle tracks are a frequent cause of divergent Western vs. Asian readings — check the original Japanese line when a debate hinges on wording.

## 5. Presenting
A good default structure for a reception answer:

1. One-line verdict of overall reception (with the strongest numbers).
2. Japan — aggregate + what people praised/criticized.
3. Chinese-speaking — same.
4. Korea / English-speaking — same, shorter unless the user cares.
5. Critics/commentators — named views.
6. Points of contention and competing interpretations.
7. Sources.

Scale it down for small questions — one episode's reaction might be three short paragraphs. Always paraphrase; quote at most a short phrase when exact wording matters, and never reproduce full reviews or long comments.
