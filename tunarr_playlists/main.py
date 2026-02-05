"""Main script to sync Plex playlists to Tunarr channels."""

import os
import sys
import logging
import random
from typing import List, Dict, Any
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .plex_client import PlexClient
from .tunarr_client import TunarrClient
from .letterboxd_client import LetterboxdClient
from .config import ConfigLoader, ChannelConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_movie_list_file(file_path: str, config_dir: str) -> List[str]:
    """Read movie names from a file and deduplicate.

    Args:
        file_path: Path to the movie list file (can be relative or absolute)
        config_dir: Directory containing the config file (for resolving relative paths)

    Returns:
        List of unique movie titles

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    # Resolve file path (support both absolute and relative paths)
    if os.path.isabs(file_path):
        resolved_path = file_path
    else:
        resolved_path = os.path.join(config_dir, file_path)

    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"Movie list file not found: {resolved_path}")

    logger.info(f"Reading movie list from: {resolved_path}")

    # Read file and process lines
    with open(resolved_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Strip whitespace, filter empty lines
    movie_titles = [line.strip() for line in lines if line.strip()]

    # Deduplicate while preserving order
    unique_movies = list(dict.fromkeys(movie_titles))

    duplicates_removed = len(movie_titles) - len(unique_movies)
    if duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} duplicate(s) from movie list")

    logger.info(f"Loaded {len(unique_movies)} unique movie(s) from file")
    return unique_movies


def convert_plex_to_tunarr_programs(
    plex_items: List[Dict[str, Any]],
    media_source_id: str
) -> List[Dict[str, Any]]:
    """Convert Plex playlist items to Tunarr program format.

    Args:
        plex_items: List of Plex item dictionaries
        media_source_id: Tunarr media source ID for the Plex server

    Returns:
        List of Tunarr program dictionaries
    """
    import uuid

    programs = []

    for item in plex_items:
        rating_key = str(item.get('rating_key', ''))

        # Determine subtype based on Plex type
        item_type = item.get('type', 'movie')
        if item_type == 'episode':
            subtype = 'episode'
        elif item_type == 'track':
            subtype = 'track'
        else:
            # Default to movie for movies and unknown types
            subtype = 'movie'

        # Generate uniqueId in the format required by Tunarr: sourceType|sourceId|externalKey
        # This format is required for Tunarr to properly track programs
        program_id = f"plex|{media_source_id}|{rating_key}"

        # Build Tunarr program object with all required fields
        program = {
            'type': 'content',
            'persisted': False,
            'id': program_id,
            'uniqueId': program_id,
            'title': item.get('title', 'Unknown'),
            'duration': item.get('duration', 0),
            'subtype': subtype,
            'externalSourceType': 'plex',
            'externalSourceName': media_source_id,
            'externalSourceId': media_source_id,
            'externalKey': rating_key,
            'externalIds': [
                {
                    'type': 'multi',
                    'source': 'plex',
                    'sourceId': media_source_id,
                    'id': rating_key
                }
            ]
        }

        # Add optional fields
        if 'year' in item:
            program['year'] = item['year']
        if 'summary' in item:
            program['summary'] = item['summary']

        programs.append(program)

    logger.info(f"Converted {len(programs)} Plex items to Tunarr program format")
    return programs


def sync_playlist_to_channel(
    plex_client: PlexClient,
    tunarr_client: TunarrClient,
    playlist_name: str,
    channel_name: str,
    channel_number: int,
    replace_existing: bool = True,
    randomize: bool = True
) -> None:
    """Sync a Plex playlist to a Tunarr channel.

    Args:
        plex_client: Connected Plex client
        tunarr_client: Tunarr client instance
        playlist_name: Name of Plex playlist
        channel_name: Name for Tunarr channel
        channel_number: Channel number to use
        replace_existing: Whether to replace existing programming
        randomize: Whether to randomize the order of programs
    """
    logger.info(f"Starting sync: '{playlist_name}' -> '{channel_name}' (#{channel_number})")

    # Get playlist items from Plex
    logger.info(f"Fetching Plex playlist: {playlist_name}")
    plex_items = plex_client.get_playlist_items(playlist_name)

    if not plex_items:
        logger.error(f"No items found in playlist: {playlist_name}")
        return

    logger.info(f"Found {len(plex_items)} items in Plex playlist")

    # Check if channel exists by number (primary identifier)
    channel = tunarr_client.get_channel_by_number(channel_number)

    if not channel:
        # Create new channel
        logger.info(f"Creating new channel: {channel_name} (#{channel_number})")
        channel = tunarr_client.create_channel(
            name=channel_name,
            number=channel_number
        )
    else:
        logger.info(f"Channel #{channel_number} exists: {channel.get('name')} (ID: {channel.get('id')})")

        # Update channel name if it has changed
        if channel.get('name') != channel_name:
            logger.info(f"Updating channel name: '{channel.get('name')}' -> '{channel_name}'")
            tunarr_client.update_channel(channel['id'], name=channel_name)
            channel['name'] = channel_name

        # Optionally clear existing programming
        if replace_existing:
            logger.info("Clearing existing programming")
            tunarr_client.delete_channel_programming(channel['id'])

    # Get Tunarr media source ID for this Plex server
    media_source_id = tunarr_client.get_plex_media_source_id(plex_client.server_name)
    if not media_source_id:
        logger.error(f"Plex server '{plex_client.server_name}' not configured in Tunarr. Please add it first.")
        return

    # Convert Plex items to Tunarr programs
    programs = convert_plex_to_tunarr_programs(plex_items, media_source_id)

    # Randomize if requested
    if randomize:
        logger.info("Randomizing program order")
        random.shuffle(programs)

    # Add programs to channel
    logger.info(f"Adding {len(programs)} programs to channel")
    tunarr_client.add_programs_to_channel(channel['id'], programs)

    logger.info("✓ Sync completed successfully!")
    logger.info(f"  Channel: {channel_name} (#{channel_number})")
    logger.info(f"  Programs: {len(programs)}")


def sync_letterboxd_to_channel(
    plex_client: PlexClient,
    tunarr_client: TunarrClient,
    letterboxd_url: str,
    channel_name: str,
    channel_number: int,
    replace_existing: bool = True,
    randomize: bool = True
) -> None:
    """Sync a Letterboxd list to a Tunarr channel.

    Args:
        plex_client: Connected Plex client
        tunarr_client: Tunarr client instance
        letterboxd_url: URL of Letterboxd list
        channel_name: Name for Tunarr channel
        channel_number: Channel number to use
        replace_existing: Whether to replace existing programming
        randomize: Whether to randomize the order of programs
    """
    logger.info(f"Starting Letterboxd sync: {letterboxd_url} -> '{channel_name}' (#{channel_number})")

    # Fetch movies from Letterboxd
    letterboxd_client = LetterboxdClient()
    logger.info(f"Fetching Letterboxd list: {letterboxd_url}")
    letterboxd_movies = letterboxd_client.get_list_movies(letterboxd_url)

    if not letterboxd_movies:
        logger.error(f"No movies found in Letterboxd list: {letterboxd_url}")
        return

    logger.info(f"Found {len(letterboxd_movies)} movies in Letterboxd list")

    # Search for each movie in Plex (parallelized for speed)
    plex_items = []
    not_found = []

    def search_single_movie(movie):
        """Helper function to search for a single movie."""
        title = movie['title']
        year = movie.get('year')
        plex_movie = plex_client.search_movie(title, year)
        return (movie, plex_movie)

    logger.info(f"Searching Plex library for {len(letterboxd_movies)} movies (parallelized)...")

    # Use ThreadPoolExecutor to parallelize searches (max 10 concurrent requests)
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all search tasks
        future_to_movie = {executor.submit(search_single_movie, movie): movie for movie in letterboxd_movies}

        # Process results as they complete
        for future in as_completed(future_to_movie):
            movie, plex_movie = future.result()
            title = movie['title']
            year = movie.get('year')

            if plex_movie:
                plex_items.append(plex_movie)
                logger.debug(f"Found: {title}" + (f" ({year})" if year else ""))
            else:
                not_found.append(f"{title}" + (f" ({year})" if year else ""))

    logger.info(f"Found {len(plex_items)} / {len(letterboxd_movies)} movies in Plex")

    if not_found:
        logger.warning(f"Could not find {len(not_found)} movies in Plex:")
        for title in not_found[:10]:  # Show first 10
            logger.warning(f"  - {title}")
        if len(not_found) > 10:
            logger.warning(f"  ... and {len(not_found) - 10} more")

    if not plex_items:
        logger.error("No movies from Letterboxd list were found in Plex")
        return

    # Check if channel exists by number (primary identifier)
    channel = tunarr_client.get_channel_by_number(channel_number)

    if not channel:
        # Create new channel
        logger.info(f"Creating new channel: {channel_name} (#{channel_number})")
        channel = tunarr_client.create_channel(
            name=channel_name,
            number=channel_number
        )
    else:
        logger.info(f"Channel #{channel_number} exists: {channel.get('name')} (ID: {channel.get('id')})")

        # Update channel name if it has changed
        if channel.get('name') != channel_name:
            logger.info(f"Updating channel name: '{channel.get('name')}' -> '{channel_name}'")
            tunarr_client.update_channel(channel['id'], name=channel_name)
            channel['name'] = channel_name

        # Optionally clear existing programming
        if replace_existing:
            logger.info("Clearing existing programming")
            tunarr_client.delete_channel_programming(channel['id'])

    # Get Tunarr media source ID for this Plex server
    media_source_id = tunarr_client.get_plex_media_source_id(plex_client.server_name)
    if not media_source_id:
        logger.error(f"Plex server '{plex_client.server_name}' not configured in Tunarr. Please add it first.")
        return

    # Convert Plex items to Tunarr programs
    programs = convert_plex_to_tunarr_programs(plex_items, media_source_id)

    # Randomize if requested
    if randomize:
        logger.info("Randomizing program order")
        random.shuffle(programs)

    # Add programs to channel
    logger.info(f"Adding {len(programs)} programs to channel")
    tunarr_client.add_programs_to_channel(channel['id'], programs)

    logger.info("✓ Sync completed successfully!")
    logger.info(f"  Channel: {channel_name} (#{channel_number})")
    logger.info(f"  Programs: {len(programs)}")
    logger.info(f"  Movies from Letterboxd: {len(letterboxd_movies)}")
    logger.info(f"  Movies found in Plex: {len(plex_items)}")
    logger.info(f"  Movies not found: {len(not_found)}")


def sync_movie_list_to_channel(
    plex_client: PlexClient,
    tunarr_client: TunarrClient,
    file_path: str,
    config_dir: str,
    channel_name: str,
    channel_number: int,
    replace_existing: bool = True,
    randomize: bool = True
) -> None:
    """Sync a movie list file to a Tunarr channel.

    Args:
        plex_client: Connected Plex client
        tunarr_client: Tunarr client instance
        file_path: Path to movie list file
        config_dir: Directory containing config file
        channel_name: Name for Tunarr channel
        channel_number: Channel number to use
        replace_existing: Whether to replace existing programming
        randomize: Whether to randomize the order of programs
    """
    logger.info(f"Starting movie list sync: {file_path} -> '{channel_name}' (#{channel_number})")

    # Read movie list from file
    try:
        movie_titles = read_movie_list_file(file_path, config_dir)
    except FileNotFoundError as e:
        logger.error(str(e))
        return

    if not movie_titles:
        logger.error(f"No movies found in file: {file_path}")
        return

    # Convert to consistent format (list of dicts with 'title' key)
    movies = [{'title': title} for title in movie_titles]

    # Search for each movie in Plex (parallelized for speed)
    plex_items = []
    not_found = []

    def search_single_movie(movie):
        """Helper function to search for a single movie."""
        title = movie['title']
        plex_movie = plex_client.search_movie(title)
        return (movie, plex_movie)

    logger.info(f"Searching Plex library for {len(movies)} movies (parallelized)...")

    # Use ThreadPoolExecutor to parallelize searches (max 10 concurrent requests)
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all search tasks
        future_to_movie = {executor.submit(search_single_movie, movie): movie for movie in movies}

        # Process results as they complete
        for future in as_completed(future_to_movie):
            movie, plex_movie = future.result()
            title = movie['title']

            if plex_movie:
                plex_items.append(plex_movie)
                logger.debug(f"Found: {title}")
            else:
                not_found.append(title)

    logger.info(f"Found {len(plex_items)} / {len(movies)} movies in Plex")

    if not_found:
        logger.warning(f"Could not find {len(not_found)} movies in Plex:")
        for title in not_found[:10]:  # Show first 10
            logger.warning(f"  - {title}")
        if len(not_found) > 10:
            logger.warning(f"  ... and {len(not_found) - 10} more")

    if not plex_items:
        logger.error("No movies from list were found in Plex")
        return

    # Check if channel exists by number (primary identifier)
    channel = tunarr_client.get_channel_by_number(channel_number)

    if not channel:
        # Create new channel
        logger.info(f"Creating new channel: {channel_name} (#{channel_number})")
        channel = tunarr_client.create_channel(
            name=channel_name,
            number=channel_number
        )
    else:
        logger.info(f"Channel #{channel_number} exists: {channel.get('name')} (ID: {channel.get('id')})")

        # Update channel name if it has changed
        if channel.get('name') != channel_name:
            logger.info(f"Updating channel name: '{channel.get('name')}' -> '{channel_name}'")
            tunarr_client.update_channel(channel['id'], name=channel_name)
            channel['name'] = channel_name

        # Optionally clear existing programming
        if replace_existing:
            logger.info("Clearing existing programming")
            tunarr_client.delete_channel_programming(channel['id'])

    # Get Tunarr media source ID for this Plex server
    media_source_id = tunarr_client.get_plex_media_source_id(plex_client.server_name)
    if not media_source_id:
        logger.error(f"Plex server '{plex_client.server_name}' not configured in Tunarr. Please add it first.")
        return

    # Convert Plex items to Tunarr programs
    programs = convert_plex_to_tunarr_programs(plex_items, media_source_id)

    # Randomize if requested
    if randomize:
        logger.info("Randomizing program order")
        random.shuffle(programs)

    # Add programs to channel
    logger.info(f"Adding {len(programs)} programs to channel")
    tunarr_client.add_programs_to_channel(channel['id'], programs)

    logger.info("✓ Sync completed successfully!")
    logger.info(f"  Channel: {channel_name} (#{channel_number})")
    logger.info(f"  Programs: {len(programs)}")
    logger.info(f"  Movies in list: {len(movies)}")
    logger.info(f"  Movies found in Plex: {len(plex_items)}")
    logger.info(f"  Movies not found: {len(not_found)}")


def process_channel(
    plex_client: PlexClient,
    tunarr_client: TunarrClient,
    channel_config: ChannelConfig,
    config_dir: str
) -> bool:
    """Process a single channel configuration.

    Args:
        plex_client: Connected Plex client
        tunarr_client: Tunarr client instance
        channel_config: Channel configuration
        config_dir: Directory containing config file

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("=" * 80)
        logger.info(f"Processing channel: {channel_config.name} (#{channel_config.number})")
        logger.info("=" * 80)

        if channel_config.is_plex_playlist:
            sync_playlist_to_channel(
                plex_client=plex_client,
                tunarr_client=tunarr_client,
                playlist_name=channel_config.playlist_name,
                channel_name=channel_config.name,
                channel_number=channel_config.number,
                replace_existing=channel_config.replace_existing,
                randomize=channel_config.randomize
            )
        elif channel_config.is_letterboxd:
            sync_letterboxd_to_channel(
                plex_client=plex_client,
                tunarr_client=tunarr_client,
                letterboxd_url=channel_config.letterboxd_url,
                channel_name=channel_config.name,
                channel_number=channel_config.number,
                replace_existing=channel_config.replace_existing,
                randomize=channel_config.randomize
            )
        elif channel_config.is_movie_list:
            sync_movie_list_to_channel(
                plex_client=plex_client,
                tunarr_client=tunarr_client,
                file_path=channel_config.file_path,
                config_dir=config_dir,
                channel_name=channel_config.name,
                channel_number=channel_config.number,
                replace_existing=channel_config.replace_existing,
                randomize=channel_config.randomize
            )

        return True

    except Exception as e:
        logger.error(f"Failed to process channel '{channel_config.name}': {e}", exc_info=True)
        return False


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()

    # Get common configuration
    plex_url = os.getenv('PLEX_URL')
    plex_token = os.getenv('PLEX_TOKEN')
    tunarr_url = os.getenv('TUNARR_URL')
    tunarr_api_key = os.getenv('TUNARR_API_KEY')
    channels_config_path = os.getenv('CHANNELS_CONFIG', 'channels.yaml')

    # Validate common configuration
    if not all([plex_url, plex_token, tunarr_url]):
        logger.error("Missing required environment variables. Check your .env file.")
        logger.error("Required: PLEX_URL, PLEX_TOKEN, TUNARR_URL")
        sys.exit(1)

    try:
        # Load channel configurations
        logger.info(f"Loading channel configurations from: {channels_config_path}")
        config_loader = ConfigLoader(channels_config_path)
        channels = config_loader.load_channels()

        # Get config directory for resolving relative file paths
        config_dir = os.path.dirname(os.path.abspath(channels_config_path))

        logger.info(f"Found {len(channels)} channel(s) to process")

    except FileNotFoundError as e:
        logger.error(str(e))
        logger.error("Please create a channels.yaml file. See channels.yaml.example for reference.")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    try:
        # Initialize clients
        logger.info("Initializing Plex client...")
        plex_client = PlexClient(plex_url, plex_token)
        plex_client.connect()

        logger.info("Initializing Tunarr client...")
        tunarr_client = TunarrClient(tunarr_url, tunarr_api_key)

        # Process all channels
        results = []
        for channel in channels:
            success = process_channel(plex_client, tunarr_client, channel, config_dir)
            results.append((channel.name, success))

        # Print summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("SYNC SUMMARY")
        logger.info("=" * 80)

        successful = sum(1 for _, success in results if success)
        failed = len(results) - successful

        for channel_name, success in results:
            status = "✓ SUCCESS" if success else "✗ FAILED"
            logger.info(f"{status}: {channel_name}")

        logger.info("")
        logger.info(f"Total channels: {len(results)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")

        if failed > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nSync cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
