# Tunarr Plex Playlist Sync

A Python tool to sync Plex playlists to Tunarr channels. Automatically creates Tunarr channels from Plex playlists and keeps the programming in sync.

## Features

- Creates Tunarr channels from Plex playlists
- Automatically adds all items from a Plex playlist to the channel
- Updates existing channels if they already exist
- Supports configuration via environment variables

## Requirements

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- Plex Media Server
- Tunarr instance

## Installation

1. Clone or download this repository

2. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install dependencies:
```bash
uv sync
```

4. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

5. Edit `.env` with your configuration:
   - `PLEX_URL`: Your Plex server URL
   - `PLEX_TOKEN`: Your Plex authentication token (see below)
   - `TUNARR_URL`: Your Tunarr instance URL
   - `TUNARR_API_KEY`: Your Tunarr API key (if required)
   - `PLEX_PLAYLIST_NAME`: Name of the Plex playlist to sync
   - `TUNARR_CHANNEL_NAME`: Name for the Tunarr channel
   - `TUNARR_CHANNEL_NUMBER`: Channel number to assign

## Getting Your Plex Token

1. Open Plex Web App
2. Play any media item
3. Click the three dots (...) > "Get Info"
4. Click "View XML"
5. Look for `X-Plex-Token` in the URL

## Usage

Run the sync script:

```bash
uv run main.py
```

Or use the installed script:

```bash
uv run tunarr-sync
```

The script will:
1. Connect to your Plex server
2. Fetch items from the specified playlist
3. Check if the Tunarr channel exists
4. Create the channel if needed
5. Add all playlist items as programming

## Project Structure

```
tunarr-playlists/
├── main.py              # Main sync script
├── plex_client.py       # Plex API client
├── tunarr_client.py     # Tunarr API client
├── pyproject.toml       # Project metadata and dependencies
├── .env                 # Configuration (not in git)
└── README.md           # This file
```

## Troubleshooting

- **Connection errors**: Verify your URLs and tokens are correct
- **Playlist not found**: Check the exact name of your Plex playlist
- **Channel creation fails**: Verify Tunarr API permissions and available channel numbers

## License

MIT
