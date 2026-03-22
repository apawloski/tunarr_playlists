# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python tool that syncs content from Plex playlists, Letterboxd lists, and plain-text movie files into Tunarr channels. Uses `uv` for dependency management.

## Commands

```bash
uv sync              # Install dependencies
uv run tunarr-sync   # Run the sync (entry point: tunarr_playlists/main.py:main)
```

No test suite exists.

## Architecture

The sync pipeline flows: **config → source fetch → Plex lookup → Tunarr channel upsert**

- `main.py` — Orchestrator. Loads config, initializes clients, dispatches to per-source-type sync functions (`sync_playlist_to_channel`, `sync_letterboxd_to_channel`, `sync_movie_list_to_channel`). Converts Plex items into Tunarr program dicts via `convert_plex_to_tunarr_programs`.
- `config.py` — `ConfigLoader` reads `channels.yaml` into `ChannelConfig` objects. Each channel has a source type (`plex_playlist`, `letterboxd`, `movie_list`), a number (primary identifier), and flags for `replace_existing`/`randomize`.
- `plex_client.py` — Wraps `plexapi`. `search_movie(title, year)` is used by Letterboxd/movie-list flows to resolve titles to Plex rating keys.
- `tunarr_client.py` — REST client for Tunarr (`/api/*`). Key pattern: channels are looked up by number (`get_channel_by_number`), created if missing, and name-updated if changed. Programming uses a two-phase approach: `batch_lookup_programs` resolves existing programs by external ID, then `add_programs_to_channel` sends a mixed lineup of `persisted` (existing) and `index` (new) entries.
- `letterboxd_client.py` — Scrapes Letterboxd list pages with `cloudscraper` + BeautifulSoup. Handles pagination and two HTML structures (new `posteritem`/react-component and legacy `poster-container`).

## Key Design Decisions

- **Channel number is the primary identifier** — channels are matched by number, not name. Name changes are applied as updates.
- **Tunarr program uniqueId format** — `plex|{mediaSourceId}|{ratingKey}`. The media source ID comes from Tunarr's `/media-sources` endpoint matched by Plex server friendly name.
- **Plex searches are parallelized** — `ThreadPoolExecutor(max_workers=10)` for Letterboxd and movie-list flows.
- **Content is randomized by default** — `randomize: true` is the default for all channel types.

## Configuration

- `.env` — Server connection details (`PLEX_URL`, `PLEX_TOKEN`, `TUNARR_URL`, `TUNARR_API_KEY`, optional `CHANNELS_CONFIG`)
- `channels.yaml` — Channel definitions. See `channels.yaml.example` for format.
- Both `.env` and `channels.yaml` are gitignored.
