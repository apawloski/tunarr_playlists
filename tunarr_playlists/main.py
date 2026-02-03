"""Main script to sync Plex playlists to Tunarr channels."""

import os
import sys
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

from .plex_client import PlexClient
from .tunarr_client import TunarrClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    replace_existing: bool = True
) -> None:
    """Sync a Plex playlist to a Tunarr channel.

    Args:
        plex_client: Connected Plex client
        tunarr_client: Tunarr client instance
        playlist_name: Name of Plex playlist
        channel_name: Name for Tunarr channel
        channel_number: Channel number to use
        replace_existing: Whether to replace existing programming
    """
    logger.info(f"Starting sync: '{playlist_name}' -> '{channel_name}' (#{channel_number})")

    # Get playlist items from Plex
    logger.info(f"Fetching Plex playlist: {playlist_name}")
    plex_items = plex_client.get_playlist_items(playlist_name)

    if not plex_items:
        logger.error(f"No items found in playlist: {playlist_name}")
        return

    logger.info(f"Found {len(plex_items)} items in Plex playlist")

    # Check if channel exists
    channel = tunarr_client.get_channel_by_name(channel_name)

    if not channel:
        # Check if channel number is already in use
        existing = tunarr_client.get_channel_by_number(channel_number)
        if existing:
            logger.error(f"Channel number {channel_number} is already in use by: {existing.get('name')}")
            return

        # Create new channel
        logger.info(f"Creating new channel: {channel_name} (#{channel_number})")
        channel = tunarr_client.create_channel(
            name=channel_name,
            number=channel_number
        )
    else:
        logger.info(f"Channel already exists: {channel_name} (ID: {channel.get('id')})")

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

    # Add programs to channel
    logger.info(f"Adding {len(programs)} programs to channel")
    tunarr_client.add_programs_to_channel(channel['id'], programs)

    logger.info("✓ Sync completed successfully!")
    logger.info(f"  Channel: {channel_name} (#{channel_number})")
    logger.info(f"  Programs: {len(programs)}")


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()

    # Get configuration
    plex_url = os.getenv('PLEX_URL')
    plex_token = os.getenv('PLEX_TOKEN')
    tunarr_url = os.getenv('TUNARR_URL')
    tunarr_api_key = os.getenv('TUNARR_API_KEY')
    playlist_name = os.getenv('PLEX_PLAYLIST_NAME')
    channel_name = os.getenv('TUNARR_CHANNEL_NAME')
    channel_number = os.getenv('TUNARR_CHANNEL_NUMBER')

    # Validate configuration
    if not all([plex_url, plex_token, tunarr_url, playlist_name, channel_name, channel_number]):
        logger.error("Missing required environment variables. Check your .env file.")
        logger.error("Required: PLEX_URL, PLEX_TOKEN, TUNARR_URL, PLEX_PLAYLIST_NAME, TUNARR_CHANNEL_NAME, TUNARR_CHANNEL_NUMBER")
        sys.exit(1)

    try:
        channel_number = int(channel_number)
    except ValueError:
        logger.error("TUNARR_CHANNEL_NUMBER must be a valid integer")
        sys.exit(1)

    try:
        # Initialize clients
        logger.info("Initializing Plex client...")
        plex_client = PlexClient(plex_url, plex_token)
        plex_client.connect()

        logger.info("Initializing Tunarr client...")
        tunarr_client = TunarrClient(tunarr_url, tunarr_api_key)

        # Perform sync
        sync_playlist_to_channel(
            plex_client=plex_client,
            tunarr_client=tunarr_client,
            playlist_name=playlist_name,
            channel_name=channel_name,
            channel_number=channel_number,
            replace_existing=True
        )

    except KeyboardInterrupt:
        logger.info("\nSync cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
