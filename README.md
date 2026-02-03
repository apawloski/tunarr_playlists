# Tunarr Plex Playlist Sync

A Python tool to sync Plex playlists and Letterboxd lists to Tunarr channels. Automatically creates Tunarr channels and keeps the programming in sync.

## Features

- **Multi-channel management**: Define and sync dozens of channels in a single configuration file
- **Plex playlist sync**: Creates Tunarr channels from Plex playlists
- **Letterboxd list sync**: Creates Tunarr channels from Letterboxd lists
- **Automatic Plex search**: Searches your Plex library for movies from Letterboxd lists
- **Smart matching**: Matches movies by title and year for accuracy
- **Graceful handling**: Handles cases where Letterboxd movies aren't in Plex
- **Batch processing**: Sync all channels with a single command
- **Flexible updates**: Replace or append to existing channel programming
- **Clear reporting**: Detailed logs and summary of sync results

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

5. Edit `.env` with your server configuration:
   - `PLEX_URL`: Your Plex server URL
   - `PLEX_TOKEN`: Your Plex authentication token (see below)
   - `TUNARR_URL`: Your Tunarr instance URL
   - `TUNARR_API_KEY`: Your Tunarr API key (if required)

6. Copy `channels.yaml.example` to `channels.yaml` and configure your channels:
```bash
cp channels.yaml.example channels.yaml
```

7. Edit `channels.yaml` to define your channels. You can define as many channels as you want! Each channel needs:
   - `name`: Channel name in Tunarr
   - `number`: Channel number
   - `source`: Where the content comes from
     - For Plex playlists: `type: plex_playlist` and `playlist_name`
     - For Letterboxd lists: `type: letterboxd` and `url`
   - `replace_existing`: Whether to replace or append to existing programming (default: true)

## Configuration Details

### Channel Configuration Format

The `channels.yaml` file uses YAML format. Each channel must have:

- **name** (required): Display name for the channel in Tunarr
- **number** (required): Channel number (must be unique)
- **source** (required): Content source configuration
  - **type**: Either `plex_playlist` or `letterboxd`
  - For `plex_playlist`: Include `playlist_name`
  - For `letterboxd`: Include `url`
- **replace_existing** (optional): `true` to replace channel content, `false` to append (default: `true`)

You can have as many channels as you want - the tool will process them all in order!

### Using a Different Config File

By default, the tool looks for `channels.yaml` in the current directory. To use a different file:

```bash
# In .env file
CHANNELS_CONFIG=/path/to/my-channels.yaml
```

Or set it as an environment variable:

```bash
CHANNELS_CONFIG=/path/to/my-channels.yaml uv run tunarr-sync
```

## Getting Your Plex Token

1. Open Plex Web App
2. Play any media item
3. Click the three dots (...) > "Get Info"
4. Click "View XML"
5. Look for `X-Plex-Token` in the URL

## Usage

Run the sync script to process all channels defined in your `channels.yaml`:

```bash
uv run tunarr-sync
```

The script will:
1. Load all channel configurations from `channels.yaml`
2. Connect to your Plex server and Tunarr instance
3. Process each channel in order:
   - **For Plex playlists**: Fetch items from the playlist and add to channel
   - **For Letterboxd lists**: Scrape the list, search Plex for each movie, add found movies to channel
4. Create channels if they don't exist
5. Update existing channels (replace or append based on config)
6. Display a summary of results

The tool will automatically:
- Handle multi-page Letterboxd lists
- Match movies by title and year for accuracy
- Log which movies couldn't be found in Plex
- Continue processing remaining channels if one fails

## Project Structure

```
tunarr-playlists/
├── tunarr_playlists/
│   ├── main.py              # Main sync script
│   ├── plex_client.py       # Plex API client
│   ├── tunarr_client.py     # Tunarr API client
│   ├── letterboxd_client.py # Letterboxd list scraper
│   └── config.py            # Configuration loader
├── pyproject.toml           # Project metadata and dependencies
├── .env                     # Server configuration (not in git)
├── .env.example             # Example server configuration
├── channels.yaml            # Channel definitions (not in git)
├── channels.yaml.example    # Example channel definitions
└── README.md                # This file
```

## Examples

### Example Configuration

`.env` file (common settings):
```env
PLEX_URL=http://192.168.1.100:32400
PLEX_TOKEN=your_token_here
TUNARR_URL=http://localhost:8000
TUNARR_API_KEY=your_api_key_here
```

`channels.yaml` file (channel definitions):
```yaml
channels:
  # Plex playlist channel
  - name: "Action Movies"
    number: 1001
    source:
      type: plex_playlist
      playlist_name: "Action Movies"
    replace_existing: true

  # Letterboxd list channel
  - name: "Oscar Nominees 2026"
    number: 1002
    source:
      type: letterboxd
      url: "https://letterboxd.com/crew/list/every-film-nominated-for-a-2026-academy-award/"
    replace_existing: true

  # Another Letterboxd list
  - name: "Criterion Collection"
    number: 1003
    source:
      type: letterboxd
      url: "https://letterboxd.com/dave/list/criterion-collection/"
    replace_existing: true

  # TV Shows playlist
  - name: "Sitcoms"
    number: 1004
    source:
      type: plex_playlist
      playlist_name: "Best Sitcoms"
    replace_existing: false  # Append instead of replace
```

Running `uv run tunarr-sync` will process all 4 channels automatically!

## Troubleshooting

- **"Configuration file not found"**: Create a `channels.yaml` file from the example: `cp channels.yaml.example channels.yaml`
- **"No channels defined"**: Make sure your `channels.yaml` has a `channels:` section with at least one channel
- **"Invalid YAML"**: Check your YAML syntax. Common issues:
  - Inconsistent indentation (use 2 spaces)
  - Missing colons after keys
  - Incorrect quote handling
- **Connection errors**: Verify your URLs and tokens are correct in `.env`
- **Playlist not found**: Check the exact name of your Plex playlist (case-sensitive)
- **Letterboxd list empty**: Verify the URL is correct and publicly accessible
- **Movies not found in Plex**: The tool searches by title and year. Ensure movie titles in Plex match Letterboxd
- **Channel creation fails**: Verify Tunarr API permissions and available channel numbers
- **Channel number conflict**: Each channel must have a unique number. Check existing Tunarr channels

## License

MIT
