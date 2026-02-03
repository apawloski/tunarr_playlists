"""Plex API client for fetching playlist information."""

import logging
from typing import List, Optional
from plexapi.server import PlexServer
from plexapi.playlist import Playlist
from plexapi.video import Movie

logger = logging.getLogger(__name__)


class PlexClient:
    """Client for interacting with Plex API."""

    def __init__(self, url: str, token: str):
        """Initialize Plex client.

        Args:
            url: Plex server URL
            token: Plex authentication token
        """
        self.url = url
        self.token = token
        self._server: Optional[PlexServer] = None

    @property
    def server_id(self) -> str:
        """Get the Plex server machine identifier.

        Returns:
            Plex server machine identifier (UUID)
        """
        if not self._server:
            raise RuntimeError("Not connected to Plex server. Call connect() first.")
        return self._server.machineIdentifier

    @property
    def server_name(self) -> str:
        """Get the Plex server friendly name.

        Returns:
            Plex server friendly name
        """
        if not self._server:
            raise RuntimeError("Not connected to Plex server. Call connect() first.")
        return self._server.friendlyName

    def connect(self) -> None:
        """Connect to Plex server."""
        try:
            self._server = PlexServer(self.url, self.token)
            logger.info(f"Connected to Plex server: {self._server.friendlyName}")
        except Exception as e:
            logger.error(f"Failed to connect to Plex: {e}")
            raise

    def get_playlist(self, playlist_name: str) -> Optional[Playlist]:
        """Get a playlist by name.

        Args:
            playlist_name: Name of the playlist

        Returns:
            Playlist object or None if not found
        """
        if not self._server:
            raise RuntimeError("Not connected to Plex server. Call connect() first.")

        try:
            playlists = self._server.playlists()
            for playlist in playlists:
                if playlist.title == playlist_name:
                    logger.info(f"Found playlist: {playlist_name} with {len(playlist.items())} items")
                    return playlist

            logger.warning(f"Playlist not found: {playlist_name}")
            return None
        except Exception as e:
            logger.error(f"Error fetching playlist: {e}")
            raise

    def get_playlist_items(self, playlist_name: str) -> List[dict]:
        """Get all items from a playlist with metadata.

        Args:
            playlist_name: Name of the playlist

        Returns:
            List of dictionaries containing item metadata
        """
        playlist = self.get_playlist(playlist_name)
        if not playlist:
            return []

        items = []
        for item in playlist.items():
            item_data = {
                'title': item.title,
                'type': item.type,
                'rating_key': item.ratingKey,
                'key': item.key,
            }

            # Add additional metadata for movies
            if hasattr(item, 'year'):
                item_data['year'] = item.year
            if hasattr(item, 'duration'):
                item_data['duration'] = item.duration
            if hasattr(item, 'guid'):
                item_data['guid'] = item.guid
            if hasattr(item, 'summary'):
                item_data['summary'] = item.summary

            items.append(item_data)

        logger.info(f"Retrieved {len(items)} items from playlist: {playlist_name}")
        return items

    def list_playlists(self) -> List[str]:
        """List all available playlists.

        Returns:
            List of playlist names
        """
        if not self._server:
            raise RuntimeError("Not connected to Plex server. Call connect() first.")

        try:
            playlists = self._server.playlists()
            names = [p.title for p in playlists]
            logger.info(f"Found {len(names)} playlists")
            return names
        except Exception as e:
            logger.error(f"Error listing playlists: {e}")
            raise
