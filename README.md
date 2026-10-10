# bangumi-companion

A skill for researching and discussing Japanese anime (bangumi / 番组 / 番剧) the way a well-read fan friend would: get the facts exactly right, know what happened in each episode, know what different communities think, and say clearly which statements are facts, which are popular readings and which are the agent's own view.

> **Age-restricted: for adults (18+) only.** See [Intended audience](#intended-audience).

## What it does

When you ask about an anime's plot, an episode, a character or design choice, an interpretation, how a show was received, release or sequel news, or who worked on it, Claude:

- Resolves the exact work first from any title, Romaji, translation or nickname (e.g. "Frieren S2", "芙莉莲", "推しの子"), including the right season and entry.
- Traces seasons, air dates, staff and cast from AniList, Bangumi, MyAnimeList and しょぼいカレンダー (Syoboi Calendar).
- Builds per-episode plot summaries from community databases and wikis (萌娘百科 Moegirl, Fandom, Wikipedia, Namu Wiki) rather than relying on memory.
- Mines Bangumi episode and character discussion pages to show where discussion spiked and how sentiment moved over a series.
- Searches in the original language and labels every opinion by who said it (Japanese, Chinese, Korean or English communities, critics, staff).

## Requirements

- Claude Code with plugin support.
- Python 3 and outbound network access for the bundled scripts (standard library only, no packages to install).
- Many fan sites block automated access; the skill documents what is reachable and falls back to web fetch and search when a script cannot reach a source.

## Data disclosure

This plugin makes no network requests on its own. It consists of instructions plus helper scripts under `skills/bangumi-companion/scripts/`. **If the agent follows the skill's instructions, data from your conversation may be sent to third-party services:**

- **Bundled scripts** send anime titles, search keywords, character names and numeric IDs derived from your question directly from your machine (your IP address included) to: AniList (`graphql.anilist.co`), Bangumi (`api.bgm.tv`, `bgm.tv`), MyAnimeList (`myanimelist.net`), しょぼいカレンダー (`cal.syoboi.jp`), 萌娘百科 (`zh.moegirl.org.cn`), Fandom wikis (`*.fandom.com`), Wikipedia (`*.wikipedia.org`) and the Namu Wiki mirror (`namu.moe`). Requests use the User-Agent `bangumi-companion-skill/<version> (+https://claude.ai)`.
- **Web search and fetch.** The skill may also have the agent use Claude's web search and fetch tools (or other connectors you have enabled) to reach other sites, such as Filmarks, Annict, Douban, Reddit or X. Search queries and URLs are derived from your question.
- Anything you write in a question (titles, character names, opinions, or personal details) may end up in such queries. Do not include information you are not comfortable sending to these services.

Each service's own terms and privacy policy apply, as do those of any connector provider. The plugin author does not receive, collect or store any of this data. The scripts write fetched comment excerpts only to a local scratch directory. Disable the plugin, or deny network and web tool permissions, to prevent transmission.

## Intended audience

This plugin is intended for adults aged 18 and over and is not designed for or directed at children or minors. Anime is a broad medium, and the sources the skill reads (Bangumi, MyAnimeList, Moegirl, Fandom, Namu Wiki, fan discussion threads and others) are community-driven and **do not reliably age-restrict their content**. Results can include mature material such as sexual content and fan-service, graphic violence, discussion of abuse, self-harm or suicide, and crude or profane user comments, in several languages. The skill does not filter or sanitize this material. Do not enable it on accounts used by minors.

## Installation

```
/plugin install bangumi-companion --marketplace ruihe774/bangumi-companion
```

Or load a local checkout directly while trying it out:

```
claude --plugin-dir /path/to/bangumi-companion
```

The skill (`bangumi-companion`) then triggers automatically on anime questions; you don't need to name it.

## Layout

- `.claude-plugin/plugin.json`: manifest
- `.claude-plugin/icon.png`: icon
- `.claude-plugin/marketplace.json`: single-plugin marketplace listing
- `skills/bangumi-companion/SKILL.md`: the skill
- `skills/bangumi-companion/scripts/`: lookup, comment mining, wiki and broadcast-record helpers
- `skills/bangumi-companion/references/`: source reachability notes and opinion-gathering guidance

## Development

```
claude plugin validate .
```

## License

[The Unlicense](LICENSE)
