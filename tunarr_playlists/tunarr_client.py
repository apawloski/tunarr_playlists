"""Tunarr API client for managing channels and programming."""

import logging
from typing import List, Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class TunarrClient:
    """Client for interacting with Tunarr API."""

    def __init__(self, url: str, api_key: Optional[str] = None):
        """Initialize Tunarr client.

        Args:
            url: Tunarr server URL
            api_key: Optional API key for authentication
        """
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()

        if api_key:
            self.session.headers.update({'X-API-Key': api_key})

    def get_plex_media_source_id(self, plex_server_name: str) -> Optional[str]:
        """Get Tunarr media source ID for a Plex server.

        Args:
            plex_server_name: Plex server friendly name

        Returns:
            Tunarr media source ID or None if not found
        """
        try:
            response = self._request('GET', '/media-sources')
            sources = response.json()

            # Find the Plex source matching the server name
            for source in sources:
                if source.get('type') == 'plex' and source.get('name') == plex_server_name:
                    media_source_id = source.get('id')
                    logger.info(f"Found Tunarr media source for Plex server '{plex_server_name}': {media_source_id}")
                    return media_source_id

            logger.warning(f"Plex media source not found for server name: {plex_server_name}")
            return None
        except Exception as e:
            logger.error(f"Error fetching media sources: {e}")
            return None

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            Response object
        """
        url = f"{self.url}/api{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {endpoint} - {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.text
                    logger.error(f"Response body: {error_body}")
                except Exception:
                    pass
            raise

    def get_channels(self) -> List[Dict[str, Any]]:
        """Get all channels.

        Returns:
            List of channel dictionaries
        """
        try:
            response = self._request('GET', '/channels')
            channels = response.json()
            logger.info(f"Retrieved {len(channels)} channels")
            return channels
        except Exception as e:
            logger.error(f"Error fetching channels: {e}")
            raise

    def get_channel_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a channel by name.

        Args:
            name: Channel name

        Returns:
            Channel dictionary or None if not found
        """
        channels = self.get_channels()
        for channel in channels:
            if channel.get('name') == name:
                logger.info(f"Found channel: {name} (ID: {channel.get('id')})")
                return channel

        logger.info(f"Channel not found: {name}")
        return None

    def get_channel_by_number(self, number: int) -> Optional[Dict[str, Any]]:
        """Get a channel by number.

        Args:
            number: Channel number

        Returns:
            Channel dictionary or None if not found
        """
        channels = self.get_channels()
        for channel in channels:
            if channel.get('number') == number:
                logger.info(f"Found channel number: {number} (ID: {channel.get('id')})")
                return channel

        return None

    def create_channel(self, name: str, number: int, **kwargs) -> Dict[str, Any]:
        """Create a new channel.

        Args:
            name: Channel name
            number: Channel number
            **kwargs: Additional channel properties

        Returns:
            Created channel dictionary
        """
        import uuid
        import time

        # Get transcode config ID (use from kwargs or get from existing channel)
        transcode_config_id = kwargs.get('transcode_config_id')
        if not transcode_config_id:
            try:
                # Get transcode config from an existing channel
                channels = self.get_channels()
                if channels:
                    transcode_config_id = channels[0].get('transcodeConfigId')
            except Exception:
                pass

        # Build channel object with all required fields
        channel_data = {
            'id': str(uuid.uuid4()),
            'name': name,
            'number': number,
            'duration': 0,
            'disableFillerOverlay': kwargs.get('disable_filler_overlay', False),
            'startTime': kwargs.get('start_time', int(time.time() * 1000)),
            'stealth': kwargs.get('stealth', False),
            'groupTitle': kwargs.get('group_title', 'tunarr'),
            'guideMinimumDuration': kwargs.get('guide_minimum_duration', 30000),
            'icon': {
                'path': kwargs.get('icon_path', ''),
                'width': kwargs.get('icon_width', 0),
                'duration': kwargs.get('icon_duration', 0),
                'position': kwargs.get('icon_position', 'bottom-right'),
            },
            'offline': {
                'mode': kwargs.get('offline_mode', 'pic'),
                'picture': kwargs.get('offline_picture', ''),
                'soundtrack': kwargs.get('offline_soundtrack', ''),
            },
            'onDemand': {
                'enabled': kwargs.get('on_demand_enabled', False),
            },
            'streamMode': kwargs.get('stream_mode', 'hls'),
            'transcodeConfigId': transcode_config_id or '',
            'subtitlesEnabled': kwargs.get('subtitles_enabled', False),
        }

        # Wrap in the required API format
        request_body = {
            'type': 'new',
            'channel': channel_data
        }

        try:
            response = self._request('POST', '/channels', json=request_body)
            channel = response.json()
            logger.info(f"Created channel: {name} (ID: {channel.get('id')})")
            return channel
        except Exception as e:
            logger.error(f"Error creating channel: {e}")
            raise

    def get_channel_by_id(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get a channel by ID.

        Args:
            channel_id: Channel ID

        Returns:
            Channel dictionary or None if not found
        """
        try:
            response = self._request('GET', f'/channels/{channel_id}')
            channel = response.json()
            logger.info(f"Retrieved channel ID: {channel_id}")
            return channel
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"Channel not found: {channel_id}")
                return None
            raise
        except Exception as e:
            logger.error(f"Error fetching channel: {e}")
            raise

    def update_channel(self, channel_id: str, **kwargs) -> Dict[str, Any]:
        """Update an existing channel.

        Args:
            channel_id: Channel ID
            **kwargs: Channel properties to update (e.g., name, number)

        Returns:
            Updated channel dictionary
        """
        try:
            # Get current channel data
            current_channel = self.get_channel_by_id(channel_id)
            if not current_channel:
                raise ValueError(f"Channel not found: {channel_id}")

            # Update fields
            for key, value in kwargs.items():
                current_channel[key] = value

            # Send update with full channel object (PUT expects channel data directly at root level)
            response = self._request('PUT', f'/channels/{channel_id}', json=current_channel)
            channel = response.json()
            logger.info(f"Updated channel ID: {channel_id}")
            return channel
        except Exception as e:
            logger.error(f"Error updating channel: {e}")
            raise

    def batch_lookup_programs(self, external_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Batch lookup programs by external IDs.

        Args:
            external_ids: List of external IDs in format "sourceType|sourceId|externalKey"

        Returns:
            Dictionary mapping Tunarr UUIDs to program data
        """
        try:
            response = self._request('POST', '/programming/batch/lookup', json={'externalIds': external_ids})
            results = response.json()
            logger.info(f"Batch lookup found {len(results)} programs")
            return results
        except Exception as e:
            logger.error(f"Error in batch lookup: {e}")
            return {}

    def add_programs_to_channel(self, channel_id: str, programs: List[Dict[str, Any]]) -> None:
        """Add programs to a channel.

        Args:
            channel_id: Channel ID
            programs: List of program dictionaries with uniqueId field
        """
        # First, try to lookup existing programs
        external_ids = [p['uniqueId'] for p in programs]
        existing_programs = self.batch_lookup_programs(external_ids)

        # Build lineup using persisted program IDs for programs that exist,
        # and new programs for those that don't
        lineup = []
        new_programs = []

        for i, program in enumerate(programs):
            # Check if this program already exists in Tunarr
            # Match by externalSourceId and externalKey
            tunarr_uuid = None
            for uuid, prog_data in existing_programs.items():
                if (prog_data.get('externalSourceId') == program['externalSourceId'] and
                    prog_data.get('externalKey') == program['externalKey']):
                    tunarr_uuid = uuid
                    break

            if tunarr_uuid:
                # Program exists, reference it as persisted
                logger.debug(f"Found existing program: {program['title']} -> {tunarr_uuid}")
                lineup.append({
                    'type': 'persisted',
                    'programId': tunarr_uuid,
                    'duration': program['duration']
                })
            else:
                # Program doesn't exist, add it as new
                logger.debug(f"Program not found, adding as new: {program['title']}")
                new_programs.append(program)
                lineup.append({
                    'type': 'index',
                    'index': len(new_programs) - 1
                })

        # Wrap in the required API format
        request_body = {
            'type': 'manual',
            'append': False,
            'programs': new_programs,
            'lineup': lineup
        }

        try:
            response = self._request('POST', f'/channels/{channel_id}/programming', json=request_body)
            logger.info(f"Added {len(programs)} programs to channel {channel_id}")
        except Exception as e:
            logger.error(f"Error adding programs to channel: {e}")
            raise

    def delete_channel_programming(self, channel_id: str) -> None:
        """Delete all programming from a channel.

        Args:
            channel_id: Channel ID
        """
        try:
            self._request('DELETE', f'/channels/{channel_id}/programming')
            logger.info(f"Deleted all programming from channel {channel_id}")
        except requests.exceptions.HTTPError as e:
            # 404 is OK - it means there's no programming to delete
            if e.response.status_code == 404:
                logger.info(f"No programming to delete from channel {channel_id}")
            else:
                logger.error(f"Error deleting channel programming: {e}")
                raise
        except Exception as e:
            logger.error(f"Error deleting channel programming: {e}")
            raise

    def get_channel_programming(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get programming for a channel.

        Args:
            channel_id: Channel ID

        Returns:
            List of program dictionaries
        """
        try:
            response = self._request('GET', f'/channels/{channel_id}/programming')
            programs = response.json()
            logger.info(f"Retrieved {len(programs)} programs from channel {channel_id}")
            return programs
        except Exception as e:
            logger.error(f"Error fetching channel programming: {e}")
            raise
